"""Entity descriptions for a Sungrow iHomeManager, hand-written.

The YAML package never read an iHomeManager, so there is **no legacy id to
preserve**. Every key starts `ihm_`, so no translation key meets another
device's. `tests/test_ihomemanager_entities.py` is their guard: every
`field` resolves on `SungrowIHomeManager`, and none is a `_raw` code.

**What gets an entity is decided after the first poll**
(`SungrowIHomeManager.serves`): a field that read nothing gets none.

**Left out, on the one unit measured** (SV930.001.00.P020, 2026-11-10;
wiki: device-ihomemanager):

* **8554, the output type**: it reads 0, "single phase", beside three
  phase voltages and three phase powers.
* **8047, 8048, 8051 and 8052**: start/stop reads 0 and the charger mode
  0xA7, codes no document lists; the active power limitation reads 0 and its
  ratio 0x7FFF, an unset value.
* **Channel 2 (8565-8574)**, the PROD.CT: zeros on a unit with no CT there.
* **8029, the feed-in limit in kW**: the template's alone, in no document.
* The type code, the protocol number and the `_raw` codes; the
  application software version goes on the device page instead.

**Signs the document does not give**: the grid's (8157) and the battery's
(8161) power. They are shown as the device sends them.

**Nothing is writable.** The holding registers are its controls; they are
shown as set.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
)
from sungrow_modbus.ihomemanager.registers import (
    CHARGE_COMMAND,
    CHARGER_STATUS,
    EMS_MODE,
    ENABLED,
    FEED_IN_LIMITATION,
)

from .entity import SungrowSensorDescription

#: The prefix every key carries.
PREFIX = "ihm_"

_KW = UnitOfPower.KILO_WATT
_W = UnitOfPower.WATT
_V = UnitOfElectricPotential.VOLT


def _sensor(
    component: str,
    field: str,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT,
    *,
    precision: int | None = None,
    category: EntityCategory | None = None,
) -> SungrowSensorDescription:
    """Describe one value read off the iHomeManager."""
    key = f"{PREFIX}{field}"
    return SungrowSensorDescription(
        key=key,
        component=component,
        field=field,
        translation_key=key,
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=state_class,
        suggested_display_precision=precision,
        entity_category=category,
    )


def _enum(
    component: str, field: str, table: dict[int, str]
) -> SungrowSensorDescription:
    """Describe a coded value, its states the table's words."""
    key = f"{PREFIX}{field}"
    return SungrowSensorDescription(
        key=key,
        component=component,
        field=field,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=list(dict.fromkeys(table.values())),
    )


_POWER = SensorDeviceClass.POWER
_DIAGNOSTIC = EntityCategory.DIAGNOSTIC

IHOMEMANAGER_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    # -- the site's flows, as it dispatches by them (V1.0.2 rows 12-17) --
    _sensor("system", "inverter_active_power", _POWER, _KW, precision=2),
    _sensor("system", "grid_active_power", _POWER, _KW, precision=2),
    _sensor("system", "load_active_power", _POWER, _KW, precision=2),
    _sensor("system", "battery_power", _POWER, _KW, precision=2),
    _sensor("system", "battery_level", SensorDeviceClass.BATTERY, PERCENTAGE),
    # -- what it manages, and its limits (rows 4-11) ----------------------
    _sensor("identity", "connected_devices", state_class=None, category=_DIAGNOSTIC),
    _sensor("identity", "devices_in_fault", state_class=None),
    _sensor(
        "system",
        "total_rated_active_power",
        _POWER,
        _KW,
        state_class=None,
        precision=1,
        category=_DIAGNOSTIC,
    ),
    _sensor(
        "system",
        "total_rated_battery_capacity",
        SensorDeviceClass.ENERGY_STORAGE,
        UnitOfEnergy.KILO_WATT_HOUR,
        state_class=None,
        precision=1,
        category=_DIAGNOSTIC,
    ),
    *(
        _sensor(
            "system",
            field,
            _POWER,
            _KW,
            state_class=None,
            precision=1,
            category=_DIAGNOSTIC,
        )
        for field in (
            "battery_power_range",
            "max_battery_charge_power",
            "min_battery_charge_power",
            "max_battery_discharge_power",
            "min_battery_discharge_power",
        )
    ),
    # -- the grid connection point, GRID.CT (rows 18-19, 23-30) -----------
    _sensor(
        "energy",
        "grid_import_energy",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    _sensor(
        "energy",
        "grid_export_energy",
        SensorDeviceClass.ENERGY,
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorStateClass.TOTAL_INCREASING,
        precision=1,
    ),
    # Line to line on a three-phase site, by the measured unit and evcc's.
    *(
        _sensor(
            "meters", f"voltage_{phase}", SensorDeviceClass.VOLTAGE, _V, precision=1
        )
        for phase in "abc"
    ),
    _sensor(
        "meters",
        "grid_frequency",
        SensorDeviceClass.FREQUENCY,
        UnitOfFrequency.HERTZ,
        precision=2,
    ),
    *(_sensor("meters", f"phase_{phase}_power", _POWER, _W) for phase in "abc"),
    # Phase to neutral, in no document: evcc #34169 and the measured unit.
    *(
        _sensor(
            "phase_voltages",
            f"phase_{phase}_voltage",
            SensorDeviceClass.VOLTAGE,
            _V,
            precision=1,
        )
        for phase in "abc"
    ),
    # -- the charger it manages (row 21; 8594-8601 field only) ------------
    _enum("meters", "charger_status", CHARGER_STATUS),
    _sensor("charger", "charger_power", _POWER, _W),
    *(
        _sensor("charger", f"charger_phase_{phase}_power", _POWER, _W)
        for phase in "abc"
    ),
    # -- its settings, as set (table 4) -----------------------------------
    _enum("settings", "ems_mode", EMS_MODE),
    _enum("settings", "charge_command", CHARGE_COMMAND),
    _sensor("settings", "charge_power", _POWER, _KW, state_class=None, precision=1),
    _enum("settings", "feed_in_limitation", FEED_IN_LIMITATION),
    _sensor("settings", "feed_in_limitation_ratio", unit=PERCENTAGE, state_class=None),
    _enum("settings", "charger_enabled", ENABLED),
    _enum("settings", "grid_draw_permitted", ENABLED),
    _sensor(
        "settings",
        "vpp_heartbeat",
        SensorDeviceClass.DURATION,
        UnitOfTime.SECONDS,
        state_class=None,
        category=_DIAGNOSTIC,
    ),
    _sensor(
        "identity",
        "protocol_version",
        state_class=None,
        category=_DIAGNOSTIC,
    ),
)
