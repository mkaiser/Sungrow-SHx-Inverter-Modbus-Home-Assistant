"""Entity descriptions for an SBR pack, hand-written for a stated reason.

`sensor_descriptions.py` is **generated** from `doc/legacy_entity_map.json`,
which is derived from `legacy/modbus_sungrow.yaml` -- the inverter's map. The
pack's registers are not in it, because they live in
`legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`, an opt-in file a
user copies in by hand. So there is nothing to generate these from, exactly as
there was nothing to generate `sungrow_modbus.battery_registers` from, and
they are hand-written for the same reason and guarded the same way:
`tests/test_battery_entities.py` checks every `field` here against a real
field or property on the components.

**No `legacy_name`, and that is a decision.** The migration reproduces the
YAML package's entity ids, and these are not in it -- the additional file is
not part of the package, is not in the entity map, and is installed by
copy-paste rather than by including a file. A user who did copy it in has ids
like `sensor.sg_battery_1_max_voltage_of_cell`, and those are **not**
adopted here. Recorded in `doc/integration_plan.md` as an open question with
its cost: this integration would be taking over entities it never generated,
whose names it does not control, on evidence no fingerprint carries. Doing
that silently is worse than not doing it.

Seventeen entities from seventeen registers, which is a coincidence rather
than a mapping. Eleven fields become eleven entities; the four packed position
words become **six**, because 780 is not a cell anybody can look up -- see
`SbrBatteryCells` for the encoding and the reading that proves it. The raw
words themselves get no entity, which is what modern mode does with a `_raw`
value everywhere else.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfTemperature,
)

from .entity import SungrowSensorDescription

#: The pack's own summary, which answers on every path a pack answers on at
#: all -- measured through a dongle and over a cable with identical values.
PACK_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="battery_pack_voltage",
        component="pack",
        field="voltage",
        translation_key="battery_pack_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_pack_current",
        component="pack",
        field="current",
        translation_key="battery_pack_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_pack_temperature",
        component="pack",
        field="temperature",
        translation_key="battery_pack_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_pack_level",
        component="pack",
        field="state_of_charge",
        translation_key="battery_pack_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_pack_state_of_health",
        component="pack",
        field="state_of_health",
        translation_key="battery_pack_state_of_health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # `total_increasing` rather than `total`, matching how the inverter's own
    # lifetime counters are declared: the pack's figure only climbs, and the
    # class is what tells long-term statistics to treat a reset as a new
    # cycle rather than as a negative delta.
    SungrowSensorDescription(
        key="battery_pack_total_charge",
        component="pack",
        field="total_charge",
        translation_key="battery_pack_total_charge",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_pack_total_discharge",
        component="pack",
        field="total_discharge",
        translation_key="battery_pack_total_discharge",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
)

#: The cell-level detail, which **a WiNet-S does not forward**.
#:
#: Created only where the block gave a non-zero reading. Both ways a dongle
#: loses it were measured: fwitten's refuses with exception 0x02, bar12's
#: answers zeros. The second is why a reading is required rather than a
#: successful read -- eight entities reporting 0 V and module 0 forever, with
#: nothing that ever removes an entity, is the failure `ZERO_MEANS_ABSENT`
#: exists to prevent.
CELL_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="battery_max_cell_voltage",
        component="cells",
        field="max_cell_voltage",
        translation_key="battery_max_cell_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
    ),
    SungrowSensorDescription(
        key="battery_min_cell_voltage",
        component="cells",
        field="min_cell_voltage",
        translation_key="battery_min_cell_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
    ),
    SungrowSensorDescription(
        key="battery_max_module_temperature",
        component="cells",
        field="max_module_temperature",
        translation_key="battery_max_module_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="battery_min_module_temperature",
        component="cells",
        field="min_module_temperature",
        translation_key="battery_min_module_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    # The unpacked halves. Diagnostic, because "which cell is highest" is a
    # thing you look at when investigating a pack rather than something a
    # dashboard shows -- and eight more entities in the main list would bury
    # the four voltages above that people actually watch.
    SungrowSensorDescription(
        key="battery_max_cell_module",
        component="cells",
        field="max_cell_module",
        translation_key="battery_max_cell_module",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="battery_max_cell_number",
        component="cells",
        field="max_cell_number",
        translation_key="battery_max_cell_number",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="battery_min_cell_module",
        component="cells",
        field="min_cell_module",
        translation_key="battery_min_cell_module",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="battery_min_cell_number",
        component="cells",
        field="min_cell_number",
        translation_key="battery_min_cell_number",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="battery_max_module_temperature_module",
        component="cells",
        field="max_module_temperature_module",
        translation_key="battery_max_module_temperature_module",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="battery_min_module_temperature_module",
        component="cells",
        field="min_module_temperature_module",
        translation_key="battery_min_module_temperature_module",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

#: Everything the pack can offer, in one tuple for the platform to walk.
#:
#: The two sensor-index halves of the temperature positions are deliberately
#: **absent**. `max_module_temperature_sensor` reads 1 or 2 and nothing else
#: across every sample known, and "sensor 2 of module 3" is an inference
#: about what that byte counts -- see `SbrBatteryCells`. A number whose
#: meaning is a guess should not become an entity somebody builds an
#: automation on; the library decodes it and the survey records it, which is
#: where a guess belongs until it is not one.
BATTERY_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    *PACK_DESCRIPTIONS,
    *CELL_DESCRIPTIONS,
)
