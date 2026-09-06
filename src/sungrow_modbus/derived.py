"""Values the YAML package computed with templates, computed here instead.

The YAML has no arithmetic of its own, so anything beyond a raw register — a
power that is voltage times current, a battery flow split into charge and
discharge, a running state decoded to text — is a `template:` sensor built on
top of the modbus ones. Those entities are user-facing and their ids have to
be reproduced, but the arithmetic belongs here rather than in Home Assistant:
it is testable without a running instance, and it is the same in every
language.

Every value returns ``None`` when an input it needs is missing, so a
derived entity goes unavailable exactly when its source does — which on an
SH10RT is what MPPT3 and MPPT4 do, permanently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import model_for

if TYPE_CHECKING:
    from .device import SungrowInverter

#: Register 13000's value to the state the YAML package showed for it. Some
#: codes repeat a label — 0x0000 and 0x0040 are both simply running — which is
#: the inverter's doing, not a mistake here.
RUNNING_STATES: dict[int, str] = {
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

#: Bits of the power flow status register, which the YAML tested one at a time
#: to produce seven binary sensors.
POWER_FLOW_BITS: dict[str, int] = {
    "pv_generating": 0x01,
    "battery_charging": 0x02,
    "battery_discharging": 0x04,
    "positive_load_power": 0x08,
    "exporting_power": 0x10,
    "importing_power": 0x20,
    "negative_load_power": 0x80,
}


class Derived:
    """Computed values, read like any other component's fields."""

    def __init__(self, inverter: SungrowInverter) -> None:
        """Bind to the inverter whose registers these are computed from."""
        self._inverter = inverter

    # -- plumbing ---------------------------------------------------------

    def _value(self, field: str) -> float | int | str | None:
        """Return one register's decoded value, wherever it lives."""
        return self._inverter.field(field)

    def _product(self, left: str, right: str) -> int | None:
        """Return the product of two readings, or None if either is missing."""
        a, b = self._value(left), self._value(right)
        if a is None or b is None:
            return None
        return int(float(a) * float(b))

    def _bit(self, name: str) -> bool | None:
        """Return one bit of the power flow status register."""
        raw = self._value("power_flow_status")
        if raw is None:
            return None
        return bool(int(raw) & POWER_FLOW_BITS[name])

    def _floats(self, *fields: str) -> tuple[float, ...] | None:
        """Return several readings as floats, or None if any is missing."""
        values = [self._value(f) for f in fields]
        if any(v is None for v in values):
            return None
        return tuple(float(v) for v in values)  # type: ignore[arg-type]

    # -- MPPT and phase power ---------------------------------------------

    @property
    def mppt1_power(self) -> int | None:
        """MPPT1 voltage times its current."""
        return self._product("mppt1_voltage", "mppt1_current")

    @property
    def mppt2_power(self) -> int | None:
        """MPPT2 voltage times its current."""
        return self._product("mppt2_voltage", "mppt2_current")

    @property
    def mppt3_power(self) -> int | None:
        """MPPT3 voltage times its current, absent on a two-tracker inverter."""
        return self._product("mppt3_voltage", "mppt3_current")

    @property
    def mppt4_power(self) -> int | None:
        """MPPT4 voltage times its current, absent on most models."""
        return self._product("mppt4_voltage", "mppt4_current")

    @property
    def phase_a_power(self) -> int | None:
        """Phase A voltage times its current."""
        return self._product("phase_a_voltage", "phase_a_current")

    @property
    def phase_b_power(self) -> int | None:
        """Phase B voltage times its current, absent on a single-phase unit."""
        return self._product("phase_b_voltage", "phase_b_current")

    @property
    def phase_c_power(self) -> int | None:
        """Phase C voltage times its current, absent on a single-phase unit."""
        return self._product("phase_c_voltage", "phase_c_current")

    # -- power flow flags -------------------------------------------------

    @property
    def pv_generating(self) -> bool | None:
        """Bit 0x01 of the power flow status register."""
        return self._bit("pv_generating")

    @property
    def battery_charging(self) -> bool | None:
        """Bit 0x02 of the power flow status register."""
        return self._bit("battery_charging")

    @property
    def battery_discharging(self) -> bool | None:
        """Bit 0x04 of the power flow status register."""
        return self._bit("battery_discharging")

    @property
    def positive_load_power(self) -> bool | None:
        """Bit 0x08 of the power flow status register."""
        return self._bit("positive_load_power")

    @property
    def exporting_power(self) -> bool | None:
        """Bit 0x10 of the power flow status register."""
        return self._bit("exporting_power")

    @property
    def importing_power(self) -> bool | None:
        """Bit 0x20 of the power flow status register."""
        return self._bit("importing_power")

    @property
    def negative_load_power(self) -> bool | None:
        """Bit 0x80 of the power flow status register."""
        return self._bit("negative_load_power")

    # -- decoded state ----------------------------------------------------

    @property
    def inverter_state(self) -> str | None:
        """The running state as text, or the raw code if it is unrecognised.

        An unknown code is reported rather than hidden: it is the only way a
        state Sungrow has added since this table was written gets noticed.
        """
        raw = self._value("running_state_raw")
        if raw is None:
            return None
        return RUNNING_STATES.get(int(raw), f"Unknown (0x{int(raw):04X})")

    @property
    def sungrow_device_type(self) -> str | None:
        """The model name for the device type code, as the YAML showed it."""
        raw = self._value("sungrow_device_type_code")
        return None if raw is None else model_for(int(raw))

    # -- battery and grid flow --------------------------------------------

    @property
    def battery_charging_power_signed(self) -> int | None:
        """Battery power, positive when charging."""
        raw = self._value("battery_power")
        return None if raw is None else -int(raw)

    @property
    def battery_discharging_power_signed(self) -> int | None:
        """Battery power, positive when discharging."""
        raw = self._value("battery_power")
        return None if raw is None else int(raw)

    @property
    def battery_charging_power(self) -> int | None:
        """Charging power, or zero when discharging."""
        signed = self.battery_charging_power_signed
        return None if signed is None else max(signed, 0)

    @property
    def battery_discharging_power(self) -> int | None:
        """Discharging power, or zero when charging."""
        signed = self.battery_discharging_power_signed
        return None if signed is None else max(signed, 0)

    @property
    def export_power(self) -> int | None:
        """Power leaving the house, or zero while importing."""
        raw = self._value("export_power_raw")
        return None if raw is None else max(int(raw), 0)

    @property
    def import_power(self) -> int | None:
        """Power entering the house, or zero while exporting."""
        raw = self._value("export_power_raw")
        return None if raw is None else max(-int(raw), 0)

    # -- battery capacity -------------------------------------------------

    @property
    def battery_level_nominal(self) -> float | None:
        """The reported level mapped onto the usable range between the SoC limits.

        A battery held between 10% and 90% reports 100% when it is full *of
        its usable range*; this says what fraction of the whole pack that is.
        """
        values = self._floats("battery_min_soc", "battery_max_soc", "battery_level")
        if values is None:
            return None
        soc_min, soc_max, soc_now = values
        return round(soc_min + (soc_max - soc_min) * (soc_now / 100), 1)

    @property
    def battery_charge_nominal(self) -> float | None:
        """Energy in the pack, against its nominal capacity."""
        level = self.battery_level_nominal
        capacity = self._value("battery_capacity_high_precision")
        if level is None or capacity is None:
            return None
        return round(float(capacity) * level / 100, 1)

    @property
    def battery_charge(self) -> float | None:
        """Energy the usable range between the SoC limits can hold."""
        values = self._floats(
            "battery_capacity_high_precision", "battery_max_soc", "battery_min_soc"
        )
        if values is None:
            return None
        capacity, soc_max, soc_min = values
        return round(capacity * (soc_max - soc_min) / 100, 1)

    @property
    def battery_charge_health_rated(self) -> float | None:
        """Usable energy, discounted by the pack's state of health."""
        charge = self.battery_charge
        health = self._value("battery_state_of_health")
        if charge is None or health is None:
            return None
        return round(charge * float(health) / 100, 2)

    # -- consumption ------------------------------------------------------

    @property
    def daily_consumed_energy(self) -> float | None:
        """What the house used today, from what it made, stored and traded."""
        return self._consumed("daily")

    @property
    def total_consumed_energy(self) -> float | None:
        """What the house has used in total."""
        return self._consumed("total")

    def _consumed(self, period: str) -> float | None:
        """Return generation, less what left, plus what arrived, less storage."""
        values = self._floats(
            f"{period}_pv_generation",
            f"{period}_exported_energy",
            f"{period}_imported_energy",
            f"{period}_battery_charge",
            f"{period}_battery_discharge",
        )
        if values is None:
            return None
        generated, exported, imported, stored, released = values
        return generated - exported + imported - stored + released
