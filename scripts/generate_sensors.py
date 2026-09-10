#!/usr/bin/env python3
"""Generate the sensor entity descriptions from the YAML package.

The register map says how to decode a value; this says what Home Assistant
should do with it. Both come from the same entity map, so an entity cannot
quietly disagree with the register it reads or with the YAML entry it replaces.

Two fields carry the migration. `legacy_name` is the name the YAML used, which
is what a legacy-mode entity sets so its entity_id comes out byte for byte the
same. And the unit together with the state class must match the YAML entry
exactly: a replacement in a different unit class freezes long-term statistics
flat while raw history keeps filling, which looks like nothing at all.

    python scripts/generate_sensors.py            # write the module
    python scripts/generate_sensors.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layout import component_for
from naming import DIAGNOSTIC, LEGACY_ONLY_SENSORS

REPO = Path(__file__).resolve().parent.parent
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
OUTPUT = REPO / "custom_components" / "sungrow_modbus" / "sensor_descriptions.py"

TIER_NAMES = {5: "realtime", 10: "fast", 60: "medium", 600: "slowest"}

HEADER = '''"""Sensor descriptions, generated from the YAML package.

Do not edit by hand: `scripts/generate_sensors.py` writes this file from
`doc/legacy_entity_map.json`, and CI checks that it matches.

Every entry carries the unit and state class of the YAML entry it replaces,
because a replacement in a different unit class silently freezes long-term
statistics, and `legacy_name`, which is what legacy mode sets so the
entity_id comes out identical to the one a user already has. The modern name
is not here: it lives in `strings.json` under `translation_key`, so it can be
translated.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from sungrow_modbus import Capability

from .entity import SungrowSensorDescription

SENSOR_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
'''


def _entities() -> list[dict]:
    """Return the modbus sensors, in entity_id order."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return sorted(
        (
            e
            for e in entities
            if e["layer"] in {"modbus", "specification"}
            and e.get("address") is not None
            and e["domain"] == "sensor"
            and e.get("scan_interval") in TIER_NAMES
        ),
        key=lambda e: e["entity_id"],
    )


#: Fields that only exist on some hardware. An entity is not created when its
#: capability is absent, rather than created and left permanently unavailable.
CAPABILITY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("mppt3_", "MPPT3"),
    ("mppt4_", "MPPT4"),
    ("phase_b_", "THREE_PHASE"),
    ("phase_c_", "THREE_PHASE"),
    # From the specification rather than the YAML: a second meter channel
    # needs a dual-channel meter, and PV power limitation is SHT-only.
    ("meter_channel_2_", "METER_CHANNEL_2"),
    ("feed_in_limitation_ratio", "FEED_IN_LIMITATION_RATIO"),
    ("pv_power_limitation_raw", "PV_POWER_LIMITATION"),
    # Two firmware strings the reference SH10RT cannot read at all. Gated so
    # they are absent rather than permanently unavailable; see
    # `scripts/layout.py` for why each is read on its own.
    ("sungrow_version_3", "SUB_CONTROLLER_FIRMWARE"),
    ("sungrow_version_4_sungrow_battery", "BATTERY_FIRMWARE"),
)


def _requires(field: str) -> str | None:
    """Return the capability a field needs, if it needs one."""
    for prefix, capability in CAPABILITY_BY_PREFIX:
        if field.startswith(prefix):
            return capability
    return None


def render() -> str:
    """Return the whole generated module."""
    lines = [HEADER]
    for entity in _entities():
        key = entity["entity_id"].split(".", 1)[1]
        component = component_for(
            key, TIER_NAMES[entity["scan_interval"]], entity["input_type"]
        )
        lines.append("    SungrowSensorDescription(")
        lines.append(f'        key="{key}",')
        lines.append(f'        component="{component}",')
        lines.append(f'        field="{key}",')
        lines.append(f'        translation_key="{key}",')
        if entity["layer"] == "modbus":
            # Only a YAML entity has an id worth inheriting; these fields are
            # what the migration identifies and claims by.
            lines.append(f'        legacy_name="{entity["name"]}",')
            lines.append(f'        legacy_unique_id="{entity["unique_id"]}",')
            lines.append('        legacy_platform="modbus",')
        capability = _requires(key)
        if capability:
            lines.append(f"        requires=Capability.{capability},")
        if key in DIAGNOSTIC:
            lines.append("        entity_category=EntityCategory.DIAGNOSTIC,")
        if key in LEGACY_ONLY_SENSORS:
            lines.append("        legacy_only=True,")
        if entity.get("device_class"):
            device_class = entity["device_class"].upper()
            lines.append(f"        device_class=SensorDeviceClass.{device_class},")
        if entity.get("state_class"):
            state_class = entity["state_class"].upper()
            lines.append(f"        state_class=SensorStateClass.{state_class},")
        if entity.get("unit_of_measurement"):
            unit = entity["unit_of_measurement"]
            lines.append(f'        native_unit_of_measurement="{unit}",')
        if entity.get("precision") is not None:
            lines.append(f"        suggested_display_precision={entity['precision']},")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _formatted(text: str) -> str:
    """Return the text as ruff would format it."""
    for command in (
        # Import order first, then formatting: the fixer can leave lines the
        # formatter would rewrap.
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
                "Run scripts/generate_sensors.py and commit the result.",
                file=sys.stderr,
            )
            return 1
        print(f"{OUTPUT.relative_to(REPO)} matches the entity map")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO)}: {len(_entities())} sensors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
