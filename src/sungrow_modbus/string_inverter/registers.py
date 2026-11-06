"""The SG string inverters' registers: a map of their own, read only.

An SG is a PV inverter with no battery, and Sungrow documents it in a protocol
of its own, the *Communication Protocol of Residential and Commercial PV
Grid-Connected Inverters* (V1.1.53). It shares the hybrid's identity block and
its core PV block, 5000-5035, register for register; everything past that
differs. There is no 13000 block, no battery, no EMS, and the holding
registers mean other things entirely. So the map lives here rather than as a
family in `inverter/`, and the 23 registers both protocols share are declared
twice, once per protocol, rather than gated per family.

**Every address here comes from ha-modbus-manager's
`sungrow_sg_dynamic.yaml`** (MIT, TCzerny, commit `4a1e662`), which is built
from V1.1.53. Two SG5.0RS surveys (`device-survey/results/string_inverter/`)
read every block through a WiNet-S; a value there is measured only on that
model. A field's docstring says which models the source says answer it, and
the entity layer creates an entity only for a field that read a value.

**Nothing here writes.** The power limitation (holding 5007/5008) is read so an
owner can see that a curtailment is set; writing it waits for a watched write,
as 31211 did on the hybrids.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, int32, integer, uint32

from ..addresses import reg
from ..model import RegisterValue

#: Which SG a device type code names (input 5000), from the source's model
#: table. The codes interleave with nothing in the hybrid's `DEVICE_TYPES`.
MODELS: dict[int, str] = {
    0x2603: "SG3.0RS",
    0x2604: "SG3.6RS",
    0x2605: "SG4.0RS",
    0x2606: "SG5.0RS",
    0x2607: "SG6.0RS",
    0x2608: "SG8.0RS",
    0x2609: "SG10RS",
    0x243D: "SG3.0RT",
    0x243E: "SG4.0RT",
    0x2430: "SG5.0RT",
    0x2431: "SG6.0RT",
    0x243C: "SG7.0RT",
    0x2432: "SG8.0RT",
    0x2433: "SG10RT",
    0x2434: "SG12RT",
    0x2435: "SG15RT",
    0x2437: "SG20RT",
    0x0026: "SG10KTL",
    0x0029: "SG12KTL",
    0x0028: "SG15KTL",
    0x002A: "SG20KTL",
    0x0027: "SG30KTL",
    0x002D: "SG36KTL",
    0x002F: "SG40KTL",
    0x010F: "SG60KTL",
    0x0138: "SG80KTL",
    0x0141: "SG30KTL-M",
    0x0135: "SG40KTL-M",
    0x011B: "SG50KTL-M",
    0x0131: "SG60KTL-M",
    0x2C10: "SG30CX",
    0x2C00: "SG33CX",
    0x2C01: "SG40CX",
    0x2C02: "SG50CX",
    0x2C22: "SG75CX",
    0x2C12: "SG100CX",
    0x2C06: "SG110CX",
    0x2C0C: "SG250HX",
    0x2C26: "SG320HX",
    0x2C27: "SG350HX",
}

#: How many MPP trackers each model has, from the same source's model table
#: (many of its entries marked unverified against a datasheet). Measured on
#: the SG5.0RS only: two trackers answer, and MPPT3 and up read 0 where the
#: protocol promises 0xFFFF, so a value alone cannot say a tracker exists.
MPPT_COUNTS: dict[int, int] = {
    0x2603: 2,  # SG3.0RS
    0x2604: 2,  # SG3.6RS
    0x2605: 2,  # SG4.0RS
    0x2606: 2,  # SG5.0RS
    0x2607: 2,  # SG6.0RS
    0x2608: 3,  # SG8.0RS
    0x2609: 3,  # SG10RS
    0x243D: 2,  # SG3.0RT
    0x243E: 2,  # SG4.0RT
    0x2430: 2,  # SG5.0RT
    0x2431: 2,  # SG6.0RT
    0x243C: 2,  # SG7.0RT
    0x2432: 2,  # SG8.0RT
    0x2433: 2,  # SG10RT
    0x2434: 2,  # SG12RT
    0x2435: 2,  # SG15RT
    0x2437: 2,  # SG20RT
    0x0026: 2,  # SG10KTL
    0x0029: 2,  # SG12KTL
    0x0028: 2,  # SG15KTL
    0x002A: 2,  # SG20KTL
    0x0027: 2,  # SG30KTL
    0x002D: 2,  # SG36KTL
    0x002F: 2,  # SG40KTL
    0x010F: 1,  # SG60KTL
    0x0138: 1,  # SG80KTL
    0x0141: 3,  # SG30KTL-M
    0x0135: 3,  # SG40KTL-M
    0x011B: 4,  # SG50KTL-M
    0x0131: 4,  # SG60KTL-M
    0x2C10: 3,  # SG30CX
    0x2C00: 3,  # SG33CX
    0x2C01: 4,  # SG40CX
    0x2C02: 5,  # SG50CX
    0x2C22: 9,  # SG75CX
    0x2C12: 12,  # SG100CX
    0x2C06: 9,  # SG110CX
    0x2C0C: 12,  # SG250HX
    0x2C26: 12,  # SG320HX
    0x2C27: 12,  # SG350HX
}

#: What input 5038, the work state, says. Codes, not bits.
WORK_STATES: dict[int, str] = {
    0x0000: "run",
    0x8000: "stop",
    0x1300: "key stop",
    0x1500: "emergency stop",
    0x1400: "standby",
    0x1200: "initial standby",
    0x1600: "starting",
    0x9100: "alarm run",
    0x8100: "derating run",
    0x8200: "dispatch run",
    0x5500: "fault",
    0x2500: "communicate fault",
    0x1111: "uninitialized",
}

#: The work states that mean the inverter is not producing because of a fault.
FAULT_STATES = frozenset({"fault", "communicate fault"})

#: The power limitation switch, holding 5007.
SWITCH: dict[int, str] = {0xAA: "on", 0x55: "off"}


def model_for(device_type_code: int | None) -> str | None:
    """Return the SG model a type code names, or None for anything else."""
    if device_type_code is None:
        return None
    return MODELS.get(device_type_code)


def is_string_inverter(device_type_code: int | None) -> bool:
    """Whether input 5000 names an SG, so the hybrid map does not apply."""
    return model_for(device_type_code) is not None


def _meaning(table: dict[int, str], code: RegisterValue) -> str | None:
    """Return what a code means, or None -- never a made-up label."""
    if code is None:
        return None
    return table.get(int(code))


class SgRealtime(Component):
    """PV, AC and state, input 5003-5038, in one read. Realtime tier.

    The block the hybrid also has, up to 5035, then the SG's own grid
    frequency and work state.
    """

    register_space = "input"

    daily_pv_generation = gauge(reg(5003), 0.1, signed=False, unit="kWh")
    """Energy generated today."""

    total_pv_generation = uint32(reg(5004), word_order="little", unit="kWh")
    """Energy generated, lifetime, in whole kWh."""

    total_running_time = uint32(reg(5006), word_order="little", unit="h")
    """Hours run, lifetime."""

    inverter_temperature = gauge(reg(5008), 0.1, signed=True, unit="°C")
    """Internal temperature."""

    total_apparent_power = uint32(reg(5009), word_order="little", unit="VA")
    """Apparent power. The source gives it for RT, KTL and CX, not RS."""

    mppt1_voltage = gauge(reg(5011), 0.1, signed=False, nan=65535, unit="V")
    """MPPT1 voltage."""
    mppt1_current = gauge(reg(5012), 0.1, signed=False, nan=65535, unit="A")
    """MPPT1 current."""
    mppt2_voltage = gauge(reg(5013), 0.1, signed=False, nan=65535, unit="V")
    """MPPT2 voltage."""
    mppt2_current = gauge(reg(5014), 0.1, signed=False, nan=65535, unit="A")
    """MPPT2 current."""
    mppt3_voltage = gauge(reg(5015), 0.1, signed=False, nan=65535, unit="V")
    """MPPT3 voltage; only models with three trackers."""
    mppt3_current = gauge(reg(5016), 0.1, signed=False, nan=65535, unit="A")
    """MPPT3 current."""

    total_dc_power = uint32(reg(5017), word_order="little", unit="W")
    """Total DC power."""

    phase_a_voltage = gauge(reg(5019), 0.1, signed=False, nan=65535, unit="V")
    """Phase A voltage, or the single phase's."""
    phase_b_voltage = gauge(reg(5020), 0.1, signed=False, nan=65535, unit="V")
    """Phase B voltage; three-phase models."""
    phase_c_voltage = gauge(reg(5021), 0.1, signed=False, nan=65535, unit="V")
    """Phase C voltage; three-phase models."""
    phase_a_current = gauge(reg(5022), 0.1, signed=False, nan=65535, unit="A")
    """Phase A current, or the single phase's."""
    phase_b_current = gauge(reg(5023), 0.1, signed=False, nan=65535, unit="A")
    """Phase B current; three-phase models."""
    phase_c_current = gauge(reg(5024), 0.1, signed=False, nan=65535, unit="A")
    """Phase C current; three-phase models."""

    total_active_power = uint32(reg(5031), word_order="little", unit="W")
    """AC output power."""

    reactive_power = int32(reg(5033), word_order="little", unit="var")
    """Reactive power."""

    power_factor = gauge(reg(5035), 0.001, signed=True)
    """Power factor, -1 to 1."""

    grid_frequency = gauge(reg(5036), 0.1, signed=False, unit="Hz")
    """Grid frequency."""

    work_state_raw = integer(reg(5038), signed=False)
    """Work state as a code; `work_state` is what it means."""

    @property
    def work_state(self) -> str | None:
        """What the work state code means, from `WORK_STATES`."""
        return _meaning(WORK_STATES, self.work_state_raw)

    @property
    def fault_reported(self) -> bool | None:
        """Whether the work state is a fault, or None where it did not read.

        `fault` and `communicate fault` only: `alarm run` still runs. A code
        the table does not name is no evidence either way, so None.
        """
        state = self.work_state
        return None if state is None else state in FAULT_STATES


