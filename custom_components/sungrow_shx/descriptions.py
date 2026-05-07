"""Entity descriptions for the Sungrow SHx integration.

The schema is data-first: every entity is a frozen dataclass declaring
what to read and how to interpret it. Derived entities (computed sensors,
binary sensors, selects, numbers) carry plain-Python compute callables or
declarative reverse-maps — no Jinja templates.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ScanGroup(StrEnum):
    REALTIME = "realtime"
    FAST = "fast"
    MEDIUM = "medium"
    SLOWEST = "slowest"


SCAN_INTERVALS: dict["ScanGroup", int] = {
    ScanGroup.REALTIME: 5,
    ScanGroup.FAST: 10,
    ScanGroup.MEDIUM: 60,
    ScanGroup.SLOWEST: 600,
}


@dataclass(frozen=True, kw_only=True)
class ModbusSensorDescription:
    key: str
    name: str
    address: int
    input_type: str
    data_type: str
    count: int = 1
    swap: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    precision: int | None = None
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    scan_group: ScanGroup = ScanGroup.SLOWEST


@dataclass(frozen=True, kw_only=True)
class ComputedSensorDescription:
    """Sensor whose value is a Python function of decoded coordinator data.

    ``compute`` is called with the coordinator's decoded dict and returns
    the value (or ``None``). ``requires`` lists decoded keys that must be
    present and non-``None`` for the entity to be available; the compute
    callable is only invoked when all of them are populated.
    """

    key: str
    name: str
    compute: Callable[[Mapping[str, Any]], Any]
    requires: tuple[str, ...] = ()
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None


@dataclass(frozen=True, kw_only=True)
class ComputedBinarySensorDescription:
    """Binary sensor whose value is a Python function of decoded data."""

    key: str
    name: str
    compute: Callable[[Mapping[str, Any]], bool | None]
    requires: tuple[str, ...] = ()
    device_class: str | None = None


@dataclass(frozen=True, kw_only=True)
class WriteRegisterAction:
    address: int
    value: int
    hub: str | None = None


@dataclass(frozen=True, kw_only=True)
class SelectDescription:
    """Select whose state mirrors a decoded register, by reverse lookup.

    Each option's :class:`WriteRegisterAction` doubles as the read map:
    the option whose ``value`` matches the register's current decoded
    value is the active option.
    """

    key: str
    name: str
    source_key: str
    options: tuple[str, ...]
    option_writes: Mapping[str, WriteRegisterAction]


@dataclass(frozen=True, kw_only=True)
class NumberDescription:
    """Number entity backed by a single holding register.

    The displayed value is the decoded value of ``source_key``. Writes
    transform user input to a register integer via ``register =
    round(value / set_scale)`` — i.e. ``set_scale`` is the same scale
    factor as on the source :class:`ModbusSensorDescription`.

    ``family_scale_overrides`` lets a model family (``"RS"``, ``"RT"``)
    use a different write scale; it's how export-power-limit handles
    SH-RT writing 0.1-W units while RS writes 1-W units.

    ``max_source_key`` replaces ``max_value`` with the runtime decoded
    value of that key (e.g. inverter rated output as the export-power-
    limit cap). ``max_from_config`` does the same against
    ``entry.data[<key>]`` instead — used for the user-configured
    ``battery_max_power`` ceiling on the forced-charge/discharge knobs.
    """

    key: str
    name: str
    source_key: str
    set_address: int
    set_scale: float = 1.0
    family_scale_overrides: Mapping[str, float] | None = None
    min_value: float
    max_value: float
    step: float
    unit: str | None
    max_source_key: str | None = None
    max_from_config: str | None = None


@dataclass(frozen=True, kw_only=True)
class ModbusSwitchDescription:
    """Modbus-native switch (mirrors the ``modbus: switches:`` YAML block).

    Fields mirror Home Assistant's native modbus switch config: a
    ``write_type`` ("holding" or "coil"), an ``address``, the
    ``command_on``/``command_off`` values, and an optional ``verify``
    block (input_type, address, state_on, state_off) to read the current
    state back.
    """

    key: str
    name: str
    address: int
    write_type: str  # "holding" or "coil"
    command_on: int
    command_off: int
    verify_input_type: str | None = None
    verify_address: int | None = None
    verify_state_on: int | None = None
    verify_state_off: int | None = None


# ---------------------------------------------------------------------------
# Device family classification.
#
# Sungrow's hybrid line splits into two electrical families that share most
# but not all of the modbus map:
#
#   * RS  — single-phase residential (SH3.0RS .. SH10RS). Phase B/C voltage,
#           current and power registers are either absent or always 0;
#           the 3-phase external-meter block 5740-5745 is absent entirely.
#   * RT  — three-phase residential (SH5.0RT .. SH10RT and -V112/-V122/-20
#           variants). Full 3-phase register set.
#
# We use the device-type code returned by input register 4999 to decide
# which family the connected unit belongs to and to suppress entities for
# registers that don't apply on that family. ``FAMILY_UNAPPLICABLE_KEYS``
# is the set of sensor keys to mark unsupported per family — additive on
# top of probe-detected illegal-address registers.
# ---------------------------------------------------------------------------
RS_DEVICE_CODES: frozenset[int] = frozenset(
    {0x0D17, 0x0D0D, 0x0D18, 0x0D0F, 0x0D10, 0x0D1A, 0x0D1B}
)


def family_for_device_code(code: int | None) -> str | None:
    """Return ``"RS"`` / ``"RT"`` / ``None`` for the given device-type code."""
    if code is None:
        return None
    if code in RS_DEVICE_CODES:
        return "RS"
    # Three-phase RT range starts at 0x0E00; the SH5K/SH4K6/etc. older codes
    # in 0x0D03..0x0D0C are legacy and treated as RS-style for safety.
    if 0x0E00 <= code <= 0x0EFF:
        return "RT"
    if 0x0D03 <= code <= 0x0D0C:
        return "RS"
    return None


# Keys that only make sense on RT (three-phase) units. Filtered out on RS.
_RS_UNAPPLICABLE: frozenset[str] = frozenset(
    {
        "sg_phase_b_voltage",
        "sg_phase_c_voltage",
        "sg_phase_b_current",
        "sg_phase_c_current",
        "sg_meter_phase_b_active_power",
        "sg_meter_phase_c_active_power",
        "sg_meter_phase_a_voltage",
        "sg_meter_phase_b_voltage",
        "sg_meter_phase_c_voltage",
        "sg_meter_phase_a_current",
        "sg_meter_phase_b_current",
        "sg_meter_phase_c_current",
        "sg_backup_phase_b_power",
        "sg_backup_phase_c_power",
    }
)


FAMILY_UNAPPLICABLE_KEYS: dict[str, frozenset[str]] = {
    "RS": _RS_UNAPPLICABLE,
    "RT": frozenset(),
}


MODBUS_SENSORS: tuple[ModbusSensorDescription, ...] = (
    ModbusSensorDescription(key='sg_version_1', name='Sungrow Version 1', address=2581, input_type='input', data_type='string', count=11, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_version_2', name='Sungrow Version 2', address=2596, input_type='input', data_type='string', count=11, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_version_3', name='Sungrow Version 3', address=2612, input_type='input', data_type='string', count=11, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_version_4_battery', name='Sungrow Version 4 (Sungrow Battery)', address=2628, input_type='input', data_type='string', count=11, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_protocol_version', name='Sungrow Protocol Version', address=4951, input_type='input', data_type='uint32', count=2, swap='word', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_arm_software', name='Sungrow Arm Software', address=4953, input_type='input', data_type='string', count=15, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_dsp_software', name='Sungrow DSP Software', address=4968, input_type='input', data_type='string', count=15, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_inverter_serial', name='Sungrow inverter serial', address=4989, input_type='input', data_type='string', count=10, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_dev_code', name='Sungrow device type code', address=4999, input_type='input', data_type='uint16', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_inverter_rated_output', name='Inverter rated output', address=5000, input_type='input', data_type='uint16', scale=100.0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_daily_pv_gen_battery_discharge', name='Daily PV generation & battery discharge', address=5002, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_pv_gen_battery_discharge', name='Total PV generation & battery discharge', address=5003, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_inverter_temperature', name='Inverter temperature', address=5007, input_type='input', data_type='int16', scale=0.1, precision=1, unit='°C', device_class='temperature', state_class='measurement', scan_group=ScanGroup.MEDIUM),
    ModbusSensorDescription(key='sg_mppt1_voltage', name='MPPT1 voltage', address=5010, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt1_current', name='MPPT1 current', address=5011, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt2_voltage', name='MPPT2 voltage', address=5012, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt2_current', name='MPPT2 current', address=5013, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt3_voltage', name='MPPT3 voltage', address=5014, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt3_current', name='MPPT3 current', address=5015, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_total_dc_power', name='Total DC power', address=5016, input_type='input', data_type='uint32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_phase_a_voltage', name='Phase A voltage', address=5018, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_phase_b_voltage', name='Phase B voltage', address=5019, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_phase_c_voltage', name='Phase C voltage', address=5020, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_reactive_power', name='Reactive power', address=5032, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_power_factor', name='Power factor', address=5034, input_type='input', data_type='int16', scale=0.001, precision=3, unit='%', device_class='power_factor', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt4_voltage', name='MPPT4 voltage', address=5114, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_mppt4_current', name='MPPT4 current', address=5115, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_power', name='Battery power', address=5213, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_grid_frequency', name='Grid frequency', address=5241, input_type='input', data_type='uint16', scale=0.01, precision=2, unit='Hz', device_class='frequency', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_active_power', name='Meter active power', address=5600, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_a_active_power', name='Meter phase A active power', address=5602, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_b_active_power', name='Meter phase B active power', address=5604, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_c_active_power', name='Meter phase C active power', address=5606, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_bdc_rated_power', name='BDC rated power', address=5627, input_type='input', data_type='uint16', scale=100.0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_battery_current', name='Battery current', address=5630, input_type='input', data_type='int16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_bms_max_charging_current', name='BMS max. charging current', address=5634, input_type='input', data_type='uint16', precision=0, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_bms_max_discharging_current', name='BMS max. discharging current', address=5635, input_type='input', data_type='uint16', precision=0, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='uid_battery_capacity_high_precision', name='Battery capacity high precision', address=5638, input_type='input', data_type='uint16', scale=0.01, precision=2, unit='kWh', device_class='energy_storage', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_backup_phase_a_power', name='Backup phase A power', address=5722, input_type='input', data_type='int16', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_backup_phase_b_power', name='Backup phase B power', address=5723, input_type='input', data_type='int16', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_backup_phase_c_power', name='Backup phase C power', address=5724, input_type='input', data_type='int16', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_total_backup_power', name='Total backup power', address=5725, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_a_voltage', name='Meter phase A voltage', address=5740, input_type='input', data_type='int16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_b_voltage', name='Meter phase B voltage', address=5741, input_type='input', data_type='int16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_c_voltage', name='Meter phase C voltage', address=5742, input_type='input', data_type='int16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_a_current', name='Meter phase A current', address=5743, input_type='input', data_type='uint16', scale=0.01, precision=2, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_b_current', name='Meter phase B current', address=5744, input_type='input', data_type='uint16', scale=0.01, precision=2, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_meter_phase_c_current', name='Meter phase C current', address=5745, input_type='input', data_type='uint16', scale=0.01, precision=2, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='uid_sg_running_state_raw', name='Running state raw', address=12999, input_type='input', data_type='uint16', precision=0, state_class='measurement', scan_group=ScanGroup.REALTIME),
    ModbusSensorDescription(key='uid_power_flow_status', name='Power Flow Status', address=13000, input_type='input', data_type='uint16', precision=0, state_class='measurement', scan_group=ScanGroup.REALTIME),
    ModbusSensorDescription(key='sg_daily_pv_generation', name='Daily PV generation', address=13001, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_pv_generation', name='Total PV generation', address=13002, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_daily_exported_energy_from_PV', name='Daily exported energy from PV', address=13004, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_exported_energy_from_pv', name='Total exported energy from PV', address=13005, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_load_power', name='Load power', address=13007, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.REALTIME),
    ModbusSensorDescription(key='sg_battery_export_power_raw', name='Export power raw', address=13009, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_daily_battery_charge_from_pv', name='Daily battery charge from PV', address=13011, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_battery_charge_from_pv', name='Total battery charge from PV', address=13012, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_daily_direct_energy_consumption', name='Daily direct energy consumption', address=13016, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_direct_energy_consumption', name='Total direct energy consumption', address=13017, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_battery_voltage', name='Battery voltage', address=13019, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='V', device_class='voltage', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_level', name='Battery level', address=13022, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='%', device_class='battery', state_class='measurement', scan_group=ScanGroup.MEDIUM),
    ModbusSensorDescription(key='sg_battery_state_of_health', name='Battery state of health', address=13023, input_type='input', data_type='uint16', scale=0.1, precision=0, unit='%', state_class='measurement', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_battery_temperature', name='Battery temperature', address=13024, input_type='input', data_type='int16', scale=0.1, precision=1, unit='°C', device_class='temperature', state_class='measurement', scan_group=ScanGroup.MEDIUM),
    ModbusSensorDescription(key='sg_daily_battery_discharge', name='Daily battery discharge', address=13025, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_battery_discharge', name='Total battery discharge', address=13026, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_phase_a_current', name='Phase A current', address=13030, input_type='input', data_type='int16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_phase_b_current', name='Phase B current', address=13031, input_type='input', data_type='int16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_phase_c_current', name='Phase C current', address=13032, input_type='input', data_type='int16', scale=0.1, precision=1, unit='A', device_class='current', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_total_active_power', name='Total active power', address=13033, input_type='input', data_type='int32', count=2, swap='word', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_daily_imported_energy', name='Daily imported energy', address=13035, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_imported_energy', name='Total imported energy', address=13036, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_daily_battery_charge', name='Daily battery charge', address=13039, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_battery_charge', name='Total battery charge', address=13040, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_daily_exported_energy', name='Daily exported energy', address=13044, input_type='input', data_type='uint16', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total_increasing', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_total_exported_energy', name='Total exported energy', address=13045, input_type='input', data_type='uint32', count=2, swap='word', scale=0.1, precision=1, unit='kWh', device_class='energy', state_class='total', scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_load_adjustment_mode_selection_raw', name='Load adjustment mode selection raw', address=13001, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_load_adjustment_mode_enable_raw', name='Load adjustment mode enable raw', address=13010, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_ems_mode_selection_raw', name='EMS mode selection raw', address=13049, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_forced_charge_discharge_cmd_raw', name='Battery forced charge discharge cmd raw', address=13050, input_type='holding', data_type='uint16', precision=0, state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_forced_charge_discharge_power', name='Battery forced charge discharge power', address=13051, input_type='holding', data_type='uint16', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='uid_sg_battery_max_soc', name='Battery max SoC', address=13057, input_type='holding', data_type='uint16', scale=0.1, precision=1, unit='%', device_class='battery', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='uid_sg_battery_min_soc', name='Battery min SoC', address=13058, input_type='holding', data_type='uint16', scale=0.1, precision=1, unit='%', device_class='battery', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_export_power_limit', name='Export power limit', address=13073, input_type='holding', data_type='uint16', precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_backup_mode_raw', name='Backup mode raw', address=13074, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_export_power_limit_mode_raw', name='Export power limit mode raw', address=13086, input_type='holding', data_type='uint16', precision=0, state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_active_power_limitation_raw', name='Active power limitation raw', address=13088, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_active_power_limitation_ratio_raw', name='Active power limitation ratio raw', address=13089, input_type='holding', data_type='uint16', scale=0.1, unit='%', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_reserved_soc_for_backup', name='Battery reserved SoC for backup', address=13099, input_type='holding', data_type='uint16', unit='%', device_class='battery', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_inverter_firmware_version', name='Inverter Firmware Version', address=13249, input_type='input', data_type='string', count=15, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_communication_module_firmware_version', name='Communication Module Firmware Version', address=13264, input_type='input', data_type='string', count=15, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_battery_firmware_version', name='Battery Firmware Version', address=13279, input_type='input', data_type='string', count=15, scan_group=ScanGroup.SLOWEST),
    ModbusSensorDescription(key='sg_apl_shutdown_on_zero_raw', name='APL shutdown at zero raw', address=31212, input_type='holding', data_type='uint16', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_max_charge_power', name='Battery max charge power', address=33046, input_type='holding', data_type='uint16', scale=10.0, precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_max_discharge_power', name='Battery max discharge power', address=33047, input_type='holding', data_type='uint16', scale=10.0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_charging_start_power', name='Battery charging start power', address=33148, input_type='holding', data_type='uint16', scale=10.0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
    ModbusSensorDescription(key='sg_battery_discharging_start_power', name='Battery discharging start power', address=33149, input_type='holding', data_type='uint16', scale=10.0, precision=0, unit='W', device_class='power', state_class='measurement', scan_group=ScanGroup.FAST),
)

# --- COMPUTED SENSORS ------------------------------------------------------


def _product(values: list[Any]) -> int | None:
    """Return product of the values rounded to int, or None if any is None."""
    if any(v is None for v in values):
        return None
    result = 1.0
    for v in values:
        result *= float(v)
    return int(result)


def _v_times_i(d: Mapping[str, Any], v_key: str, i_key: str) -> int | None:
    return _product([d.get(v_key), d.get(i_key)])


# Inverter running-state code → human-readable label.
_RUNNING_STATE_MAP: Mapping[int, str] = {
    0x0000: "Running",
    0x0001: "Stop",
    0x0002: "Key stop",
    0x0004: "Emergency Stop",
    0x0008: "Standby",
    0x0010: "Initial standby",
    0x0014: "Microgrid Operation",
    0x0020: "Starting",
    0x0040: "Running",
    0x0041: "Off-grid Charge",
    0x0080: "Derating Running",
    0x0100: "Fault",
    0x0200: "Update Failed",
    0x0400: "Running in maintain mode",
    0x0800: "Running in compulsory (forced) mode",
    0x1000: "Running (off-grid)",
    0x1111: "Uninitialized",
    0x1200: "Initial standby",
    0x1300: "Key stop",
    0x1400: "Standby",
    0x1500: "Emergency Stop",
    0x1600: "Starting",
    0x1700: "AFCI self-test shutdown",
    0x1800: "Intelligent Station Building Status",
    0x1900: "Safe Mode",
    0x2000: "Open loop",
    0x2500: "Communicate fault",
    0x2501: "Restarting",
    0x4000: "Running in External EMS mode",
    0x4001: "Emergency Charging Operation",
    0x5500: "Fault",
    0x8000: "Stop",
    0x8100: "Derating Running",
    0x8200: "Dispatch Running",
    0x9100: "Warn Running",
}

# Device-type code (input register 4999) → marketing model name.
DEVICE_TYPE_MAP: Mapping[int, str] = {
    0x0D03: "SH5K-V13",
    0x0D06: "SH3K6",
    0x0D07: "SH4K6",
    0x0D09: "SH5K-20",
    0x0D0A: "SH3K6-30",
    0x0D0B: "SH4K6-30",
    0x0D0C: "SH5K-30",
    0x0D0D: "SH3.6RS",
    0x0D0F: "SH5.0RS",
    0x0D10: "SH6.0RS",
    0x0D17: "SH3.0RS",
    0x0D18: "SH4.0RS",
    0x0D1A: "SH8.0RS",
    0x0D1B: "SH10RS",
    0x0D27: "MG5RL",
    0x0D28: "MG6RL",
    0x0E00: "SH5.0RT",
    0x0E01: "SH6.0RT",
    0x0E02: "SH8.0RT",
    0x0E03: "SH10RT",
    0x0E08: "SH5.0RT-V122",
    0x0E09: "SH6.0RT-V122",
    0x0E0A: "SH8.0RT-V122",
    0x0E0B: "SH10RT-V122",
    0x0E0C: "SH5.0RT-V112",
    0x0E0D: "SH6.0RT-V112",
    0x0E0E: "SH8.0RT-V112",
    0x0E0F: "SH10RT-V112",
    0x0E10: "SH5.0RT-20",
    0x0E11: "SH6.0RT-20",
    0x0E12: "SH8.0RT-20",
    0x0E13: "SH10RT-20",
    0x0E20: "SH5T",
    0x0E21: "SH6T",
    0x0E22: "SH8T",
    0x0E23: "SH10T",
    0x0E24: "SH12T",
    0x0E25: "SH15T",
    0x0E26: "SH20T",
    0x0E28: "SH25T",
}


def _running_state(d: Mapping[str, Any]) -> str | None:
    raw = d.get("uid_sg_running_state_raw")
    if raw is None:
        return None
    return _RUNNING_STATE_MAP.get(int(raw), f"Unknown running state code: 0x{int(raw):04X}")


def _device_type(d: Mapping[str, Any]) -> str | None:
    raw = d.get("sg_dev_code")
    if raw is None:
        return None
    return DEVICE_TYPE_MAP.get(int(raw), f"Unknown device code: 0x{int(raw):04X}")


def _battery_level_nom(d: Mapping[str, Any]) -> float:
    soc_min = float(d["uid_sg_battery_min_soc"])
    soc_max = float(d["uid_sg_battery_max_soc"])
    soc_cur = float(d["sg_battery_level"])
    return round(soc_min + (soc_max - soc_min) * (soc_cur / 100.0), 1)


def _battery_charge_nom(d: Mapping[str, Any]) -> float:
    capacity = float(d["uid_battery_capacity_high_precision"])
    nom = float(d["sg_battery_level_nom"])
    return round(capacity * nom / 100.0, 1)


def _battery_charge(d: Mapping[str, Any]) -> float:
    capacity = float(d["uid_battery_capacity_high_precision"])
    soc_min = float(d["uid_sg_battery_min_soc"])
    soc_max = float(d["uid_sg_battery_max_soc"])
    level = float(d["sg_battery_level"])
    return round(capacity * (soc_max - soc_min) / 100.0 * level / 100.0, 2)


def _battery_charge_health_rated(d: Mapping[str, Any]) -> float:
    return round(
        float(d["sg_battery_charge"]) * float(d["sg_battery_state_of_health"]) / 100.0, 2
    )


def _daily_consumed_energy(d: Mapping[str, Any]) -> float:
    return (
        float(d["sg_daily_pv_generation"])
        - float(d["sg_daily_exported_energy"])
        + float(d["sg_daily_imported_energy"])
        - float(d["sg_daily_battery_charge"])
        + float(d["sg_daily_battery_discharge"])
    )


def _total_consumed_energy(d: Mapping[str, Any]) -> float:
    return (
        float(d["sg_total_pv_generation"])
        - float(d["sg_total_exported_energy"])
        + float(d["sg_total_imported_energy"])
        - float(d["sg_total_battery_charge"])
        + float(d["sg_total_battery_discharge"])
    )


COMPUTED_SENSORS: tuple[ComputedSensorDescription, ...] = (
    # MPPT power = V × I.
    ComputedSensorDescription(
        key="sg_mppt1_power",
        name="MPPT1 power",
        compute=lambda d: _v_times_i(d, "sg_mppt1_voltage", "sg_mppt1_current"),
        requires=("sg_mppt1_voltage", "sg_mppt1_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_mppt2_power",
        name="MPPT2 power",
        compute=lambda d: _v_times_i(d, "sg_mppt2_voltage", "sg_mppt2_current"),
        requires=("sg_mppt2_voltage", "sg_mppt2_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="uid_sg_mppt3_power",
        name="MPPT3 power",
        compute=lambda d: _v_times_i(d, "sg_mppt3_voltage", "sg_mppt3_current"),
        requires=("sg_mppt3_voltage", "sg_mppt3_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="uid_sg_mppt4_power",
        name="MPPT4 power",
        compute=lambda d: _v_times_i(d, "sg_mppt4_voltage", "sg_mppt4_current"),
        requires=("sg_mppt4_voltage", "sg_mppt4_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    # Phase power = V × I.
    ComputedSensorDescription(
        key="sg_phase_a_power",
        name="Phase A power",
        compute=lambda d: _v_times_i(d, "sg_phase_a_voltage", "sg_phase_a_current"),
        requires=("sg_phase_a_voltage", "sg_phase_a_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_phase_b_power",
        name="Phase B power",
        compute=lambda d: _v_times_i(d, "sg_phase_b_voltage", "sg_phase_b_current"),
        requires=("sg_phase_b_voltage", "sg_phase_b_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_phase_c_power",
        name="Phase C power",
        compute=lambda d: _v_times_i(d, "sg_phase_c_voltage", "sg_phase_c_current"),
        requires=("sg_phase_c_voltage", "sg_phase_c_current"),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    # Coded values mapped to strings.
    ComputedSensorDescription(
        key="sg_inverter_state",
        name="Sungrow inverter state",
        compute=_running_state,
        requires=("uid_sg_running_state_raw",),
        device_class="enum",
    ),
    ComputedSensorDescription(
        key="sg_device_type",
        name="Sungrow device type",
        compute=_device_type,
        requires=("sg_dev_code",),
        device_class="enum",
    ),
    # Battery power: split into signed (= battery_power flipped/identity) and
    # one-sided positive views for charging/discharging meters.
    ComputedSensorDescription(
        key="sg_battery_charging_power_signed",
        name="Battery charging power signed",
        compute=lambda d: -int(d["sg_battery_power"]),
        requires=("sg_battery_power",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_charging_power",
        name="Battery charging power",
        compute=lambda d: max(0, int(d["sg_battery_charging_power_signed"])),
        requires=("sg_battery_charging_power_signed",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_discharging_power_signed",
        name="Battery discharging power signed",
        compute=lambda d: int(d["sg_battery_power"]),
        requires=("sg_battery_power",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_discharging_power",
        name="Battery discharging power",
        compute=lambda d: max(0, int(d["sg_battery_discharging_power_signed"])),
        requires=("sg_battery_discharging_power_signed",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    # Grid import / export = clamp(±export_power_raw).
    ComputedSensorDescription(
        key="sg_import_power",
        name="Import power",
        compute=lambda d: max(0, -int(d["sg_battery_export_power_raw"])),
        requires=("sg_battery_export_power_raw",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_export_power",
        name="Export power",
        compute=lambda d: max(0, int(d["sg_battery_export_power_raw"])),
        requires=("sg_battery_export_power_raw",),
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    # Battery SoC view that maps min/max-clamped ranges back to nominal 0..100%.
    ComputedSensorDescription(
        key="sg_battery_level_nom",
        name="Battery level (nominal)",
        compute=_battery_level_nom,
        requires=(
            "sg_battery_level",
            "uid_sg_battery_min_soc",
            "uid_sg_battery_max_soc",
        ),
        unit="%",
        device_class="battery",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_charge_nom",
        name="Battery charge (nominal)",
        compute=_battery_charge_nom,
        requires=(
            "uid_battery_capacity_high_precision",
            "sg_battery_level_nom",
        ),
        unit="kWh",
        device_class="energy_storage",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_charge",
        name="Battery charge",
        compute=_battery_charge,
        requires=(
            "uid_battery_capacity_high_precision",
            "sg_battery_level",
            "uid_sg_battery_min_soc",
            "uid_sg_battery_max_soc",
        ),
        unit="kWh",
        device_class="energy_storage",
        state_class="measurement",
    ),
    ComputedSensorDescription(
        key="sg_battery_charge_health_rated",
        name="Battery charge (health-rated)",
        compute=_battery_charge_health_rated,
        requires=("sg_battery_charge", "sg_battery_state_of_health"),
        unit="kWh",
        device_class="energy_storage",
        state_class="measurement",
    ),
    # Net consumption = pv − export + import − bat_charge + bat_discharge.
    ComputedSensorDescription(
        key="sg_daily_consumed_energy",
        name="Daily consumed energy",
        compute=_daily_consumed_energy,
        requires=(
            "sg_daily_pv_generation",
            "sg_daily_exported_energy",
            "sg_daily_imported_energy",
            "sg_daily_battery_charge",
            "sg_daily_battery_discharge",
        ),
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
    ComputedSensorDescription(
        key="sg_total_consumed_energy",
        name="Total consumed energy",
        compute=_total_consumed_energy,
        requires=(
            "sg_total_pv_generation",
            "sg_total_exported_energy",
            "sg_total_imported_energy",
            "sg_total_battery_charge",
            "sg_total_battery_discharge",
        ),
        unit="kWh",
        device_class="energy",
        state_class="total",
    ),
)


# --- COMPUTED BINARY SENSORS ----------------------------------------------
#
# All the legacy template binary sensors (and their *_delay duplicates) just
# checked individual bits of the power_flow_status register at 13000. The
# delay variants existed so users could attach HA debounce logic separately;
# they're identical-by-value copies and have been dropped.


def _bit(mask: int) -> Callable[[Mapping[str, Any]], bool]:
    def _check(d: Mapping[str, Any]) -> bool:
        return bool(int(d["uid_power_flow_status"]) & mask)
    return _check


COMPUTED_BINARY_SENSORS: tuple[ComputedBinarySensorDescription, ...] = (
    ComputedBinarySensorDescription(
        key="sg_pv_generating",
        name="PV generating",
        compute=_bit(0x01),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_battery_charging",
        name="Battery charging",
        compute=_bit(0x02),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_battery_discharging",
        name="Battery discharging",
        compute=_bit(0x04),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_positive_load_power",
        name="Positive Load Power",
        compute=_bit(0x08),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_exporting_power",
        name="Exporting Power",
        compute=_bit(0x10),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_importing_power",
        name="Importing Power",
        compute=_bit(0x20),
        requires=("uid_power_flow_status",),
    ),
    ComputedBinarySensorDescription(
        key="sg_negative_load_power",
        name="Negative Load Power",
        compute=_bit(0x80),
        requires=("uid_power_flow_status",),
    ),
)


# --- SELECTS --------------------------------------------------------------

SELECTS: tuple[SelectDescription, ...] = (
    SelectDescription(
        key="uid_ems_mode",
        name="EMS mode",
        source_key="sg_ems_mode_selection_raw",
        options=(
            "Self-consumption mode (default)",
            "Forced mode",
            "External EMS",
            "VPP",
        ),
        option_writes={
            "Self-consumption mode (default)": WriteRegisterAction(address=13049, value=0),
            "Forced mode": WriteRegisterAction(address=13049, value=2),
            "External EMS": WriteRegisterAction(address=13049, value=3),
            "VPP": WriteRegisterAction(address=13049, value=4),
        },
    ),
    SelectDescription(
        key="uid_battery_forced_charge_discharge",
        name="Battery forced charge discharge",
        source_key="sg_battery_forced_charge_discharge_cmd_raw",
        options=("Stop (default)", "Forced charge", "Forced discharge"),
        option_writes={
            "Stop (default)": WriteRegisterAction(address=13050, value=204),
            "Forced charge": WriteRegisterAction(address=13050, value=170),
            "Forced discharge": WriteRegisterAction(address=13050, value=187),
        },
    ),
    SelectDescription(
        key="uid_load_adjustment_mode",
        name="Load adjustment mode",
        source_key="sg_load_adjustment_mode_selection_raw",
        options=("Timing", "ON/OFF", "Power optimization", "Disabled"),
        option_writes={
            "Timing": WriteRegisterAction(address=13001, value=0),
            "ON/OFF": WriteRegisterAction(address=13001, value=1),
            "Power optimization": WriteRegisterAction(address=13001, value=2),
            "Disabled": WriteRegisterAction(address=13001, value=3),
        },
    ),
)


# --- NUMBERS ---------------------------------------------------------------

NUMBERS: tuple[NumberDescription, ...] = (
    NumberDescription(
        key="uid_battery_min_soc",
        name="Battery Min Soc",
        source_key="uid_sg_battery_min_soc",
        set_address=13058,
        set_scale=0.1,
        min_value=0.0,
        max_value=50.0,
        step=1.0,
        unit="%",
    ),
    NumberDescription(
        key="uid_battery_max_soc",
        name="Battery Max Soc",
        source_key="uid_sg_battery_max_soc",
        set_address=13057,
        set_scale=0.1,
        min_value=50.0,
        max_value=100.0,
        step=1.0,
        unit="%",
    ),
    NumberDescription(
        key="uid_battery_reserved_soc_for_backup",
        name="Battery Reserved SoC for Backup",
        source_key="sg_battery_reserved_soc_for_backup",
        set_address=13099,
        set_scale=1.0,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        unit="%",
    ),
    NumberDescription(
        key="uid_battery_charging_start_power",
        name="Battery charging start power",
        source_key="sg_battery_charging_start_power",
        set_address=33148,
        set_scale=10.0,
        min_value=0.0,
        max_value=1000.0,
        step=10.0,
        unit="W",
    ),
    NumberDescription(
        key="uid_battery_discharging_start_power",
        name="Battery discharging start power",
        source_key="sg_battery_discharging_start_power",
        set_address=33149,
        set_scale=10.0,
        min_value=0.0,
        max_value=1000.0,
        step=10.0,
        unit="W",
    ),
    NumberDescription(
        key="uid_battery_forced_charge_discharge_power",
        name="Battery forced charge discharge power",
        source_key="sg_battery_forced_charge_discharge_power",
        set_address=13051,
        set_scale=1.0,
        min_value=0.0,
        max_value=0.0,
        step=100.0,
        unit="W",
        max_from_config="battery_max_power",
    ),
    NumberDescription(
        key="uid_battery_max_charge_power",
        name="Battery max charge power",
        source_key="sg_battery_max_charge_power",
        set_address=33046,
        set_scale=10.0,
        min_value=10.0,
        max_value=0.0,
        step=100.0,
        unit="W",
        max_from_config="battery_max_power",
    ),
    NumberDescription(
        key="uid_battery_max_discharge_power",
        name="Battery max discharge power",
        source_key="sg_battery_max_discharge_power",
        set_address=33047,
        set_scale=10.0,
        min_value=10.0,
        max_value=0.0,
        step=100.0,
        unit="W",
        max_from_config="battery_max_power",
    ),
    NumberDescription(
        key="uid_export_power_limit",
        name="Export power limit",
        source_key="sg_export_power_limit",
        set_address=13073,
        # RT firmware accepts the value in 0.1-W units, RS in 1-W.
        set_scale=1.0,
        family_scale_overrides={"RT": 10.0},
        min_value=0.0,
        max_value=0.0,
        step=100.0,
        unit="W",
        max_source_key="sg_inverter_rated_output",
    ),
)


MODBUS_SWITCHES: tuple[ModbusSwitchDescription, ...] = (
    ModbusSwitchDescription(
        key='sg_backup_mode_switch',
        name='Backup Mode',
        address=13074,
        write_type='holding',
        command_on=0xAA,
        command_off=0x55,
        verify_input_type='holding',
        verify_address=13074,
        verify_state_on=0xAA,
        verify_state_off=0x55,
    ),
    ModbusSwitchDescription(
        key='sg_export_power_limit_switch',
        name='Export power limit',
        address=13086,
        write_type='holding',
        command_on=0xAA,
        command_off=0x55,
        verify_input_type='holding',
        verify_address=13086,
        verify_state_on=0xAA,
        verify_state_off=0x55,
    ),
    ModbusSwitchDescription(
        key='sg_load_adjustment_mode_switch',
        name='Load adjustment mode',
        address=13010,
        write_type='holding',
        command_on=0xAA,
        command_off=0x55,
        verify_input_type='holding',
        verify_address=13010,
        verify_state_on=0xAA,
        verify_state_off=0x55,
    ),
)
