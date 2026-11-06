"""Entity descriptions for a Sungrow SG string inverter, hand-written.

The YAML package never read an SG, so there is **no legacy id to preserve**:
every entity here is new, as on the wallbox.

`tests/test_string_inverter_entities.py` is their guard: every `field`
resolves to a real field or property of `SungrowStringInverter`, and no
`_raw` code gets an entity -- its decoded property does.

**What gets an entity is decided per device**, after the first poll: an SG5.0RS
has two trackers and one phase, an SG110CX nine and three. A field that
read nothing -- refused, or the protocol's "unavailable" -- gets no entity,
rather than one that is unavailable forever; nor does a phase or tracker the
model lacks, which an SG answers as 0 (`SungrowStringInverter.serves`).

**Nothing is writable.** The power limitation is shown so an owner can see a
curtailment is set; writing it waits for a watched write.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)

from .entity import SungrowBinarySensorDescription, SungrowSensorDescription

#: The prefix every key carries, so no translation key meets a hybrid's.
PREFIX = "sg_"


def _sensor(
    component: str,
    field: str,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    *,
    category: EntityCategory | None = None,
    key: str | None = None,
) -> SungrowSensorDescription:
    """Describe one value; `key` names it where it is not the field's name."""
    key = f"{PREFIX}{key or field}"
    return SungrowSensorDescription(
        key=key,
        component=component,
        field=field,
        translation_key=key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        entity_category=category,
    )


def _energy(
    component: str, field: str, *, key: str | None = None
) -> SungrowSensorDescription:
    """Describe a meter that only climbs, or resets at midnight or month end.

    `total_increasing` for both: a daily total's reset is exactly the reset
    that class exists to describe.
    """
    return _sensor(
        component,
        field,
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorStateClass.TOTAL_INCREASING,
        key=key,
    )


def _tracker(component: str, number: int) -> tuple[SungrowSensorDescription, ...]:
    """Describe one tracker: voltage, current, their product, and its integral.

    The power is computed (`_tracker_power` in the library), and the energy
    is that power integrated over every poll, since no SG register counts
    energy per tracker.
    """
    key = f"{PREFIX}mppt{number}_energy"
    return (
        _sensor(
            component,
            f"mppt{number}_voltage",
            SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT,
        ),
        _sensor(
            component,
            f"mppt{number}_current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
        ),
        _sensor(
            component,
            f"mppt{number}_power",
            SensorDeviceClass.POWER,
            UnitOfPower.WATT,
        ),
        SungrowSensorDescription(
            key=key,
            component=component,
            field=f"mppt{number}_power",
            translation_key=key,
            integrated=True,
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            suggested_display_precision=2,
        ),
    )


def _phase(phase: str) -> tuple[SungrowSensorDescription, ...]:
    return (
        _sensor(
            "sg_realtime",
            f"phase_{phase}_voltage",
            SensorDeviceClass.VOLTAGE,
            UnitOfElectricPotential.VOLT,
        ),
        _sensor(
            "sg_realtime",
            f"phase_{phase}_current",
            SensorDeviceClass.CURRENT,
            UnitOfElectricCurrent.AMPERE,
        ),
    )


STRING_INVERTER_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    # -- what it makes, second to second ------------------------------------
    _sensor("sg_realtime", "total_dc_power", SensorDeviceClass.POWER, UnitOfPower.WATT),
    _sensor(
        "sg_realtime", "total_active_power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _sensor(
        "sg_realtime",
        "total_apparent_power",
        SensorDeviceClass.APPARENT_POWER,
        UnitOfApparentPower.VOLT_AMPERE,
    ),
    _sensor(
        "sg_realtime",
        "reactive_power",
        SensorDeviceClass.REACTIVE_POWER,
        UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
    ),
    _sensor("sg_realtime", "power_factor", SensorDeviceClass.POWER_FACTOR),
    _sensor(
        "sg_realtime",
        "grid_frequency",
        SensorDeviceClass.FREQUENCY,
        UnitOfFrequency.HERTZ,
    ),
    _sensor(
        "sg_realtime",
        "inverter_temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
    ),
    _sensor("sg_realtime", "work_state", state_class=None),
    *_tracker("sg_realtime", 1),
    *_tracker("sg_realtime", 2),
    *_tracker("sg_realtime", 3),
    *_phase("a"),
    *_phase("b"),
    *_phase("c"),
    # -- what it has made ---------------------------------------------------
    _energy("sg_realtime", "daily_pv_generation"),
    # One lifetime total, from 5144 in 0.1 kWh rather than 5004 in whole kWh,
    # which steps the Energy dashboard's hourly bars by a kWh at a time.
    _energy("sg_precision", "total_pv_generation_precise", key="total_pv_generation"),
    _energy("sg_trackers", "monthly_pv_generation"),
    _sensor(
        "sg_realtime",
        "total_running_time",
        SensorDeviceClass.DURATION,
        UnitOfTime.HOURS,
        SensorStateClass.TOTAL_INCREASING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _sensor(
        "sg_trackers",
        "daily_running_time",
        SensorDeviceClass.DURATION,
        UnitOfTime.MINUTES,
        SensorStateClass.TOTAL_INCREASING,
        category=EntityCategory.DIAGNOSTIC,
    ),
    # -- the meter, where one is wired: undocumented on RS by the source ----
    _sensor(
        "sg_meter", "meter_active_power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _sensor(
        "sg_meter", "meter_phase_a_power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _sensor(
        "sg_meter", "meter_phase_b_power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _sensor(
        "sg_meter", "meter_phase_c_power", SensorDeviceClass.POWER, UnitOfPower.WATT
    ),
    _sensor("sg_meter", "load_power", SensorDeviceClass.POWER, UnitOfPower.WATT),
    _energy("sg_meter", "daily_exported_energy"),
    _energy("sg_meter", "total_exported_energy"),
    _energy("sg_meter", "daily_imported_energy"),
    _energy("sg_meter", "total_imported_energy"),
    _energy("sg_meter", "daily_direct_energy_consumption"),
    _energy("sg_meter", "total_direct_energy_consumption"),
    # -- the trackers past three, on the models that have them --------------
    *(
        description
        for number in range(4, 13)
        for description in _tracker("sg_trackers", number)
    ),
    # -- slow-moving, and for diagnosing --------------------------------------
    _sensor(
        "sg_precision",
        "negative_voltage_to_ground",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _sensor(
        "sg_precision",
        "bus_voltage",
        SensorDeviceClass.VOLTAGE,
        UnitOfElectricPotential.VOLT,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _sensor(
        "sg_power_limit",
        "power_limitation",
        state_class=None,
        category=EntityCategory.DIAGNOSTIC,
    ),
    _sensor(
        "sg_power_limit",
        "power_limitation_setting",
        unit=PERCENTAGE,
        category=EntityCategory.DIAGNOSTIC,
    ),
)

#: States, where a boolean is the honest shape, as on the hybrid. The power
#: limitation's on/off is already the `power_limitation` sensor.
STRING_INVERTER_BINARY_DESCRIPTIONS: tuple[SungrowBinarySensorDescription, ...] = (
    SungrowBinarySensorDescription(
        key=f"{PREFIX}fault_reported",
        component="sg_realtime",
        field="fault_reported",
        translation_key=f"{PREFIX}fault_reported",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)
