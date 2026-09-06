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


@pytest.mark.parametrize("key", sorted(BY_KEY))
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


@pytest.mark.parametrize("key", sorted(BY_KEY))
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
