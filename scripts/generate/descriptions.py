#!/usr/bin/env python3
"""Generate the integration's entity descriptions and their names.

Five artefacts, one command each, all from tables rather than typed by hand:

* `derived` -- the computed values in `sungrow_modbus.inverter.derived`, as the
  entities that replace the YAML package's `template:` sensors;
* `numbers`, `switches`, `selects` -- one entity per row of the write table in
  [tables/writes.py](tables/writes.py), because a bound typed twice is a bound
  that will disagree with itself eventually, and the number that decides how
  far a battery discharges is not one to get wrong;
* `strings` -- every entity's name, to the convention in
  [tables/naming.py](tables/naming.py), into `strings.json` and its English
  copy under `translations/`.

`strings` reads the descriptions the other four write, so `all` runs it last.

    python scripts/generate/descriptions.py                  # write all five
    python scripts/generate/descriptions.py --check          # fail if any is stale
    python scripts/generate/descriptions.py numbers --check  # just one
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent / "tables"))
# `strings` imports the integration's descriptions to name them.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from naming import DIAGNOSTIC, modern_name
from writes import NUMBERS, SELECTS, SWITCHES

from sungrow_modbus.inverter.faults import FAULT_WORDS
from sungrow_modbus.inverter.registers import COMPONENTS

REPO = Path(__file__).resolve().parents[2]
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"
COMPONENT = REPO / "custom_components" / "sungrow_modbus"

TIER_NAMES = {5: "realtime", 10: "fast", 60: "medium", 600: "slowest"}


# --------------------------------------------------------------------------
# Shared: the entity map, and how a register row names its component


def _entities() -> list[dict[str, Any]]:
    """Return every entity the YAML package defines, from the frozen map."""
    entities: list[dict[str, Any]] = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))[
        "entities"
    ]
    return entities


def _registers() -> dict[str, dict]:
    """Return the modbus register rows, by field name."""
    # Sensors only. `switch.export_power_limit` shares its object id with
    # `sensor.export_power_limit` and points at a different register -- the
    # mode flag at 13086 rather than the value at 13073 -- so a lookup keyed
    # by object id alone silently takes whichever came last.
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in _entities()
        if e["layer"] == "modbus"
        and e["domain"] == "sensor"
        and e.get("address") is not None
    }


def _by_unique_id(domain: str) -> dict[str, dict]:
    """Return the YAML's entities of one domain, by unique_id."""
    return {
        e["unique_id"]: e
        for e in _entities()
        if e["domain"] == domain and e.get("unique_id")
    }


def _component(register: dict) -> str:
    """Return the component a register row is read by."""
    return f"{TIER_NAMES[register['scan_interval']]}_{register['input_type']}"


def _component_declaring(field: str) -> str:
    """Return the component that declares a field, from the register map itself.

    For a register the YAML never read, which has no scan interval to derive a
    component name from: it sits in a component of its own, named for it.
    """
    for attribute, component in COMPONENTS.items():
        if field in component.declared_fields:
            return attribute
    raise KeyError(field)


def _formatted(text: str, filename: str) -> str:
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
            filename,
            "-",
        ],
        ["ruff", "format", "--stdin-filename", filename, "-"],
    ):
        result = subprocess.run(
            command, input=text, capture_output=True, text=True, check=False
        )
        if result.returncode not in (0, 1):
            raise SystemExit(f"{command[1]} failed:\n{result.stderr}")
        text = result.stdout
    return text


# --------------------------------------------------------------------------
# derived: the computed values
#
# The arithmetic lives in `sungrow_modbus.inverter.derived`; this says which Home
# Assistant entity each computed value becomes, carrying the same unit, state
# class and legacy name as the `template:` sensor it replaces.
#
# The one thing that cannot be read out of the entity map is which registers a
# derived value depends on, because the YAML expresses that as a Jinja
# template over other entities. It is declared below, and it earns its keep
# twice: it decides which coordinator writes the entity -- the fastest tier it
# reads, so a derived value never lags the raw sensors behind it -- and it
# decides availability, since a value is unavailable when any component it
# reads is.

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

