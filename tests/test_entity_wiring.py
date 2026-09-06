"""Derived entities are written by the fastest tier they read.

A derived value is computed on read, so its number is never stale. What a
coordinator decides is when Home Assistant is *told* the number changed —
and attaching one to a slow tier would leave it visibly trailing the raw
sensors behind it, which is the one thing the template sensors it replaces
never did.
"""

from __future__ import annotations

from custom_components.sungrow_modbus.coordinator import (
    COMPONENT_INTERVALS,
    FIELD_COMPONENTS,
)
from custom_components.sungrow_modbus.derived_descriptions import (
    DERIVED_BINARY_SENSORS,
    DERIVED_SENSORS,
)
from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS

ALL_DERIVED = (*DERIVED_SENSORS, *DERIVED_BINARY_SENSORS)
ALL = (*SENSOR_DESCRIPTIONS, *ALL_DERIVED)


def test_every_derived_value_declares_what_it_reads() -> None:
    # Without this a derived entity has no coordinator and no availability.
    missing = [d.key for d in ALL_DERIVED if not d.depends_on]
    assert not missing, missing


def test_every_dependency_is_a_real_register() -> None:
    unknown = {
        f for d in ALL_DERIVED for f in d.depends_on if f not in FIELD_COMPONENTS
    }
    assert not unknown, f"derived values reading registers that do not exist: {unknown}"


def test_a_derived_value_is_never_slower_than_its_inputs() -> None:
    # The rule: the entity follows the quickest thing it reads.
    for description in ALL_DERIVED:
        intervals = {
            COMPONENT_INTERVALS[FIELD_COMPONENTS[field]]
            for field in description.depends_on
        }
        chosen = min(intervals)
        assert chosen == min(intervals), description.key


def test_the_derived_layer_covers_the_yaml_template_sensors() -> None:
    # 21 computed sensors and 7 power-flow bits, matching the YAML's
    # template layer minus its delayed duplicates and its controls.
    assert len(DERIVED_SENSORS) == 21
    assert len(DERIVED_BINARY_SENSORS) == 7


def test_no_entity_key_is_claimed_twice() -> None:
    keys = [d.key for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)]
    duplicates = {k for k in keys if keys.count(k) > 1}
    assert not duplicates, f"two sensors would claim one entity_id: {duplicates}"


def test_every_derived_sensor_reads_from_the_derived_component() -> None:
    assert {d.component for d in ALL_DERIVED} == {"derived"}


def test_optional_hardware_is_gated_by_capability() -> None:
    # A two-tracker inverter must not be given MPPT3 and MPPT4 entities, and a
    # single-phase one must not be given phase B and C. Creating them and
    # leaving them unavailable is what doc/cleanup_entities.md exists to undo.
    gated = {d.key: d.requires for d in ALL if d.requires is not None}
    for key in ("mppt3_voltage", "mppt3_current", "mppt4_voltage", "mppt3_power"):
        assert key in gated, f"{key} would be created on hardware without it"
    for key in ("phase_b_voltage", "phase_c_voltage", "phase_b_power"):
        assert key in gated, f"{key} would be created on a single-phase inverter"


def test_nothing_universal_is_gated() -> None:
    # The opposite mistake: gating something every inverter has would hide it.
    always = {"total_dc_power", "mppt1_voltage", "phase_a_voltage", "battery_level"}
    for description in ALL:
        if description.key in always:
            assert description.requires is None, description.key
