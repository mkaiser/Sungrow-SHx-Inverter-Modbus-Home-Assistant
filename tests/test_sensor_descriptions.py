"""Every sensor must match the YAML entry it replaces.

This is the freeze-flat trap made mechanical. Long-term statistics pin the
unit: a replacement entity in a different unit class is dropped from
normalisation, and statistics then repeat the last value forever while raw
history keeps filling. Nothing looks broken — the Energy dashboard simply
reads as a house producing nothing — so the only way to catch it is to compare
every entity against what it replaces, before anybody runs it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.util.unit_conversion import (
    ElectricCurrentConverter,
    ElectricPotentialConverter,
    EnergyConverter,
    PowerConverter,
    TemperatureConverter,
)

ENTITY_MAP = Path(__file__).resolve().parent.parent / "doc" / "legacy_entity_map.json"

#: The converters decide what "same unit class" means, so they are the
#: authority here rather than a list of units written out by hand.
CONVERTERS = (
    EnergyConverter,
    PowerConverter,
    ElectricCurrentConverter,
    ElectricPotentialConverter,
    TemperatureConverter,
)

BY_KEY = {d.key: d for d in SENSOR_DESCRIPTIONS}
LEGACY = {
    e["entity_id"].split(".", 1)[1]: e
    for e in json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    if e["layer"] == "modbus" and e["domain"] == "sensor"
}


def _unit_class(unit: str | None) -> str | None:
    """Return the name of the converter that owns a unit, if any owns it."""
    for converter in CONVERTERS:
        if unit in converter.VALID_UNITS:
            return converter.__name__
    return None


def test_every_yaml_sensor_has_a_description() -> None:
    missing = {k for k in LEGACY if k not in BY_KEY}
    # Anything here would silently not be recreated on migration.
    assert not missing, f"YAML sensors with no replacement: {sorted(missing)[:10]}"


@pytest.mark.parametrize("key", sorted(LEGACY))
def test_unit_and_state_class_match_the_yaml(key: str) -> None:
    description = BY_KEY[key]
    legacy = LEGACY[key]

    assert description.native_unit_of_measurement == legacy.get(
        "unit_of_measurement"
    ), "unit"
    assert (
        description.state_class.value if description.state_class else None
    ) == legacy.get("state_class"), "state class"
    assert (
        description.device_class.value if description.device_class else None
    ) == legacy.get("device_class"), "device class"


@pytest.mark.parametrize("key", sorted(LEGACY))
def test_the_unit_class_is_unchanged(key: str) -> None:
    # The deeper property: even a unit that differs is survivable if it is in
    # the same class, because the recorder converts. A different class is not.
    description = BY_KEY[key]
    legacy = LEGACY[key]
    assert _unit_class(description.native_unit_of_measurement) == _unit_class(
        legacy.get("unit_of_measurement")
    ), "unit class"


def test_statistics_bearing_sensors_carry_a_unit() -> None:
    # A state class with no unit cannot be checked at all, in either direction.
    offenders = [
        d.key
        for d in SENSOR_DESCRIPTIONS
        if d.state_class in {SensorStateClass.TOTAL, SensorStateClass.TOTAL_INCREASING}
        and not d.native_unit_of_measurement
    ]
    assert not offenders, offenders


def test_energy_totals_are_not_measurement() -> None:
    # A total recorded as `measurement` produces no long-term statistics at
    # all, which is the other way to lose the Energy dashboard quietly.
    offenders = [
        d.key
        for d in SENSOR_DESCRIPTIONS
        if d.device_class is SensorDeviceClass.ENERGY
        and d.state_class is SensorStateClass.MEASUREMENT
    ]
    assert not offenders, offenders


#: Registers the specification defines that the YAML never read. They have no
#: YAML entry to be compared against, so they are checked against the entity
#: map, which is where their definition was written down from V1.1.11 --
#: or, for an `observed` one, from the hardware that answered it.
ADDED = {
    e["entity_id"].split(".", 1)[1]: e
    for e in json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    if e["layer"] in {"specification", "observed"} and e["domain"] == "sensor"
}

#: Additions that are an entity on another platform instead of a sensor. The
#: map records a sensor because the specification lists a register; a
#: register an owner sets is a control rather than a reading.
NOT_A_SENSOR: dict[str, str] = {
    # 13017 reads back 0xAA and 0x55; `writes.SWITCHES` explains.
    "forced_startup_under_low_soc_raw": "switch.forced_startup_under_low_soc",
}
for _key in NOT_A_SENSOR:
    del ADDED[_key]

#: Additions read only as an input to a derived value, which is where the
#: reading goes: no entity of their own, because it would show the same
#: quantity twice. Each names the derived sensor that reads it.
INPUT_ONLY: dict[str, str] = {
    # 13022, unsigned: the battery term of the self consumption where 5214
    # is refused, signed by 13001's bits. 5214 is the battery power entity.
    "battery_power_unsigned": "inverter_self_consumption",
}
for _key in INPUT_ONLY:
    del ADDED[_key]


def test_an_input_only_addition_is_read_by_the_value_it_names() -> None:
    """Declared input-only, so it must be an input: otherwise it is dropped."""
    from custom_components.sungrow_modbus.derived_descriptions import DERIVED_SENSORS

    derived = {d.key: d for d in DERIVED_SENSORS}
    for field, key in INPUT_ONLY.items():
        assert field in derived[key].depends_on, (field, key)


def test_an_addition_that_is_not_a_sensor_names_what_it_became() -> None:
    from custom_components.sungrow_modbus.button_descriptions import BUTTON_DESCRIPTIONS
    from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS

    controls = {f"button.{d.key}": d.field for d in BUTTON_DESCRIPTIONS} | {
        f"switch.{d.key}": d.field for d in SWITCH_DESCRIPTIONS
    }
    for field, entity in NOT_A_SENSOR.items():
        assert field not in BY_KEY
        assert controls.get(entity) == field


def test_the_specification_additions_all_became_entities() -> None:
    assert set(ADDED) <= set(BY_KEY), sorted(set(ADDED) - set(BY_KEY))


@pytest.mark.parametrize("key", sorted(ADDED))
def test_an_addition_matches_what_the_specification_says(key: str) -> None:
    """The same check as for a YAML entity, against the source it came from.

    A guessed scale produces a plausible wrong number, so the values in the
    map were read out of the specification rather than inferred — and this is
    what stops a description drifting away from them afterwards.
    """
    description = BY_KEY[key]
    added = ADDED[key]

    assert description.native_unit_of_measurement == added.get("unit_of_measurement"), (
        "unit"
    )
    assert (
        description.state_class.value if description.state_class else None
    ) == added.get("state_class"), "state class"
    assert (
        description.device_class.value if description.device_class else None
    ) == added.get("device_class"), "device class"


def test_an_addition_has_nothing_to_migrate_from() -> None:
    """No YAML entity, so no id to inherit -- and claiming one would be wrong."""
    for key in ADDED:
        description = BY_KEY[key]
        assert description.legacy_name is None
        assert description.legacy_unique_id is None
        assert description.legacy_platform is None


def test_every_dropped_sensor_names_a_replacement_that_exists() -> None:
    """Nothing is dropped in modern mode unless the reading went somewhere.

    A clean cut removes duplication, not capability, and the only way to tell
    which is being removed is to say where the reading went instead. So each
    entry in `LEGACY_ONLY_SENSORS` names its replacement, and this asserts
    that the replacement is one of the entities modern mode *does* create.

    The first version of this test derived the replacement from the name
    instead -- and passed for fifteen of the seventeen while guessing at
    `export_power_raw` and `running_state_raw`, whose counterparts are
    derived sensors and, in the second case, under an entirely different key.
    A test that agrees with a guess is worth nothing.
    """
    from pathlib import Path as _Path
    import sys

    sys.path.insert(
        0,
        str(
            _Path(__file__).resolve().parent.parent / "scripts" / "generate" / "tables"
        ),
    )
    from naming import LEGACY_ONLY_SENSORS

    from custom_components.sungrow_modbus.derived_descriptions import (
        DERIVED_BINARY_SENSORS,
        DERIVED_SENSORS,
    )
    from custom_components.sungrow_modbus.number_descriptions import NUMBER_DESCRIPTIONS
    from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS
    from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS

    exists = (
        # Binary sensors count: two replacements are one.
        {f"binary_sensor.{d.translation_key}" for d in DERIVED_BINARY_SENSORS}
        | {f"number.{d.translation_key}" for d in NUMBER_DESCRIPTIONS}
        | {f"select.{d.translation_key}" for d in SELECT_DESCRIPTIONS}
        | {f"switch.{d.translation_key}" for d in SWITCH_DESCRIPTIONS}
        | {
            f"sensor.{d.translation_key}"
            for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)
            if not getattr(d, "legacy_only", False)
        }
    )

    for dropped, replacement in sorted(LEGACY_ONLY_SENSORS.items()):
        assert replacement in exists, (
            f"{dropped} is dropped in modern mode and its stated replacement "
            f"{replacement} does not exist, so this is lost capability"
        )
        assert replacement != f"sensor.{dropped}", dropped


def test_the_register_with_nothing_better_is_kept() -> None:
    """What is left of the four, and why it stayed.

    Three of the four became something better and are therefore dropped:
    13089 and 13018 are Sungrow mode registers, and 31213 holds the same
    0xAA/0x55 pair -- undocumented, but the diagnoses read both codes on it
    (issue #554's pair, wiki: register 31213) -- so a binary sensor decodes
    each.

    **13090 was never raw**: it has a scale and a unit and reads 100.0 % on
    every machine diagnosed, so it only needed the word taken out of its name.
    """
    kept = {
        description.translation_key
        for description in SENSOR_DESCRIPTIONS
        if not description.legacy_only
    }
    assert "active_power_limitation_ratio_raw" in kept, (
        "dropped without anything replacing it"
    )


def test_legacy_mode_keeps_everything_and_modern_mode_does_not() -> None:
    """`serves` answers the mode question, so no platform has to.

    The legacy-only sensors exist for an entry that took over the YAML package's ids and
    for nothing else. Asserted through `serves` rather than by reading the
    flag, because the flag is only correct if something consults it -- and
    for a while nothing did.
    """
    from custom_components.sungrow_modbus.coordinator import SungrowRuntimeData

    dropped = [d for d in SENSOR_DESCRIPTIONS if d.legacy_only]
    assert len(dropped) == 21

    # Every capability granted, so the *only* thing under test is the mode.
    # Without it `pv_power_limitation_raw` is refused for requiring a
    # capability the fixture never granted -- which would have passed the
    # "modern does not serve it" half of this test for the wrong reason.
    from sungrow_modbus.hybrid_inverter.capabilities import Capability

    components = {description.component for description in dropped}
    everything = frozenset(Capability)
    legacy = SungrowRuntimeData(
        coordinators=dict.fromkeys(components),
        capabilities=everything,
        legacy_ids=True,
    )
    modern = SungrowRuntimeData(
        coordinators=dict.fromkeys(components),
        capabilities=everything,
        legacy_ids=False,
    )
    for description in dropped:
        assert legacy.serves(description), description.translation_key
        assert not modern.serves(description), description.translation_key

    # And a sensor that is not legacy-only is served either way.
    ordinary = next(d for d in SENSOR_DESCRIPTIONS if not d.legacy_only)
    both = SungrowRuntimeData(
        coordinators=dict.fromkeys([ordinary.component]),
        capabilities=everything,
        legacy_ids=False,
    )
    assert both.serves(ordinary)


def test_a_3p3l_inverter_gets_no_phase_voltages() -> None:
    """On 3P3L, 5019-5021 are line voltages, so nothing built on them is made.

    The three voltages and the three powers computed from them, and nothing
    else: the phase currents are still phase currents.
    """
    from custom_components.sungrow_modbus.coordinator import SungrowRuntimeData
    from custom_components.sungrow_modbus.derived_descriptions import DERIVED_SENSORS
    from sungrow_modbus.hybrid_inverter.capabilities import (
        LINE_VOLTAGE_OUTPUT_TYPE,
        Capability,
    )

    descriptions = (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)
    gated = {"phase_a_voltage", "phase_b_voltage", "phase_c_voltage"} | {
        "phase_a_power",
        "phase_b_power",
        "phase_c_power",
    }

    def served(output_type: int | None) -> set[str]:
        runtime = SungrowRuntimeData(
            coordinators=dict.fromkeys(
                {d.component for d in SENSOR_DESCRIPTIONS} | {"derived"}
            ),
            capabilities=frozenset(Capability),
            legacy_ids=False,
            output_type=output_type,
        )
        return {d.key for d in descriptions if runtime.serves(d)}

    four_wire = served(1)
    assert gated <= four_wire
    assert served(None) == four_wire
    assert four_wire - served(LINE_VOLTAGE_OUTPUT_TYPE) == gated


# `sensor_descriptions.py` is edited by hand. These make the properties below
# true by assertion, so a hand edit cannot quietly undo one.


def _tables():
    """Return `naming`'s two tables, which this file has to follow."""
    import sys

    tables = Path(__file__).resolve().parent.parent / "scripts" / "generate" / "tables"
    sys.path.insert(0, str(tables))
    from naming import DIAGNOSTIC, LEGACY_ONLY_SENSORS

    return DIAGNOSTIC, LEGACY_ONLY_SENSORS


@pytest.mark.parametrize("key", sorted(LEGACY))
def test_the_legacy_identity_is_the_yamls(key: str) -> None:
    """What the migration claims an entity by has to be the YAML's, exactly.

    A wrong `legacy_unique_id` finds nothing to adopt, and a wrong
    `legacy_name` produces a different entity id -- either way a user's
    history is left behind under the old id, with nothing looking broken.
    """
    description, entry = BY_KEY[key], LEGACY[key]
    assert description.field == key
    assert description.translation_key == key
    assert description.legacy_name == entry["name"]
    assert description.legacy_unique_id == entry["unique_id"]
    assert description.legacy_platform == "modbus"
    expected_class = (entry.get("device_class") or "").upper() or None
    actual_class = description.device_class.name if description.device_class else None
    assert actual_class == expected_class, "device class"
    assert description.suggested_display_precision == entry.get("precision")


@pytest.mark.parametrize("description", SENSOR_DESCRIPTIONS, ids=lambda d: d.key)
def test_the_component_named_is_the_one_that_reads_the_field(description) -> None:
    """An entity names its component by string; a wrong one finds nothing.

    It is easy to leave a field pointing at its tier's pooled component after
    `registers.py` moves it into one of its own.
    """
    from custom_components.sungrow_modbus.coordinator import FIELD_COMPONENTS

    assert FIELD_COMPONENTS[description.field] == description.component


def test_exactly_the_tabled_sensors_are_legacy_only() -> None:
    """`naming.LEGACY_ONLY_SENSORS` is the list; the flag has to follow it."""
    _diagnostic, legacy_only = _tables()
    flagged = {d.key for d in SENSOR_DESCRIPTIONS if d.legacy_only}
    assert flagged == set(legacy_only)


def test_exactly_the_diagnostic_sensors_are_in_the_diagnostic_category() -> None:
    """`naming.DIAGNOSTIC` decides the category, for sensors as for the rest."""
    from homeassistant.const import EntityCategory

    diagnostic, _legacy_only = _tables()
    for description in SENSOR_DESCRIPTIONS:
        is_diagnostic = description.entity_category is EntityCategory.DIAGNOSTIC
        assert is_diagnostic == (description.key in diagnostic), description.key