#: Mode registers that read as a flag, and the register each decodes.
#:
#: Not power-flow bits and not `(delay)` twins: these are whole registers
#: holding Sungrow's `0xAA`/`0x55` pair, which the YAML package exposed as the
#: number itself -- `sensor.active_power_limitation_raw` reading 170 or 85 and
#: leaving the reader to know which is which.
#:
#: There is no third one. `apl_shutdown_at_zero_raw` looks like these and is
#: deliberately **not** here: register 31213 is absent from Sungrow's
#: datasheet -- the comment that added it to the YAML says exactly that -- and
#: all three surveyed inverters read the same single value, so its enum is a
#: convention assumed rather than a pair observed. It stays a diagnostic
#: number until a machine shows a second value.
MODE_FLAGS: dict[str, tuple[str, str]] = {
    # key: (the boolean on `Derived`, the register it decodes)
    "active_power_limitation_enabled": (
        "active_power_limitation_enabled",
        "active_power_limitation_raw",
    ),
    "pv_power_limitation_enabled": (
        "pv_power_limitation_enabled",
        "pv_power_limitation_raw",
    ),
    # Outside the specification, but both codes were observed by their effect
    # (#738), which is the bar the comment above sets.
    "pv_generation_cut": ("pv_generation_cut", "pv_generation_cut_raw"),
}

#: Whether the inverter reports a problem, from Appendix 4's words.
#:
#: The two entities an owner automates on; the fifteen word sensors beside
#: them say what the problem is. Problem binary sensors rather than
#: diagnostic ones, because a fault is the one thing on this device page that
#: somebody should notice without looking for it.
PROBLEMS: dict[str, str] = {
    # key: the boolean on `Derived`
    "fault_reported": "fault_reported",
    "alarm_reported": "alarm_reported",
}

#: Seconds a power-flow bit must hold before its `(delay)` twin reports it.
#: One value for all seven, which is what the YAML uses.
DELAY_ON = 60

#: The one `filter` entity: `key` to the derived sensor it smooths and the
#: window in seconds. The YAML asks for `time_simple_moving_average` over five
#: minutes at precision 2.
#:
#: Its unit, device class and state class come from the **source**, because
#: that is where Home Assistant's own filter sensor gets them -- it copies
#: them off the source state at runtime, so the entity map has none recorded
#: for it. Copying the wrong ones freezes long-term statistics flat while raw
#: history keeps filling, which is the failure mode this project watches for.
SMOOTHED: dict[str, tuple[str, float]] = {
    "daily_consumed_energy_filtered": ("daily_consumed_energy", 300),
}

DERIVED_HEADER = '''"""Entity descriptions for the derived values, generated.

Do not edit by hand: `scripts/generate/descriptions.py derived` writes this
file, and CI checks it. The arithmetic itself lives in
`sungrow_modbus.inverter.derived`.

Each entry names the registers its value reads, which decides both the
coordinator that writes it — the fastest tier among them, so a derived value
never lags the sensors it is computed from — and when it is unavailable.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from sungrow_modbus import Capability

from .entity import SungrowBinarySensorDescription, SungrowSensorDescription

DERIVED_SENSORS: tuple[SungrowSensorDescription, ...] = (
'''


def _legacy() -> dict[str, dict]:
    """Return the YAML entities `derived` replaces, keyed by object id.

    Both the `template` layer and the one `filter` entity, which is a moving
    average of a template sensor and so is derived twice over.
    """
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in _entities()
        if e["layer"] in {"template", "filter"}
    }


#: Fields that only exist on some hardware. An entity is not created when its
#: capability is absent, rather than created and left permanently unavailable.
CAPABILITY_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("mppt3_", "MPPT3"),
    ("mppt4_", "MPPT4"),
    ("phase_b_", "THREE_PHASE"),
    ("phase_c_", "THREE_PHASE"),
    ("pv_generation_cut", "PV_GENERATION_CUT"),
    # Battery power, charge and the charging/discharging flags: an inverter
    # without a pack answers zeros or sentinels for every one of them.
    ("battery_", "BATTERY"),
)


def _requires(field: str) -> str | None:
    """Return the capability a field needs, if it needs one."""
    for prefix, capability in CAPABILITY_BY_PREFIX:
        if field.startswith(prefix):
            return capability
    return None


