"""Sungrow inverter registers, generated from the YAML package.

Do not edit by hand: `scripts/generate_registers.py` writes this file from
[doc/legacy_entity_map.json](../../doc/legacy_entity_map.json), and CI checks
that it matches. Hand-written register knowledge — the identity block, decoded
enumerations, derived values — lives in `components.py` instead.

Registers are declared by the number Sungrow's documentation and the YAML's
comments give them; `reg()` turns that into the protocol address, one below,
which is what goes on the wire. Sungrow sends 32-bit
values low word first, which the YAML spells `swap: word` and this spells
`word_order="little"`.

Each class is one poll interval in one register space, because a Component
reads a single space and the integration gives each interval its own
coordinator.
"""

from __future__ import annotations

from typing import Any

from modbus_connection.model import (
    Component,
    NumberField,
    gauge,
    int32,
    integer,
    string,
    uint32,
)

from .addresses import reg


class AsymmetricNumberField(NumberField[int]):
    """A register that reads in one unit and writes in another.

    Every other register in this map uses one scale for both directions, which
    is what `NumberField` is built for: `encode` and `decode` share `scale`.
    Register 13074 does not. It **reads** in watts -- 10000 back against a
    10000 W maximum from register 5623, so the read side agrees with its own
    bounds -- and **writes** in tens of watts, multiplying the word it is
    handed by ten before storing it.

    Measured 2026-09-19 on the reference SH10RT with feed-in limitation on, six
    times, including values no rounding could produce (123 -> 1230, 47 -> 470),
    and replicated the same day at a second house on an SH10RT-20 through a
    dongle. Two houses, two models, two transports.

    It also explains the refusals: the multiply happens **before** the range
    check, so writing 3400 becomes 34000, fails against the 10000 W maximum and
    returns exception 0x04 -- which is why restoring 10000 was refused while the
    register sat on 10000, and why writing 1000 is how you actually put 10000
    back.

    So this is a device quirk rather than a second scale: `scale` stays 1
    because that is what the register *contains*, and only the write side is
    divided. `control_test.py`'s `spec_units_per_count` stays 1 for the same
    reason, and its leg B is what proves this on hardware -- before the fix a
    900 W write left the raw word at 9000 and the verdict was `SCALED`.
    """

    def __init__(
        self, address: int, *, write_units_per_count: float, **kwargs: Any
    ) -> None:
        """Initialize the field with a write scale of its own.

        Refuses a field that also has a read `scale`. The two divisions would
        compose -- `encode` would divide by the write scale and then the base
        class would divide by the read one -- and the result would be wrong by
        their product while still looking like a plain number in the register.
        Nothing needs that combination today, so it is refused rather than
        guessed at.
        """
        super().__init__(address, **kwargs)
        if self.scale != 1:
            raise ValueError(
                "an asymmetric write scale needs a read scale of 1; "
                f"{address} has {self.scale}"
            )
        self.write_units_per_count = write_units_per_count

    def encode(self, value: Any, scale_exponent: int | None = None) -> list[int]:
        """Encode the engineering value at the **write** scale.

        Rounded here rather than left to the base class, which takes a fast
        path on a scale-1 field -- `raw = int(value)` -- and would silently
        **truncate** a value the division does not leave whole.
        """
        raw = round(float(value) / self.write_units_per_count)
        return super().encode(float(raw), scale_exponent)


class InverterRealtimeInput(Component):
    """3 input registers, polled every 5s."""

    register_space = "input"

    running_state_raw = integer(reg(13000), signed=False)
    """Running state raw."""
    power_flow_status = integer(reg(13001), signed=False)
    """Power Flow Status."""
    load_power = int32(reg(13008), word_order="little", nan=2147483647, unit="W")
    """Load power."""


