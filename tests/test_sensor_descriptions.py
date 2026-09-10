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
#: map, which is where their definition was written down from V1.1.11.
ADDED = {
    e["entity_id"].split(".", 1)[1]: e
    for e in json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    if e["layer"] == "specification" and e["domain"] == "sensor"
}


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

    sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "scripts"))
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


def test_the_two_registers_with_nothing_better_are_kept() -> None:
    """What is left of the four, and why each one stayed.

    Two of the four became something better and are therefore dropped: 13089
    and 13018 are Sungrow mode registers, and a binary sensor now decodes
    each.

    The two here stay for opposite reasons. **13090 was never raw** -- it has
    a scale and a unit and reads 100.0 % on every machine surveyed -- so it
    only needed the word taken out of its name. **31213 is undocumented**:
    absent from Sungrow's protocol document, contributed through community
    feedback in issue #554, untested here, and all three surveyed inverters
    read the same single value -- so its 0xAA/0x55 pair is a convention
    assumed rather than a pair observed. Making it a flag would be a guess
    wearing a decode, and this test fails if somebody does it.
    """
    kept = {
        description.translation_key
        for description in SENSOR_DESCRIPTIONS
        if not description.legacy_only
    }
    for key in ("active_power_limitation_ratio_raw", "apl_shutdown_at_zero_raw"):
        assert key in kept, f"{key} was dropped without anything replacing it"


def test_legacy_mode_keeps_everything_and_modern_mode_does_not() -> None:
    """`serves` answers the mode question, so no platform has to.

    The seventeen exist for an entry that took over the YAML package's ids and
    for nothing else. Asserted through `serves` rather than by reading the
    flag, because the flag is only correct if something consults it -- and
    for a while nothing did.
    """
    from custom_components.sungrow_modbus.coordinator import SungrowRuntimeData

    dropped = [d for d in SENSOR_DESCRIPTIONS if d.legacy_only]
    assert len(dropped) == 19

    # Every capability granted, so the *only* thing under test is the mode.
    # Without it `pv_power_limitation_raw` is refused for requiring a
    # capability the fixture never granted -- which would have passed the
    # "modern does not serve it" half of this test for the wrong reason.
    from sungrow_modbus.capabilities import Capability

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