def _derived_description(
    field: str, key: str, depends: tuple[str, ...], legacy: dict[str, Any]
) -> list[str]:
    """Emit one description for a value computed from other registers."""
    lines: list[str] = []
    entry = legacy.get(key, {})
    lines.append("    SungrowSensorDescription(")
    lines.append(f'        key="{key}",')
    lines.append('        component="derived",')
    lines.append(f'        field="{field}",')
    lines.append(f'        translation_key="{key}",')
    if entry.get("name"):
        lines.append(f'        legacy_name="{entry["name"]}",')
    if entry.get("unique_id"):
        lines.append(f'        legacy_unique_id="{entry["unique_id"]}",')
        lines.append('        legacy_platform="template",')
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
    return lines


def _smoothed_description(
    key: str, source_key: str, window: object, legacy: dict[str, Any]
) -> list[str]:
    """Emit one description for a moving average of a derived value.

    Its device class, state class and unit come from the **source**, not
    from the smoothed entry: an average of watts is still watts, and the
    YAML entry for the filtered sensor does not restate them.
    """
    lines: list[str] = []
    entry = legacy.get(key, {})
    source_field, depends = DERIVED[source_key]
    source = legacy.get(source_key, {})
    lines.append("    SungrowSensorDescription(")
    lines.append(f'        key="{key}",')
    lines.append('        component="derived",')
    lines.append(f'        field="{source_field}",')
    lines.append(f'        translation_key="{key}",')
    if entry.get("name"):
        lines.append(f'        legacy_name="{entry["name"]}",')
    if entry.get("unique_id"):
        lines.append(f'        legacy_unique_id="{entry["unique_id"]}",')
        # Registered by the `filter` platform, not `template`, and the
        # migration finds the entity by (platform, unique_id).
        lines.append('        legacy_platform="filter",')
    lines.append(f"        depends_on={depends!r},")
    lines.append(f"        smoothed_over={window},")
    # From the source: see SMOOTHED.
    if source.get("device_class"):
        device_class = source["device_class"].upper()
        lines.append(f"        device_class=SensorDeviceClass.{device_class},")
    if source.get("state_class"):
        state_class = source["state_class"].upper()
        lines.append(f"        state_class=SensorStateClass.{state_class},")
    if source.get("unit_of_measurement"):
        lines.append(
            f'        native_unit_of_measurement="{source["unit_of_measurement"]}",'
        )
    # The YAML rounds the filtered value to two decimals. Display
    # precision does the same thing where it belongs, leaving statistics
    # the full value instead of a rounded one.
    lines.append("        suggested_display_precision=2,")
    lines.append("    ),")
    return lines


def render_derived() -> str:
    """Return the whole `derived_descriptions.py` module."""
    legacy = _legacy()
    lines = [DERIVED_HEADER]

    for field, (key, depends) in DERIVED.items():
        lines += _derived_description(field, key, depends, legacy)

    for key, (source_key, window) in SMOOTHED.items():
        lines += _smoothed_description(key, source_key, window, legacy)
    lines.append(")")

    lines.append(
        "\nDERIVED_BINARY_SENSORS: tuple[SungrowBinarySensorDescription, ...] = ("
    )
    for field, key in FLAGS.items():
        # The bit, then the twin that waits for it to hold, so the pair reads
        # together in the generated file and in a diff.
        for entity_key, delay in ((key, None), (f"{key}_delay", DELAY_ON)):
            entry = legacy.get(entity_key, {})
            lines.append("    SungrowBinarySensorDescription(")
            lines.append(f'        key="{entity_key}",')
            lines.append('        component="derived",')
            lines.append(f'        field="{field}",')
            lines.append(f'        translation_key="{entity_key}",')
            if entry.get("name"):
                lines.append(f'        legacy_name="{entry["name"]}",')
            if entry.get("unique_id"):
                lines.append(f'        legacy_unique_id="{entry["unique_id"]}",')
                lines.append('        legacy_platform="template",')
            lines.append('        depends_on=("power_flow_status",),')
            if capability := _requires(field):
                lines.append(f"        requires=Capability.{capability},")
            if delay is not None:
                lines.append(f"        delay_on={delay},")
            lines.append("    ),")

    for key, (field, register) in MODE_FLAGS.items():
        # No legacy anything: the YAML exposed the number rather than a flag,
        # so there is no id to inherit and nothing to migrate. The number it
        # replaces keeps its own history in legacy mode, where it still
        # exists.
        lines.append("    SungrowBinarySensorDescription(")
        lines.append(f'        key="{key}",')
        lines.append('        component="derived",')
        lines.append(f'        field="{field}",')
        lines.append(f'        translation_key="{key}",')
        lines.append(f"        depends_on={(register,)!r},")
        if capability := _requires(field):
            lines.append(f"        requires=Capability.{capability},")
        lines.append("        entity_category=EntityCategory.DIAGNOSTIC,")
        lines.append("    ),")

    for key, field in PROBLEMS.items():
        kind = field.removesuffix("_reported")
        depends = tuple(word.field for word in FAULT_WORDS if word.kind == kind)
        lines.append("    SungrowBinarySensorDescription(")
        lines.append(f'        key="{key}",')
        lines.append('        component="derived",')
        lines.append(f'        field="{field}",')
        lines.append(f'        translation_key="{key}",')
        lines.append(f"        depends_on={depends!r},")
        lines.append("        device_class=BinarySensorDeviceClass.PROBLEM,")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# numbers

