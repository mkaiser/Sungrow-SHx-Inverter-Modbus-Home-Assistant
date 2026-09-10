"""Entity descriptions for a Sungrow AC wallbox, hand-written.

Third hand-written description module, and the reason is the same each time:
`sensor_descriptions.py` is generated from the YAML package's entity map, and
the wallbox is not in it. Unlike the SBR there is not even an opt-in YAML file
to port -- the package never covered a wallbox at all -- so there is nothing
to generate from and **no legacy id to preserve**. Every entity here is new,
which makes this the one device with no migration question at all.

`tests/test_wallbox_entities.py` gives these the guard generation gives the
others: every `field` resolves to a real field or property, and no key
collides with another device's.

**What gets an entity, and what does not.** Thirty-two registers, and three
kinds of thing are deliberately left out:

* the **raw code** fields -- `charging_status_raw` and its five siblings.
  Their decoded properties are the entities, exactly as modern mode treats
  every other `_raw` value.
* **register 21313**, which nobody can name. It is read, carried in the
  survey, and given no entity, because inventing a meaning is worse than
  admitting there isn't one.
* the two **session timestamps**. They are epoch-shaped numbers holding the
  wallbox's *local* time rather than UTC -- decoded as UTC they read two hours
  off in Berlin and matched the wall clock exactly. A `timestamp` entity needs
  a real instant, and this project does not know the device's zone, so
  publishing one would be a claim it cannot support. Recorded in
  `doc/wallbox_registers.md`; the library reads them either way.

**Nothing is writable.** The registers that would start and stop a charge are
known -- holding 21211 and 21212 -- and no manufacturer document covers this
map. Starting somebody's car charging from a stale automation is not a thing
to ship on one measurement of one unit.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)

from .entity import SungrowBinarySensorDescription, SungrowSensorDescription

#: What it is doing right now: the block worth polling quickly.
LIVE_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="wallbox_charging_power",
        component="wallbox_live",
        field="charging_power",
        translation_key="wallbox_charging_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # `total_increasing` on the session counter, not `total`: it resets to
    # zero when a new session starts, which is exactly the reset that class
    # exists to describe. Measured across a session boundary -- two dumps 157
    # seconds apart and 21 samples over ten minutes -- which is the only way
    # to tell a counter that resets from one that keeps climbing.
    SungrowSensorDescription(
        key="wallbox_session_energy",
        component="wallbox_live",
        field="session_energy",
        translation_key="wallbox_session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SungrowSensorDescription(
        key="wallbox_lifetime_energy",
        component="wallbox_live",
        field="lifetime_energy",
        translation_key="wallbox_lifetime_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # An enum rather than a bare string, so the states are declared and a
    # dashboard can translate them. The nine codes are the strongest thing in
    # `doc/wallbox_registers.md` -- agreed by every source that has one, and
    # not measurable here: a finished session settles on 6, and only a source
    # with the whole table says 6 is *completed* rather than idle.
    SungrowSensorDescription(
        key="wallbox_charging_status",
        component="wallbox_live",
        field="charging_status",
        translation_key="wallbox_charging_status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "idle",
            "standby",
            "charging",
            "suspended by the charge point",
            "suspended by the vehicle",
            "completed",
            "reserved",
            "disabled",
            "fault",
        ],
    ),
    SungrowSensorDescription(
        key="wallbox_phase_a_voltage",
        component="wallbox_live",
        field="phase_a_voltage",
        translation_key="wallbox_phase_a_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_a_current",
        component="wallbox_live",
        field="phase_a_current",
        translation_key="wallbox_phase_a_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_b_voltage",
        component="wallbox_live",
        field="phase_b_voltage",
        translation_key="wallbox_phase_b_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_b_current",
        component="wallbox_live",
        field="phase_b_current",
        translation_key="wallbox_phase_b_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_c_voltage",
        component="wallbox_live",
        field="phase_c_voltage",
        translation_key="wallbox_phase_c_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_c_current",
        component="wallbox_live",
        field="phase_c_current",
        translation_key="wallbox_phase_c_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_available_current",
        component="wallbox_live",
        field="available_current",
        translation_key="wallbox_available_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    # Diagnostic, and genuinely useful as one: 12 V is nothing plugged in,
    # 9 V a vehicle connected and not charging, 6 V a vehicle charging. It is
    # the Type 2 signalling line, so it says what the *cable* thinks where
    # the status register says what the charge point thinks.
    SungrowSensorDescription(
        key="wallbox_control_pilot_voltage",
        component="wallbox_live",
        field="control_pilot_voltage",
        translation_key="wallbox_control_pilot_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="wallbox_start_mode",
        component="wallbox_live",
        field="start_mode",
        translation_key="wallbox_start_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["stopped", "start with EMS", "start by swiping"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

#: What it is, and what it is allowed to draw. Read on the slow tier.
RATING_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="wallbox_rated_current",
        component="wallbox_ratings",
        field="rated_current",
        translation_key="wallbox_rated_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
    SungrowSensorDescription(
        key="wallbox_maximum_charging_power",
        component="wallbox_ratings",
        field="maximum_charging_power",
        translation_key="wallbox_maximum_charging_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="wallbox_minimum_charging_power",
        component="wallbox_ratings",
        field="minimum_charging_power",
        translation_key="wallbox_minimum_charging_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="wallbox_phase_mode",
        component="wallbox_ratings",
        field="phase_mode",
        translation_key="wallbox_phase_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["single phase", "three phase"],
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SungrowSensorDescription(
        key="wallbox_firmware_version",
        component="wallbox_identity",
        field="version_string",
        translation_key="wallbox_firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

#: The settings, read and never written.
SETTING_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="wallbox_output_current_setting",
        component="wallbox_settings",
        field="output_current_setting",
        translation_key="wallbox_output_current_setting",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
    ),
)

#: States, where a boolean is the honest shape.
BINARY_DESCRIPTIONS: tuple[SungrowBinarySensorDescription, ...] = (
    # `-ing`, which this project's naming convention reserves for exactly
    # this: a binary sensor meaning "happening right now". Derived from the
    # status code and not from the power, deliberately -- a vehicle that has
    # stopped drawing mid-session reads 0 W and is still charging as far as
    # the charge point is concerned.
    SungrowBinarySensorDescription(
        key="wallbox_charging",
        component="wallbox_live",
        field="charging",
        translation_key="wallbox_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    SungrowBinarySensorDescription(
        key="wallbox_enabled",
        component="wallbox_settings",
        field="charger_enabled",
        translation_key="wallbox_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

#: Everything the wallbox offers, for the platforms to walk.
WALLBOX_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    *LIVE_DESCRIPTIONS,
    *RATING_DESCRIPTIONS,
    *SETTING_DESCRIPTIONS,
)

WALLBOX_BINARY_DESCRIPTIONS = BINARY_DESCRIPTIONS
