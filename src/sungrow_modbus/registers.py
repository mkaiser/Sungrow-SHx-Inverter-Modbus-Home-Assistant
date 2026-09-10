"""Sungrow inverter registers, generated from the YAML package.

Do not edit by hand: `scripts/generate_registers.py` writes this file from
[doc/legacy_entity_map.json](../../doc/legacy_entity_map.json), and CI checks
that it matches. Hand-written register knowledge — the identity block, decoded
enumerations, derived values — lives in `components.py` instead.

Addresses are protocol addresses, one below the register number printed in
Sungrow's documentation and in the YAML's comments. Sungrow sends 32-bit
values low word first, which the YAML spells `swap: word` and this spells
`word_order="little"`.

Each class is one poll interval in one register space, because a Component
reads a single space and the integration gives each interval its own
coordinator.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, int32, integer, string, uint32


class InverterRealtimeInput(Component):
    """3 input registers, polled every 5s."""

    register_space = "input"

    running_state_raw = integer(12999, signed=False)
    """Running state raw (reg 13000)."""
    power_flow_status = integer(13000, signed=False)
    """Power Flow Status (reg 13001)."""
    load_power = int32(13007, word_order="little", nan=2147483647, unit="W")
    """Load power (reg 13008)."""


class InverterFastInput(Component):
    """36 input registers, polled every 10s."""

    register_space = "input"

    mppt1_voltage = gauge(5010, 0.1, signed=False, unit="V")
    """MPPT1 voltage (reg 5011)."""
    mppt1_current = gauge(5011, 0.1, signed=False, unit="A")
    """MPPT1 current (reg 5012)."""
    mppt2_voltage = gauge(5012, 0.1, signed=False, unit="V")
    """MPPT2 voltage (reg 5013)."""
    mppt2_current = gauge(5013, 0.1, signed=False, unit="A")
    """MPPT2 current (reg 5014)."""
    mppt3_voltage = gauge(5014, 0.1, signed=False, nan=65535, unit="V")
    """MPPT3 voltage (reg 5015)."""
    mppt3_current = gauge(5015, 0.1, signed=False, nan=65535, unit="A")
    """MPPT3 current (reg 5016)."""
    total_dc_power = uint32(5016, word_order="little", unit="W")
    """Total DC power (reg 5017)."""
    phase_a_voltage = gauge(5018, 0.1, signed=False, unit="V")
    """Phase A voltage (reg 5019)."""
    phase_b_voltage = gauge(5019, 0.1, signed=False, unit="V")
    """Phase B voltage (reg 5020)."""
    phase_c_voltage = gauge(5020, 0.1, signed=False, unit="V")
    """Phase C voltage (reg 5021)."""
    reactive_power = int32(5032, word_order="little", unit="W")
    """Reactive power (reg 5033)."""
    power_factor = gauge(5034, 0.001, signed=True)
    """Power factor (reg 5035)."""
    mppt4_voltage = gauge(5114, 0.1, signed=False, nan=65535, unit="V")
    """MPPT4 voltage (reg 5115)."""
    mppt4_current = gauge(5115, 0.1, signed=False, nan=65535, unit="A")
    """MPPT4 current (reg 5116)."""
    grid_frequency = gauge(5241, 0.01, signed=False, unit="Hz")
    """Grid frequency (reg 5242)."""
    meter_active_power = int32(5600, word_order="little", nan=2147483647, unit="W")
    """Meter active power (reg 5601)."""
    meter_phase_a_active_power = int32(
        5602, word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase A active power (reg 5603)."""
    meter_phase_b_active_power = int32(
        5604, word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase B active power (reg 5605)."""
    meter_phase_c_active_power = int32(
        5606, word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase C active power (reg 5607)."""
    battery_current = gauge(5630, 0.1, signed=True, unit="A")
    """Battery current (reg 5631)."""
    backup_phase_a_power = integer(5722, signed=True, unit="W")
    """Backup phase A power (reg 5723)."""
    backup_phase_b_power = integer(5723, signed=True, unit="W")
    """Backup phase B power (reg 5724)."""
    backup_phase_c_power = integer(5724, signed=True, unit="W")
    """Backup phase C power (reg 5725)."""
    total_backup_power = int32(5725, word_order="little", unit="W")
    """Total backup power (reg 5726)."""
    meter_phase_a_voltage = gauge(5740, 0.1, signed=True, nan=32767, unit="V")
    """Meter phase A voltage (reg 5741)."""
    meter_phase_b_voltage = gauge(5741, 0.1, signed=True, nan=32767, unit="V")
    """Meter phase B voltage (reg 5742)."""
    meter_phase_c_voltage = gauge(5742, 0.1, signed=True, nan=32767, unit="V")
    """Meter phase C voltage (reg 5743)."""
    meter_phase_a_current = gauge(5743, 0.01, signed=False, nan=65535, unit="A")
    """Meter phase A current (reg 5744)."""
    meter_phase_b_current = gauge(5744, 0.01, signed=False, nan=65535, unit="A")
    """Meter phase B current (reg 5745)."""
    meter_phase_c_current = gauge(5745, 0.01, signed=False, nan=65535, unit="A")
    """Meter phase C current (reg 5746)."""
    export_power_raw = int32(13009, word_order="little", nan=2147483647, unit="W")
    """Export power raw (reg 13010)."""
    battery_voltage = gauge(13019, 0.1, signed=False, unit="V")
    """Battery voltage (reg 13020)."""
    phase_a_current = gauge(13030, 0.1, signed=True, unit="A")
    """Phase A current (reg 13031)."""
    phase_b_current = gauge(13031, 0.1, signed=True, unit="A")
    """Phase B current (reg 13032)."""
    phase_c_current = gauge(13032, 0.1, signed=True, unit="A")
    """Phase C current (reg 13033)."""
    total_active_power = int32(13033, word_order="little", unit="W")
    """Total active power (reg 13034)."""


class InverterBatteryPower(Component):
    """1 input register, polled every 10s.

    Battery power at register 5214, which one measured firmware refuses on
    the inverter's own LAN port while serving it through a WiNet-S.
    """

    register_space = "input"

    battery_power = int32(5213, word_order="little", unit="W")
    """Battery power (reg 5214)."""


class InverterMeterChannel2(Component):
    """4 input registers, polled every 10s.

    A second metering channel, which most installations do not have and
    some firmware answers by closing the connection.
    """

    register_space = "input"

    meter_channel_2_total_active_power = int32(
        13199, word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 total active power (reg 13200)."""
    meter_channel_2_phase_a_active_power = int32(
        13201, word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase A active power (reg 13202)."""
    meter_channel_2_phase_b_active_power = int32(
        13203, word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase B active power (reg 13204)."""
    meter_channel_2_phase_c_active_power = int32(
        13205, word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase C active power (reg 13206)."""


class InverterFastHolding(Component):
    """19 holding registers, polled every 10s."""

    register_space = "holding"

    load_adjustment_mode_selection_raw = integer(13001, signed=False, writable=True)
    """Load adjustment mode selection raw (reg 13002)."""
    load_adjustment_mode_enable_raw = integer(13010, signed=False, writable=True)
    """Load adjustment mode enable raw (reg 13011)."""
    pv_power_limitation_raw = integer(13017, signed=False, nan=65535)
    """PV power limitation raw (reg 13018)."""
    ems_mode_selection_raw = integer(13049, signed=False, writable=True)
    """EMS mode selection raw (reg 13050)."""
    battery_forced_charge_discharge_cmd_raw = integer(
        13050, signed=False, writable=True
    )
    """Battery forced charge discharge cmd raw (reg 13051)."""
    battery_forced_charge_discharge_power = integer(
        13051, signed=False, unit="W", writable=True
    )
    """Battery forced charge discharge power (reg 13052)."""
    battery_max_soc = gauge(13057, 0.1, signed=False, unit="%", writable=True)
    """Battery max SoC (reg 13058)."""
    battery_min_soc = gauge(13058, 0.1, signed=False, unit="%", writable=True)
    """Battery min SoC (reg 13059)."""
    export_power_limit = integer(13073, signed=False, unit="W", writable=True)
    """Export power limit (reg 13074)."""
    backup_mode_raw = integer(13074, signed=False, writable=True)
    """Backup mode raw (reg 13075)."""
    export_power_limit_mode_raw = integer(13086, signed=False, writable=True)
    """Export power limit mode raw (reg 13087)."""
    feed_in_limitation_ratio = gauge(13087, 0.1, signed=False, nan=65535, unit="%")
    """Feed-in limitation ratio (reg 13088)."""
    active_power_limitation_raw = integer(13088, signed=False)
    """Active power limitation raw (reg 13089)."""
    active_power_limitation_ratio_raw = gauge(13089, 0.1, signed=False, unit="%")
    """Active power limitation ratio raw (reg 13090)."""
    battery_reserved_soc_for_backup = integer(
        13099, signed=False, unit="%", writable=True
    )
    """Battery reserved SoC for backup (reg 13100)."""
    battery_max_charge_power = gauge(33046, 10, signed=False, unit="W", writable=True)
    """Battery max charge power (reg 33047)."""
    battery_max_discharge_power = gauge(
        33047, 10, signed=False, unit="W", writable=True
    )
    """Battery max discharge power (reg 33048)."""
    battery_charging_start_power = gauge(
        33148, 10, signed=False, nan=65535, unit="W", writable=True
    )
    """Battery charging start power (reg 33149)."""
    battery_discharging_start_power = gauge(
        33149, 10, signed=False, nan=65535, unit="W", writable=True
    )
    """Battery discharging start power (reg 33150)."""


class InverterAplShutdownAtZero(Component):
    """1 holding register, polled every 10s.

    The active-power-limit shutdown flag at register 31213, refused by one
    measured firmware on the inverter's own LAN port. **Experimental and
    unverified:** this register is not in Sungrow's protocol document --
    the comment that added it to the YAML package says so outright -- and
    it comes from community feedback in issue #554, a request for ramping
    PV production down. What it does is inferred from its name, whether the
    inverter shuts down when the active power limit is set to zero or idles
    at zero output, and nobody here has tested it. All three surveyed
    inverters read 85 (0x55), one value three times, so its 0xAA/0x55 pair
    is a convention assumed rather than observed -- which is why it stays a
    number instead of becoming a binary sensor like the two documented mode
    registers beside it.
    """

    register_space = "holding"

    apl_shutdown_at_zero_raw = integer(31212, signed=False)
    """APL shutdown at zero raw (reg 31213)."""


class InverterMediumInput(Component):
    """3 input registers, polled every 60s."""

    register_space = "input"

    inverter_temperature = gauge(5007, 0.1, signed=True, unit="°C")
    """Inverter temperature (reg 5008)."""
    battery_level = gauge(13022, 0.1, signed=False, unit="%")
    """Battery level (reg 13023)."""
    battery_temperature = gauge(13024, 0.1, signed=True, unit="°C")
    """Battery temperature (reg 13025)."""


class InverterSlowestInput(Component):
    """33 input registers, polled every 600s."""

    register_space = "input"

    sungrow_version_1 = string(2581, 11)
    """Sungrow Version 1 (reg 2582)."""
    sungrow_version_2 = string(2596, 11)
    """Sungrow Version 2 (reg 2597)."""
    sungrow_protocol_version = uint32(4951, word_order="little")
    """Sungrow Protocol Version (reg 4952)."""
    sungrow_arm_software = string(4953, 15)
    """Sungrow Arm Software (reg 4954)."""
    sungrow_dsp_software = string(4968, 15)
    """Sungrow DSP Software (reg 4969)."""
    sungrow_inverter_serial = string(4989, 10)
    """Sungrow inverter serial (reg 4990)."""
    sungrow_device_type_code = integer(4999, signed=False)
    """Sungrow device type code (reg 5000)."""
    inverter_rated_output = gauge(5000, 100, signed=False, unit="W")
    """Inverter rated output (reg 5001)."""
    daily_pv_generation_battery_discharge = gauge(5002, 0.1, signed=False, unit="kWh")
    """Daily PV generation & battery discharge (reg 5003)."""
    total_pv_generation_battery_discharge = uint32(
        5003, scale=0.1, word_order="little", unit="kWh"
    )
    """Total PV generation & battery discharge (reg 5004)."""
    export_power_limit_min = gauge(5621, 10, signed=False, nan=65535, unit="W")
    """Export power limit min (reg 5622)."""
    export_power_limit_max = gauge(5622, 10, signed=False, nan=65535, unit="W")
    """Export power limit max (reg 5623)."""
    bdc_rated_power = gauge(5627, 100, signed=False, unit="W")
    """BDC rated power (reg 5628)."""
    bms_max_charging_current = integer(5634, signed=False, unit="A")
    """BMS max. charging current (reg 5635)."""
    bms_max_discharging_current = integer(5635, signed=False, unit="A")
    """BMS max. discharging current (reg 5636)."""
    battery_capacity_high_precision = gauge(5638, 0.01, signed=False, unit="kWh")
    """Battery capacity high precision (reg 5639)."""
    daily_pv_generation = gauge(13001, 0.1, signed=False, unit="kWh")
    """Daily PV generation (reg 13002)."""
    total_pv_generation = uint32(13002, scale=0.1, word_order="little", unit="kWh")
    """Total PV generation (reg 13003)."""
    daily_exported_energy_from_pv = gauge(13004, 0.1, signed=False, unit="kWh")
    """Daily exported energy from PV (reg 13005)."""
    total_exported_energy_from_pv = uint32(
        13005, scale=0.1, word_order="little", unit="kWh"
    )
    """Total exported energy from PV (reg 13006)."""
    daily_battery_charge_from_pv = gauge(13011, 0.1, signed=False, unit="kWh")
    """Daily battery charge from PV (reg 13012)."""
    total_battery_charge_from_pv = uint32(
        13012, scale=0.1, word_order="little", unit="kWh"
    )
    """Total battery charge from PV (reg 13013)."""
    daily_direct_energy_consumption = gauge(13016, 0.1, signed=False, unit="kWh")
    """Daily direct energy consumption (reg 13017)."""
    total_direct_energy_consumption = uint32(
        13017, scale=0.1, word_order="little", unit="kWh"
    )
    """Total direct energy consumption (reg 13018)."""
    battery_state_of_health = gauge(13023, 0.1, signed=False, unit="%")
    """Battery state of health (reg 13024)."""
    daily_battery_discharge = gauge(13025, 0.1, signed=False, unit="kWh")
    """Daily battery discharge (reg 13026)."""
    total_battery_discharge = uint32(13026, scale=0.1, word_order="little", unit="kWh")
    """Total battery discharge (reg 13027)."""
    daily_imported_energy = gauge(13035, 0.1, signed=False, unit="kWh")
    """Daily imported energy (reg 13036)."""
    total_imported_energy = uint32(13036, scale=0.1, word_order="little", unit="kWh")
    """Total imported energy (reg 13037)."""
    daily_battery_charge = gauge(13039, 0.1, signed=False, unit="kWh")
    """Daily battery charge (reg 13040)."""
    total_battery_charge = uint32(13040, scale=0.1, word_order="little", unit="kWh")
    """Total battery charge (reg 13041)."""
    daily_exported_energy = gauge(13044, 0.1, signed=False, unit="kWh")
    """Daily exported energy (reg 13045)."""
    total_exported_energy = uint32(13045, scale=0.1, word_order="little", unit="kWh")
    """Total exported energy (reg 13046)."""


class InverterBatteryFirmware(Component):
    """1 input register, polled every 600s.

    The battery firmware string, which the YAML package documents as being
    for Sungrow batteries only.
    """

    register_space = "input"

    sungrow_version_4_sungrow_battery = string(2628, 15)
    """Sungrow Version 4 (Sungrow Battery) (reg 2629)."""


class InverterFirmwareBlockBattery(Component):
    """1 input register, polled every 600s.

    The battery firmware string at register 13280, which some firmware
    answers by closing the connection.
    """

    register_space = "input"

    battery_firmware_version = string(13279, 15)
    """Battery Firmware Version (reg 13280)."""


class InverterFirmwareBlockCommunicationModule(Component):
    """1 input register, polled every 600s.

    The communication module's firmware string at register 13265, absent on
    a direct LAN connection and read on its own because some firmware
    answers it by closing the connection.
    """

    register_space = "input"

    communication_module_firmware_version = string(13264, 15)
    """Communication Module Firmware Version (reg 13265)."""


class InverterFirmwareBlockInverter(Component):
    """1 input register, polled every 600s.

    The inverter firmware string at register 13250, which some firmware
    answers by closing the connection.
    """

    register_space = "input"

    inverter_firmware_version = string(13249, 15)
    """Inverter Firmware Version (reg 13250)."""


class InverterSubControllerFirmware(Component):
    """1 input register, polled every 600s.

    The sub-controller firmware string, which some firmware versions do not
    publish at all.
    """

    register_space = "input"

    sungrow_version_3 = string(2612, 15)
    """Sungrow Version 3 (reg 2613)."""


#: Attribute name on the device to the Component it holds.
COMPONENTS: dict[str, type[Component]] = {
    "realtime_input": InverterRealtimeInput,
    "fast_input": InverterFastInput,
    "battery_power": InverterBatteryPower,
    "meter_channel_2": InverterMeterChannel2,
    "fast_holding": InverterFastHolding,
    "apl_shutdown_at_zero": InverterAplShutdownAtZero,
    "medium_input": InverterMediumInput,
    "slowest_input": InverterSlowestInput,
    "battery_firmware": InverterBatteryFirmware,
    "firmware_block_battery": InverterFirmwareBlockBattery,
    "firmware_block_communication_module": InverterFirmwareBlockCommunicationModule,
    "firmware_block_inverter": InverterFirmwareBlockInverter,
    "sub_controller_firmware": InverterSubControllerFirmware,
}

#: Tier name to the components read at its interval.
TIER_COMPONENTS: dict[str, tuple[str, ...]] = {
    "realtime": ("realtime_input",),
    "fast": (
        "fast_input",
        "battery_power",
        "meter_channel_2",
        "fast_holding",
        "apl_shutdown_at_zero",
    ),
    "medium": ("medium_input",),
    "slowest": (
        "slowest_input",
        "battery_firmware",
        "firmware_block_battery",
        "firmware_block_communication_module",
        "firmware_block_inverter",
        "sub_controller_firmware",
    ),
}

#: How often each tier is polled unless the user says otherwise.
DEFAULT_INTERVALS: dict[str, int] = {
    "realtime": 5,
    "fast": 10,
    "medium": 60,
    "slowest": 600,
}