NUMBERS_HEADER = '''"""Number descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py numbers` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

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


def render_numbers() -> str:
    """Return the whole `number_descriptions.py` module."""
    registers = _registers()
    legacy_numbers = _by_unique_id("number")
    lines = [NUMBERS_HEADER]

    for row in NUMBERS:
        register = registers[row["field"]]
        legacy = legacy_numbers[row["legacy_unique_id"]]

        lines.append("    SungrowNumberDescription(")
        lines.append(f'        key="{row["field"]}",')
        lines.append(f'        component="{_component(register)}",')
        lines.append(f'        field="{row["field"]}",')
        lines.append(f'        translation_key="{row["field"]}",')
        # The YAML's `number` entity is what a migrating user has, so its name
        # and platform are what the id is claimed through -- not the sensor's,
        # which reads the same register under a different entity id.
        lines.append(f'        legacy_name="{legacy["name"]}",')
        lines.append(f'        legacy_unique_id="{row["legacy_unique_id"]}",')
        lines.append('        legacy_platform="template",')
        # Read from the table rather than decided here. The conditional this
        # replaces said "BATTERY unless it is the export limit", which was
        # right about the export limit and wrong about the two start-power
        # thresholds: their own comment in `writes.py` says
        # `Capability.BATTERY_START_POWER` gates them, and it did not.
        if capability := row.get("requires"):
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


# --------------------------------------------------------------------------
# switches

SWITCHES_HEADER = '''"""Switch descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py switches` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is one holding register carrying 0xAA or 0x55. The specification states
both values for the first three, and the owner of an SH10RT observed both by
their effect for the fourth -- the `on` and `off` codes travel with the
description rather than being assumed.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory
from sungrow_modbus import Capability

from .entity import SungrowSwitchDescription

SWITCH_DESCRIPTIONS: tuple[SungrowSwitchDescription, ...] = (
'''


def render_switches() -> str:
    """Return the whole `switch_descriptions.py` module."""
    registers = _registers()
    legacy = _by_unique_id("switch")
    lines = [SWITCHES_HEADER]

    for row in SWITCHES:
        key = row.get("key") or row["field"].removesuffix("_raw")
        if row["field"] in registers:
            component = _component(registers[row["field"]])
        else:
            component = _component_declaring(row["field"])

        lines.append("    SungrowSwitchDescription(")
        lines.append(f'        key="{key}",')
        lines.append(f'        component="{component}",')
        lines.append(f'        field="{row["field"]}",')
        lines.append(f'        translation_key="{key}",')
        # A switch the YAML never had claims no id: there is no history to
        # continue, and inventing a legacy name would adopt somebody else's.
        if unique_id := row.get("legacy_unique_id"):
            lines.append(f'        legacy_name="{legacy[unique_id]["name"]}",')
            lines.append(f'        legacy_unique_id="{unique_id}",')
            lines.append('        legacy_platform="modbus",')
        if capability := row.get("requires"):
            lines.append(f"        requires=Capability.{capability},")
        lines.append(f"        on_value={row['on']:#04x},")
        lines.append(f"        off_value={row['off']:#04x},")
        lines.append("        entity_category=EntityCategory.CONFIG,")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# selects

SELECTS_HEADER = '''"""Select descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py selects` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is one holding register with a fixed set of values. The options and the
value each one writes come from the same row of the write table as the labels
in `strings.json`, so a label cannot drift from the value behind it.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory

from sungrow_modbus import Capability

from .entity import SungrowSelectDescription

SELECT_DESCRIPTIONS: tuple[SungrowSelectDescription, ...] = (
'''


def render_selects() -> str:
    """Return the whole `select_descriptions.py` module."""
    registers = _registers()
    legacy = _by_unique_id("select")
    lines = [SELECTS_HEADER]

    for row in SELECTS:
        register = registers[row["field"]]
        entry = legacy[row["legacy_unique_id"]]
        key = row["key"]
        slugs = [option["slug"] for option in row["options"]]
        values = {option["slug"]: option["value"] for option in row["options"]}

        lines.append("    SungrowSelectDescription(")
        lines.append(f'        key="{key}",')
        lines.append(f'        component="{_component(register)}",')
        lines.append(f'        field="{row["field"]}",')
        lines.append(f'        translation_key="{key}",')
        lines.append(f'        legacy_name="{entry["name"]}",')
        lines.append(f'        legacy_unique_id="{row["legacy_unique_id"]}",')
        lines.append('        legacy_platform="template",')
        if capability := row.get("requires"):
            lines.append(f"        requires=Capability.{capability},")
        lines.append(f"        options={slugs!r},")
        lines.append(f"        values={values!r},")
        lines.append("        entity_category=EntityCategory.CONFIG,")
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# strings: every entity's name
#
# English is the source language, so `en.json` is a copy rather than a
# translation; every other language is a real translation of it, and none of
# them is generated here.

STRINGS = COMPONENT / "strings.json"
TRANSLATION = COMPONENT / "translations" / "en.json"


def descriptions() -> list[tuple[str, str, str]]:
    """Return (domain, key, legacy name) for every entity the integration has."""
    from custom_components.sungrow_modbus.battery_descriptions import (
        BATTERY_DESCRIPTIONS,
    )
    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.external_descriptions import EXTERNAL_SENSORS
    from custom_components.sungrow_modbus.number_descriptions import NUMBER_DESCRIPTIONS
    from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
    from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
    from custom_components.sungrow_modbus.wallbox_descriptions import (
        WALLBOX_BINARY_DESCRIPTIONS,
        WALLBOX_DESCRIPTIONS,
    )

    # A specification addition has no legacy name, so its name comes from the
    # entity map, where it was written down from V1.1.11. Falling back to the
    # key instead loses whatever the key cannot carry -- "Feed-in" came out as
    # "Feed in", because a slug has no hyphens.
    added = {
        entity["entity_id"].split(".", 1)[1]: entity["name"]
        for entity in _entities()
        if entity["layer"] in {"specification", "observed"}
    }

    # The battery's entities go through the same convention as everything
    # else, deliberately. They are hand-written rather than generated, which
    # is exactly the case where a naming rule stops being enforced by
    # accident -- so they are named in `naming.OVERRIDES` like any other
    # exception and checked by `test_naming_convention.py` like any other
    # name.
    entries = [
        ("sensor", d)
        for d in (
            *SENSOR_DESCRIPTIONS,
            *DERIVED_SENSORS,
            *BATTERY_DESCRIPTIONS,
            *WALLBOX_DESCRIPTIONS,
            *EXTERNAL_SENSORS,
        )
    ]
    entries += [
        ("binary_sensor", d)
        for d in (*DERIVED_BINARY_SENSORS, *WALLBOX_BINARY_DESCRIPTIONS)
    ]
    entries += [("number", d) for d in NUMBER_DESCRIPTIONS]
    entries += [("switch", d) for d in SWITCH_DESCRIPTIONS]
    entries += [("select", d) for d in SELECT_DESCRIPTIONS]
    return [
        (
            domain,
            d.key,
            d.legacy_name or added.get(d.key) or d.key.replace("_", " ").capitalize(),
        )
        for domain, d in entries
    ]


def names() -> dict[str, dict[str, str]]:
    """Return the modern name of every entity, by domain and translation key."""
    from custom_components.sungrow_modbus.survey_entities import SURVEY_ENTITIES

    result: dict[str, dict[str, str]] = {}
    for domain, key, legacy in descriptions():
        result.setdefault(domain, {})[key] = modern_name(key, legacy)

    # The survey's own entities. They carry no `EntityDescription` -- there is
    # no register behind them -- so they are listed rather than discovered,
    # and `modern_name` finds each one in `naming.OVERRIDES`.
    for domain, key in SURVEY_ENTITIES:
        result.setdefault(domain, {})[key] = modern_name(key, "")
    return result


def option_labels() -> dict[str, dict[str, str]]:
    """Return each select's option labels, from the same table as its values.

    A label and the register value behind it come from one row, so the two
    cannot drift -- which is the whole reason the options are not written into
    strings.json by hand.
    """
    return {
        row["key"]: {option["slug"]: option["label"] for option in row["options"]}
        for row in SELECTS
    }


def render_strings() -> str:
    """Return strings.json with its `entity` block regenerated."""
    document = json.loads(STRINGS.read_text(encoding="utf-8"))
    labels = option_labels()
    entity: dict[str, dict[str, dict[str, object]]] = {}
    for domain, entries in sorted(names().items()):
        entity[domain] = {}
        for key, name in sorted(entries.items()):
            block: dict[str, object] = {"name": name}
            if domain == "select" and key in labels:
                block["state"] = labels[key]
            entity[domain][key] = block
    document["entity"] = entity
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------
# The command


class Target(NamedTuple):
    """One artefact: where it goes, how it is made, and what to call it."""

    outputs: tuple[Path, ...]
    render: Callable[[], str]
    #: Python modules go through ruff; `strings.json` does not.
    python: bool
    #: What the artefact is checked against, for the "is current" line.
    source: str


TARGETS: dict[str, Target] = {
    "derived": Target(
        (COMPONENT / "derived_descriptions.py",),
        render_derived,
        True,
        "sungrow_modbus.inverter.derived",
    ),
    "numbers": Target(
        (COMPONENT / "number_descriptions.py",), render_numbers, True, "the write table"
    ),
    "switches": Target(
        (COMPONENT / "switch_descriptions.py",),
        render_switches,
        True,
        "the write table",
    ),
    "selects": Target(
        (COMPONENT / "select_descriptions.py",),
        render_selects,
        True,
        "the write table",
    ),
    # Last: it reads what the four above write.
    "strings": Target(
        (STRINGS, TRANSLATION), render_strings, False, "the descriptions"
    ),
}


def _run(name: str, check: bool) -> bool:
    """Write one target, or check it; return whether it was current."""
    target = TARGETS[name]
    rendered = target.render()
    if target.python:
        rendered = _formatted(rendered, target.outputs[0].name)
    shown = ", ".join(str(path.relative_to(REPO)) for path in target.outputs)

    if check:
        stale = [
            path
            for path in target.outputs
            if not path.exists() or path.read_text(encoding="utf-8") != rendered
        ]
        if stale:
            print(
                f"{', '.join(str(p.relative_to(REPO)) for p in stale)} is stale.\n"
                f"Run scripts/generate/descriptions.py {name} and commit the result.",
                file=sys.stderr,
            )
            return False
        print(f"{shown} matches {target.source}")
        return True

    for path in target.outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {shown}")
    return True


def main() -> int:
    """Write the chosen artefacts, or check the committed ones are current."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("target", nargs="?", default="all", choices=[*TARGETS, "all"])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    names_ = list(TARGETS) if args.target == "all" else [args.target]
    # Every target, even after a stale one, so one run names all of them.
    results = [_run(name, args.check) for name in names_]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
