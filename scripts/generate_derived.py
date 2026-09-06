#!/usr/bin/env python3
"""Generate entity descriptions for the derived values.

The arithmetic lives in `sungrow_modbus.derived`; this says which Home
Assistant entity each computed value becomes, carrying the same unit, state
class and legacy name as the `template:` sensor it replaces.

The one thing that cannot be read out of the entity map is which registers a
derived value depends on, because the YAML expresses that as a Jinja template
over other entities. It is declared below, and it earns its keep twice: it
decides which coordinator writes the entity — the fastest tier it reads, so a
derived value never lags the raw sensors behind it — and it decides
availability, since a value is unavailable when any component it reads is.

    python scripts/generate_derived.py            # write the module
    python scripts/generate_derived.py --check    # fail if it is stale
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from naming import DIAGNOSTIC

REPO = Path(__file__).resolve().parent.parent
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
OUTPUT = REPO / "custom_components" / "sungrow_modbus" / "derived_descriptions.py"

_DAILY = (
    "daily_pv_generation",
    "daily_exported_energy",
    "daily_imported_energy",
    "daily_battery_charge",
    "daily_battery_discharge",
)
_TOTAL = tuple(f.replace("daily_", "total_") for f in _DAILY)
_SOC = ("battery_min_soc", "battery_max_soc")
_CAPACITY = ("battery_capacity_high_precision",)

#: Derived value to (the YAML entity it replaces, the registers it reads).
DERIVED: dict[str, tuple[str, tuple[str, ...]]] = {
    "mppt1_power": ("mppt1_power", ("mppt1_voltage", "mppt1_current")),
    "mppt2_power": ("mppt2_power", ("mppt2_voltage", "mppt2_current")),
    "mppt3_power": ("mppt3_power", ("mppt3_voltage", "mppt3_current")),
    "mppt4_power": ("mppt4_power", ("mppt4_voltage", "mppt4_current")),
    "phase_a_power": ("phase_a_power", ("phase_a_voltage", "phase_a_current")),
    "phase_b_power": ("phase_b_power", ("phase_b_voltage", "phase_b_current")),
    "phase_c_power": ("phase_c_power", ("phase_c_voltage", "phase_c_current")),
    "inverter_state": ("sungrow_inverter_state", ("running_state_raw",)),
    "sungrow_device_type": ("sungrow_device_type", ("sungrow_device_type_code",)),
    "battery_charging_power_signed": (
        "battery_charging_power_signed",
        ("battery_power",),
    ),
    "battery_charging_power": ("battery_charging_power", ("battery_power",)),
    "battery_discharging_power_signed": (
        "battery_discharging_power_signed",
        ("battery_power",),
    ),
    "battery_discharging_power": ("battery_discharging_power", ("battery_power",)),
    "export_power": ("export_power", ("export_power_raw",)),
    "import_power": ("import_power", ("export_power_raw",)),
    "battery_level_nominal": ("battery_level_nominal", (*_SOC, "battery_level")),
    "battery_charge_nominal": (
        "battery_charge_nominal",
        (*_SOC, "battery_level", *_CAPACITY),
    ),
    "battery_charge": ("battery_charge", (*_SOC, *_CAPACITY)),
    "battery_charge_health_rated": (
        "battery_charge_health_rated",
        (*_SOC, *_CAPACITY, "battery_state_of_health"),
    ),
    "daily_consumed_energy": ("daily_consumed_energy", _DAILY),
    "total_consumed_energy": ("total_consumed_energy", _TOTAL),
}

#: The seven bits of the power flow status register.
FLAGS: dict[str, str] = {
    "pv_generating": "pv_generating",
    "battery_charging": "battery_charging",
    "battery_discharging": "battery_discharging",
    "positive_load_power": "positive_load_power",
    "exporting_power": "exporting_power",
    "importing_power": "importing_power",
    "negative_load_power": "negative_load_power",
}

HEADER = '''"""Entity descriptions for the derived values, generated.

Do not edit by hand: `scripts/generate_derived.py` writes this file, and CI
checks it. The arithmetic itself lives in `sungrow_modbus.derived`.

Each entry names the registers its value reads, which decides both the
coordinator that writes it — the fastest tier among them, so a derived value
never lags the sensors it is computed from — and when it is unavailable.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from sungrow_modbus import Capability

from .entity import SungrowBinarySensorDescription, SungrowSensorDescription

DERIVED_SENSORS: tuple[SungrowSensorDescription, ...] = (
'''


def _legacy() -> dict[str, dict]:
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["entity_id"].split(".", 1)[1]: e for e in entities if e["layer"] == "template"
    }


#: Fields that only exist on some hardware. An entity is not created when its
#: capability is absent, rather than created and left permanently unavailable.
CAPABILITY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("mppt3_", "MPPT3"),
    ("mppt4_", "MPPT4"),
    ("phase_b_", "THREE_PHASE"),
    ("phase_c_", "THREE_PHASE"),
)


def _requires(field: str) -> str | None:
    """Return the capability a field needs, if it needs one."""
    for prefix, capability in CAPABILITY_BY_PREFIX:
        if field.startswith(prefix):
            return capability
    return None


def render() -> str:
    """Return the whole generated module."""
    legacy = _legacy()
    lines = [HEADER]

    for field, (key, depends) in DERIVED.items():
        entry = legacy.get(key, {})
        lines.append("    SungrowSensorDescription(")
        lines.append(f'        key="{key}",')
        lines.append('        component="derived",')
        lines.append(f'        field="{field}",')
        lines.append(f'        translation_key="{key}",')
        if entry.get("name"):
            lines.append(f'        legacy_name="{entry["name"]}",')
        lines.append(f"        depends_on={depends!r},")
        capability = _requires(field)
        if capability:
            lines.append(f"        requires=Capability.{capability},")
        if key in DIAGNOSTIC:
            lines.append("        entity_category=EntityCategory.DIAGNOSTIC,")
        if entry.get("device_class"):
            device_class = entry["device_class"].upper()
            lines.append(f"        device_class=SensorDeviceClass.{device_class},")
        if entry.get("state_class"):
            state_class = entry["state_class"].upper()
            lines.append(f"        state_class=SensorStateClass.{state_class},")
        if entry.get("unit_of_measurement"):
            lines.append(
                f'        native_unit_of_measurement="{entry["unit_of_measurement"]}",'
            )
        lines.append("    ),")
    lines.append(")")

    lines.append(
        "\nDERIVED_BINARY_SENSORS: tuple[SungrowBinarySensorDescription, ...] = ("
    )
    for field, key in FLAGS.items():
        entry = legacy.get(key, {})
        lines.append("    SungrowBinarySensorDescription(")
        lines.append(f'        key="{key}",')
        lines.append('        component="derived",')
        lines.append(f'        field="{field}",')
        lines.append(f'        translation_key="{key}",')
        if entry.get("name"):
            lines.append(f'        legacy_name="{entry["name"]}",')
        lines.append('        depends_on=("power_flow_status",),')
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
            print(f"{OUTPUT.relative_to(REPO)} is stale.", file=sys.stderr)
            return 1
        print(f"{OUTPUT.relative_to(REPO)} is current")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        f"Wrote {OUTPUT.relative_to(REPO)}: {len(DERIVED)} sensors, {len(FLAGS)} flags"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