class InverterFastInput(Component):
    """43 input registers, polled every 10s."""

    register_space = "input"

    mppt1_voltage = gauge(reg(5011), 0.1, signed=False, unit="V")
    """MPPT1 voltage."""
    mppt1_current = gauge(reg(5012), 0.1, signed=False, unit="A")
    """MPPT1 current."""
    mppt2_voltage = gauge(reg(5013), 0.1, signed=False, unit="V")
    """MPPT2 voltage."""
    mppt2_current = gauge(reg(5014), 0.1, signed=False, unit="A")
    """MPPT2 current."""
    mppt3_voltage = gauge(reg(5015), 0.1, signed=False, nan=65535, unit="V")
    """MPPT3 voltage."""
    mppt3_current = gauge(reg(5016), 0.1, signed=False, nan=65535, unit="A")
    """MPPT3 current."""
    total_dc_power = uint32(reg(5017), word_order="little", unit="W")
    """Total DC power."""
    phase_a_voltage = gauge(reg(5019), 0.1, signed=False, unit="V")
    """Phase A voltage."""
    phase_b_voltage = gauge(reg(5020), 0.1, signed=False, unit="V")
    """Phase B voltage."""
    phase_c_voltage = gauge(reg(5021), 0.1, signed=False, unit="V")
    """Phase C voltage."""
    reactive_power = int32(reg(5033), word_order="little", unit="W")
    """Reactive power."""
    power_factor = gauge(reg(5035), 0.001, signed=True)
    """Power factor."""
    mppt4_voltage = gauge(reg(5115), 0.1, signed=False, nan=65535, unit="V")
    """MPPT4 voltage."""
    mppt4_current = gauge(reg(5116), 0.1, signed=False, nan=65535, unit="A")
    """MPPT4 current."""
    grid_frequency = gauge(reg(5242), 0.01, signed=False, unit="Hz")
    """Grid frequency."""
    meter_active_power = int32(reg(5601), word_order="little", nan=2147483647, unit="W")
    """Meter active power."""
    meter_phase_a_active_power = int32(
        reg(5603), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase A active power."""
    meter_phase_b_active_power = int32(
        reg(5605), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase B active power."""
    meter_phase_c_active_power = int32(
        reg(5607), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase C active power."""
    battery_current = gauge(reg(5631), 0.1, signed=True, unit="A")
    """Battery current."""
    backup_phase_a_current = gauge(reg(5720), 0.1, signed=True, nan=32767, unit="A")
    """Backup phase A current."""
    backup_phase_b_current = gauge(reg(5721), 0.1, signed=True, nan=32767, unit="A")
    """Backup phase B current."""
    backup_phase_c_current = gauge(reg(5722), 0.1, signed=True, nan=32767, unit="A")
    """Backup phase C current."""
    backup_phase_a_power = integer(reg(5723), signed=True, unit="W")
    """Backup phase A power."""
    backup_phase_b_power = integer(reg(5724), signed=True, unit="W")
    """Backup phase B power."""
    backup_phase_c_power = integer(reg(5725), signed=True, unit="W")
    """Backup phase C power."""
    total_backup_power = int32(reg(5726), word_order="little", unit="W")
    """Total backup power."""
    backup_phase_a_voltage = gauge(reg(5731), 0.1, signed=False, nan=65535, unit="V")
    """Backup phase A voltage."""
    backup_phase_b_voltage = gauge(reg(5732), 0.1, signed=False, nan=65535, unit="V")
    """Backup phase B voltage."""
    backup_phase_c_voltage = gauge(reg(5733), 0.1, signed=False, nan=65535, unit="V")
    """Backup phase C voltage."""
    backup_frequency = gauge(reg(5734), 0.01, signed=False, nan=65535, unit="Hz")
    """Backup frequency."""
    meter_phase_a_voltage = gauge(reg(5741), 0.1, signed=True, nan=32767, unit="V")
    """Meter phase A voltage."""
    meter_phase_b_voltage = gauge(reg(5742), 0.1, signed=True, nan=32767, unit="V")
    """Meter phase B voltage."""
    meter_phase_c_voltage = gauge(reg(5743), 0.1, signed=True, nan=32767, unit="V")
    """Meter phase C voltage."""
    meter_phase_a_current = gauge(reg(5744), 0.01, signed=False, nan=65535, unit="A")
    """Meter phase A current."""
    meter_phase_b_current = gauge(reg(5745), 0.01, signed=False, nan=65535, unit="A")
    """Meter phase B current."""
    meter_phase_c_current = gauge(reg(5746), 0.01, signed=False, nan=65535, unit="A")
    """Meter phase C current."""
    export_power_raw = int32(reg(13010), word_order="little", nan=2147483647, unit="W")
    """Export power raw."""
    battery_voltage = gauge(reg(13020), 0.1, signed=False, unit="V")
    """Battery voltage."""
    phase_a_current = gauge(reg(13031), 0.1, signed=True, unit="A")
    """Phase A current."""
    phase_b_current = gauge(reg(13032), 0.1, signed=True, unit="A")
    """Phase B current."""
    phase_c_current = gauge(reg(13033), 0.1, signed=True, unit="A")
    """Phase C current."""
    total_active_power = int32(reg(13034), word_order="little", unit="W")
    """Total active power."""


class InverterBatteryPower(Component):
    """1 input register, polled every 10s.

    Battery power at register 5214, which one measured firmware refuses on
    the inverter's own LAN port while serving it through a WiNet-S.
    """

    register_space = "input"

    battery_power = int32(reg(5214), word_order="little", unit="W")
    """Battery power."""


class InverterMeterChannel2(Component):
    """4 input registers, polled every 10s.

    A second metering channel, which most installations do not have and
    some firmware answers by closing the connection.
    """

    register_space = "input"

    meter_channel_2_total_active_power = int32(
        reg(13200), word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 total active power."""
    meter_channel_2_phase_a_active_power = int32(
        reg(13202), word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase A active power."""
    meter_channel_2_phase_b_active_power = int32(
        reg(13204), word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase B active power."""
    meter_channel_2_phase_c_active_power = int32(
        reg(13206), word_order="little", nan=2147483647, unit="W"
    )
    """Meter channel 2 phase C active power."""


class InverterFastHolding(Component):
    """20 holding registers, polled every 10s."""

    register_space = "holding"

    load_adjustment_mode_selection_raw = integer(
        reg(13002), signed=False, writable=True
    )
    """Load adjustment mode selection raw."""
    load_adjustment_mode_enable_raw = integer(reg(13011), signed=False, writable=True)
    """Load adjustment mode enable raw."""
    forced_startup_under_low_soc_raw = integer(reg(13017), signed=False, nan=65535)
    """Forced startup under low SoC raw."""
    pv_power_limitation_raw = integer(reg(13018), signed=False, nan=65535)
    """PV power limitation raw."""
    ems_mode_selection_raw = integer(reg(13050), signed=False, writable=True)
    """EMS mode selection raw."""
    battery_forced_charge_discharge_cmd_raw = integer(
        reg(13051), signed=False, writable=True
    )
    """Battery forced charge discharge cmd raw."""
    battery_forced_charge_discharge_power = integer(
        reg(13052), signed=False, unit="W", writable=True
    )
    """Battery forced charge discharge power."""
    battery_max_soc = gauge(reg(13058), 0.1, signed=False, unit="%", writable=True)
    """Battery max SoC."""
    battery_min_soc = gauge(reg(13059), 0.1, signed=False, unit="%", writable=True)
    """Battery min SoC."""
    export_power_limit = AsymmetricNumberField(
        reg(13074), signed=False, unit="W", writable=True, write_units_per_count=10
    )
    """Export power limit."""
    backup_mode_raw = integer(reg(13075), signed=False, writable=True)
    """Backup mode raw."""
    export_power_limit_mode_raw = integer(reg(13087), signed=False, writable=True)
    """Export power limit mode raw."""
    feed_in_limitation_ratio = gauge(reg(13088), 0.1, signed=False, nan=65535, unit="%")
    """Feed-in limitation ratio."""
    active_power_limitation_raw = integer(reg(13089), signed=False)
    """Active power limitation raw."""
    active_power_limitation_ratio_raw = gauge(reg(13090), 0.1, signed=False, unit="%")
    """Active power limitation ratio raw."""
    battery_reserved_soc_for_backup = integer(
        reg(13100), signed=False, unit="%", writable=True
    )
    """Battery reserved SoC for backup."""
    battery_max_charge_power = gauge(
        reg(33047), 10, signed=False, unit="W", writable=True
    )
    """Battery max charge power."""
    battery_max_discharge_power = gauge(
        reg(33048), 10, signed=False, unit="W", writable=True
    )
    """Battery max discharge power."""
    battery_charging_start_power = gauge(
        reg(33149), 10, signed=False, nan=65535, unit="W", writable=True
    )
    """Battery charging start power."""
    battery_discharging_start_power = gauge(
        reg(33150), 10, signed=False, nan=65535, unit="W", writable=True
    )
    """Battery discharging start power."""


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

    apl_shutdown_at_zero_raw = integer(reg(31213), signed=False)
    """APL shutdown at zero raw."""


class InverterMediumInput(Component):
    """3 input registers, polled every 60s."""

    register_space = "input"

    inverter_temperature = gauge(reg(5008), 0.1, signed=True, unit="°C")
    """Inverter temperature."""
    battery_level = gauge(reg(13023), 0.1, signed=False, unit="%")
    """Battery level."""
    battery_temperature = gauge(reg(13025), 0.1, signed=True, unit="°C")
    """Battery temperature."""


class InverterSlowestInput(Component):
    """34 input registers, polled every 600s."""

    register_space = "input"

    sungrow_version_1 = string(reg(2582), 11)
    """Sungrow Version 1."""
    sungrow_version_2 = string(reg(2597), 11)
    """Sungrow Version 2."""
    sungrow_protocol_version = uint32(reg(4952), word_order="little")
    """Sungrow Protocol Version."""
    sungrow_arm_software = string(reg(4954), 15)
    """Sungrow Arm Software."""
    sungrow_dsp_software = string(reg(4969), 15)
    """Sungrow DSP Software."""
    sungrow_inverter_serial = string(reg(4990), 10)
    """Sungrow inverter serial."""
    sungrow_device_type_code = integer(reg(5000), signed=False)
    """Sungrow device type code."""
    inverter_rated_output = gauge(reg(5001), 100, signed=False, unit="W")
    """Inverter rated output."""
    daily_pv_generation_battery_discharge = gauge(
        reg(5003), 0.1, signed=False, unit="kWh"
    )
    """Daily PV generation & battery discharge."""
    total_pv_generation_battery_discharge = uint32(
        reg(5004), scale=0.1, word_order="little", unit="kWh"
    )
    """Total PV generation & battery discharge."""
    export_power_limit_min = gauge(reg(5622), 10, signed=False, nan=65535, unit="W")
    """Export power limit min."""
    export_power_limit_max = gauge(reg(5623), 10, signed=False, nan=65535, unit="W")
    """Export power limit max."""
    bdc_rated_power = gauge(reg(5628), 100, signed=False, unit="W")
    """BDC rated power."""
    bms_max_charging_current = integer(reg(5635), signed=False, unit="A")
    """BMS max. charging current."""
    bms_max_discharging_current = integer(reg(5636), signed=False, unit="A")
    """BMS max. discharging current."""
    battery_capacity_high_precision = gauge(reg(5639), 0.01, signed=False, unit="kWh")
    """Battery capacity high precision."""
    daily_pv_generation = gauge(reg(13002), 0.1, signed=False, unit="kWh")
    """Daily PV generation."""
    total_pv_generation = uint32(reg(13003), scale=0.1, word_order="little", unit="kWh")
    """Total PV generation."""
    daily_exported_energy_from_pv = gauge(reg(13005), 0.1, signed=False, unit="kWh")
    """Daily exported energy from PV."""
    total_exported_energy_from_pv = uint32(
        reg(13006), scale=0.1, word_order="little", unit="kWh"
    )
    """Total exported energy from PV."""
    daily_battery_charge_from_pv = gauge(reg(13012), 0.1, signed=False, unit="kWh")
    """Daily battery charge from PV."""
    total_battery_charge_from_pv = uint32(
        reg(13013), scale=0.1, word_order="little", unit="kWh"
    )
    """Total battery charge from PV."""
    daily_direct_energy_consumption = gauge(reg(13017), 0.1, signed=False, unit="kWh")
    """Daily direct energy consumption."""
    total_direct_energy_consumption = uint32(
        reg(13018), scale=0.1, word_order="little", unit="kWh"
    )
    """Total direct energy consumption."""
    battery_state_of_health = gauge(reg(13024), 0.1, signed=False, unit="%")
    """Battery state of health."""
    daily_battery_discharge = gauge(reg(13026), 0.1, signed=False, unit="kWh")
    """Daily battery discharge."""
    total_battery_discharge = uint32(
        reg(13027), scale=0.1, word_order="little", unit="kWh"
    )
    """Total battery discharge."""
    self_consumption_of_today = gauge(
        reg(13029), 0.1, signed=False, nan=65535, unit="%"
    )
    """Self-consumption of today."""
    daily_imported_energy = gauge(reg(13036), 0.1, signed=False, unit="kWh")
    """Daily imported energy."""
    total_imported_energy = uint32(
        reg(13037), scale=0.1, word_order="little", unit="kWh"
    )
    """Total imported energy."""
    daily_battery_charge = gauge(reg(13040), 0.1, signed=False, unit="kWh")
    """Daily battery charge."""
    total_battery_charge = uint32(
        reg(13041), scale=0.1, word_order="little", unit="kWh"
    )
    """Total battery charge."""
    daily_exported_energy = gauge(reg(13045), 0.1, signed=False, unit="kWh")
    """Daily exported energy."""
    total_exported_energy = uint32(
        reg(13046), scale=0.1, word_order="little", unit="kWh"
    )
    """Total exported energy."""


class InverterBatteryFirmware(Component):
    """1 input register, polled every 600s.

    The battery firmware string, which the YAML package documents as being
    for Sungrow batteries only.
    """

    register_space = "input"

    sungrow_version_4_sungrow_battery = string(reg(2629), 15)
    """Sungrow Version 4 (Sungrow Battery)."""


class InverterFirmwareBlockBattery(Component):
    """1 input register, polled every 600s.

    The battery firmware string at register 13280, which some firmware
    answers by closing the connection.
    """

    register_space = "input"

    battery_firmware_version = string(reg(13280), 15)
    """Battery Firmware Version."""


class InverterFirmwareBlockCommunicationModule(Component):
    """1 input register, polled every 600s.

    The communication module's firmware string at register 13265, absent on
    a direct LAN connection and read on its own because some firmware
    answers it by closing the connection.
    """

    register_space = "input"

    communication_module_firmware_version = string(reg(13265), 15)
    """Communication Module Firmware Version."""


class InverterFirmwareBlockInverter(Component):
    """1 input register, polled every 600s.

    The inverter firmware string at register 13250, which some firmware
    answers by closing the connection.
    """

    register_space = "input"

    inverter_firmware_version = string(reg(13250), 15)
    """Inverter Firmware Version."""


class InverterSubControllerFirmware(Component):
    """1 input register, polled every 600s.

    The sub-controller firmware string, which some firmware versions do not
    publish at all.
    """

    register_space = "input"

    sungrow_version_3 = string(reg(2613), 15)
    """Sungrow Version 3."""


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