class SgMeter(Component):
    """Meter, load and grid energy, input 5083-5104. Fast tier.

    The source says V1.1.53 documents this block for the KTL series, and
    adds the RS models (and the SG10RT) undocumented. Its own component so
    a model that refuses it costs only itself.
    """

    register_space = "input"

    meter_active_power = int32(reg(5083), word_order="little", nan=2147483647, unit="W")
    """Power at the meter; positive is export, as on the hybrids' 5601."""

    meter_phase_a_power = int32(
        reg(5085), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase A power. KTL only, by the source."""
    meter_phase_b_power = int32(
        reg(5087), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase B power. KTL only, by the source."""
    meter_phase_c_power = int32(
        reg(5089), word_order="little", nan=2147483647, unit="W"
    )
    """Meter phase C power. KTL only, by the source."""

    load_power = int32(reg(5091), word_order="little", nan=2147483647, unit="W")
    """What the house draws. KTL only, by the source."""

    daily_exported_energy = uint32(
        reg(5093), scale=0.1, word_order="little", unit="kWh"
    )
    """Exported today. KTL only, by the source."""
    total_exported_energy = uint32(
        reg(5095), scale=0.1, word_order="little", unit="kWh"
    )
    """Exported, lifetime. KTL and RS, by the source."""
    daily_imported_energy = uint32(
        reg(5097), scale=0.1, word_order="little", unit="kWh"
    )
    """Imported today. KTL only, by the source."""
    total_imported_energy = uint32(
        reg(5099), scale=0.1, word_order="little", unit="kWh"
    )
    """Imported, lifetime. KTL and RS, by the source."""
    daily_direct_energy_consumption = uint32(
        reg(5101), scale=0.1, word_order="little", unit="kWh"
    )
    """PV used directly today. KTL only, by the source."""
    total_direct_energy_consumption = uint32(reg(5103), word_order="little", unit="kWh")
    """PV used directly, lifetime, in whole kWh. KTL only, by the source."""


class SgTrackers(Component):
    """Daily running time, MPPT4-12 and the month's yield, input 5113-5137.

    Medium tier. The trackers past three exist on the larger models only; the
    source says they read 0xFFFF elsewhere, and an SG5.0RS reads them as 0.
    """

    register_space = "input"

    daily_running_time = integer(reg(5113), signed=False, unit="min")
    """Minutes run today."""

    mppt4_voltage = gauge(reg(5115), 0.1, signed=False, nan=65535, unit="V")
    """MPPT4 voltage."""
    mppt4_current = gauge(reg(5116), 0.1, signed=False, nan=65535, unit="A")
    """MPPT4 current."""
    mppt5_voltage = gauge(reg(5117), 0.1, signed=False, nan=65535, unit="V")
    """MPPT5 voltage."""
    mppt5_current = gauge(reg(5118), 0.1, signed=False, nan=65535, unit="A")
    """MPPT5 current."""
    mppt6_voltage = gauge(reg(5119), 0.1, signed=False, nan=65535, unit="V")
    """MPPT6 voltage."""
    mppt6_current = gauge(reg(5120), 0.1, signed=False, nan=65535, unit="A")
    """MPPT6 current."""
    mppt7_voltage = gauge(reg(5121), 0.1, signed=False, nan=65535, unit="V")
    """MPPT7 voltage."""
    mppt7_current = gauge(reg(5122), 0.1, signed=False, nan=65535, unit="A")
    """MPPT7 current."""
    mppt8_voltage = gauge(reg(5123), 0.1, signed=False, nan=65535, unit="V")
    """MPPT8 voltage."""
    mppt8_current = gauge(reg(5124), 0.1, signed=False, nan=65535, unit="A")
    """MPPT8 current."""

    monthly_pv_generation = uint32(
        reg(5128), scale=0.1, word_order="little", unit="kWh"
    )
    """Energy generated this month."""

    mppt9_voltage = gauge(reg(5130), 0.1, signed=False, nan=65535, unit="V")
    """MPPT9 voltage."""
    mppt9_current = gauge(reg(5131), 0.1, signed=False, nan=65535, unit="A")
    """MPPT9 current."""
    mppt10_voltage = gauge(reg(5132), 0.1, signed=False, nan=65535, unit="V")
    """MPPT10 voltage."""
    mppt10_current = gauge(reg(5133), 0.1, signed=False, nan=65535, unit="A")
    """MPPT10 current."""
    mppt11_voltage = gauge(reg(5134), 0.1, signed=False, nan=65535, unit="V")
    """MPPT11 voltage."""
    mppt11_current = gauge(reg(5135), 0.1, signed=False, nan=65535, unit="A")
    """MPPT11 current."""
    mppt12_voltage = gauge(reg(5136), 0.1, signed=False, nan=65535, unit="V")
    """MPPT12 voltage."""
    mppt12_current = gauge(reg(5137), 0.1, signed=False, nan=65535, unit="A")
    """MPPT12 current."""


class SgPrecision(Component):
    """The high-resolution yield, insulation and bus, input 5144-5151. Slowest tier."""

    register_space = "input"

    total_pv_generation_precise = uint32(
        reg(5144), scale=0.1, word_order="little", unit="kWh"
    )
    """Energy generated, lifetime, in tenths of a kWh: `total_pv_generation`
    finer, which is the one to feed the Energy dashboard where it answers."""

    negative_voltage_to_ground = gauge(reg(5146), 0.1, signed=True, unit="V")
    """Negative pole to ground."""

    bus_voltage = gauge(reg(5147), 0.1, signed=False, unit="V")
    """DC bus voltage."""

    grid_frequency_precise = gauge(reg(5148), 0.01, signed=False, nan=65535, unit="Hz")
    """Grid frequency in hundredths."""


class SgPowerLimit(Component):
    """The power limitation as set, holding 5007-5008. Slowest tier, read only."""

    register_space = "holding"

    power_limitation_raw = integer(reg(5007), signed=False)
    """0xAA on, 0x55 off; `power_limitation` is what it means."""

    power_limitation_setting = gauge(reg(5008), 0.1, signed=False, unit="%")
    """The limit, as a share of rated power.

    Reset to 110 % while the switch is off, by evcc's account, so a writer
    sets the switch first (`.wiki/raw/cross-reference-evcc.md`).
    """

    @property
    def power_limitation(self) -> str | None:
        """Whether the inverter is limiting its output."""
        return _meaning(SWITCH, self.power_limitation_raw)


#: Every component, by the attribute a device holds it under.
COMPONENTS: dict[str, type[Component]] = {
    "sg_realtime": SgRealtime,
    "sg_meter": SgMeter,
    "sg_trackers": SgTrackers,
    "sg_precision": SgPrecision,
    "sg_power_limit": SgPowerLimit,
}
