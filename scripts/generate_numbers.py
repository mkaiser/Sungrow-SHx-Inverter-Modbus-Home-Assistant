#!/usr/bin/env python3
"""Generate the `number` entity descriptions from the write table.

The registers, their bounds and which of them are writable at all come from
[scripts/writes.py](writes.py); this turns each row into a Home Assistant
entity description. Generated rather than written by hand for the same reason
the sensors are: a bound typed twice is a bound that will disagree with itself
eventually, and the number that decides how far a battery discharges is not
one to get wrong.

    python scripts/generate_numbers.py            # write the module
    python scripts/generate_numbers.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from writes import NUMBERS

REPO = Path(__file__).resolve().parent.parent
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
OUTPUT = REPO / "custom_components" / "sungrow_modbus" / "number_descriptions.py"

TIER_NAMES = {5: "realtime", 10: "fast", 60: "medium", 600: "slowest"}

HEADER = '''"""Number descriptions, generated from the write table.

Do not edit by hand: `scripts/generate_numbers.py` writes this file from
`scripts/writes.py`, and CI checks that it matches.

Each of these reads and writes one register. The YAML package needed three
pieces for that — a `template number`, a `modbus.write_register` action and a
`homeassistant.update_entity` call to see the result — because YAML Modbus has
no write-then-read. An integration does not.
"""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower

from sungrow_modbus import Capability

from .entity import SungrowNumberDescription

NUMBER_DESCRIPTIONS: tuple[SungrowNumberDescription, ...] = (
'''


def _registers() -> dict[str, dict]:
    """Return the modbus register rows, by field name."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    # Sensors only. `switch.export_power_limit` shares its object id with
    # `sensor.export_power_limit` and points at a different register -- the
    # mode flag at 13086 rather than the value at 13073 -- so a lookup keyed
    # by object id alone silently takes whichever came last.
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in entities
        if e["layer"] == "modbus"
        and e["domain"] == "sensor"
        and e.get("address") is not None
    }


def _numbers() -> dict[str, dict]:
    """Return the YAML's `number` template rows, by unique_id."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["unique_id"]: e
        for e in entities
        if e["domain"] == "number" and e.get("unique_id")
    }


def render() -> str:
    """Return the whole generated module."""
    registers = _registers()
    legacy_numbers = _numbers()
    lines = [HEADER]

    for row in NUMBERS:
        register = registers[row["field"]]
        legacy = legacy_numbers[row["legacy_unique_id"]]
        component = f"{TIER_NAMES[register['scan_interval']]}_{register['input_type']}"

        lines.append("    SungrowNumberDescription(")
        lines.append(f'        key="{row["field"]}",')
        lines.append(f'        component="{component}",')
        lines.append(f'        field="{row["field"]}",')
        lines.append(f'        translation_key="{row["field"]}",')
        # The YAML's `number` entity is what a migrating user has, so its name
        # and platform are what the id is claimed through -- not the sensor's,
        # which reads the same register under a different entity id.
        lines.append(f'        legacy_name="{legacy["name"]}",')
        lines.append(f'        legacy_unique_id="{row["legacy_unique_id"]}",')
        lines.append('        legacy_platform="template",')
        # The export power limit is the inverter's, not the battery's.
        capability = "BATTERY" if row["field"] != "export_power_limit" else None
        if capability:
            lines.append(f"        requires=Capability.{capability},")
        lines.append(f"        native_min_value={row['minimum']},")
        lines.append(f"        native_max_value={row['maximum']},")
        lines.append(f"        native_step={row['step']},")
        if row.get("minimum_field"):
            lines.append(f'        minimum_field="{row["minimum_field"]}",')
        if row.get("maximum_field"):
            lines.append(f'        maximum_field="{row["maximum_field"]}",')
        if row.get("maximum_from_battery"):
            lines.append("        maximum_from_battery=True,")
        if row["unit"] == "%":
            lines.append("        native_unit_of_measurement=PERCENTAGE,")
            lines.append("        device_class=NumberDeviceClass.BATTERY,")
        else:
            lines.append("        native_unit_of_measurement=UnitOfPower.WATT,")
            lines.append("        device_class=NumberDeviceClass.POWER,")
        lines.append("        mode=NumberMode.BOX,")
        lines.append("        entity_category=EntityCategory.CONFIG,")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _formatted(text: str) -> str:
    """Return the text as ruff would format it."""
    for command in (
        [
            "ruff",
            "check",
            "--fix",
            "--select",
            "I",
            "--stdin-filename",
            OUTPUT.name,
            "-",
        ],
        ["ruff", "format", "--stdin-filename", OUTPUT.name, "-"],
    ):
        result = subprocess.run(
            command, input=text, capture_output=True, text=True, check=False
        )
        if result.returncode not in (0, 1):
            raise SystemExit(f"{command[1]} failed:\n{result.stderr}")
        text = result.stdout
    return text


def main() -> int:
    """Write the descriptions, or check the committed ones are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = _formatted(render())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"{OUTPUT.relative_to(REPO)} is stale.\n"
                "Run scripts/generate_numbers.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the write table")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}: {len(NUMBERS)} numbers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
