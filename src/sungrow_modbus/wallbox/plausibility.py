"""The wallbox's readings checked against each other, while a car charges.

The wallbox's share of `capability_test.plausibility`, in the same words and
fed the same way: one poll's readings at a time, kept as a plain mapping, read
only. A wallbox's registers are mostly read, never written, and a reading a
decade off is as plausible as a right one until it is set beside another:

- the power 21308 against the voltage times the current of each phase;
- the session's energy against the power integrated over time, and against
  how far the lifetime counter rose;
- a counter that falls while a session runs;
- the control pilot's voltage against what the status says is plugged in;
- the inverter's load, which must move by the wallbox's power step when the
  car's draw does: the energy dashboard counts on the load including it.

Register 21313 is not a check. Nobody can name it, so what it holds is logged
beside the session's minutes, energy and setting, for a person to read.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..capability_test.plausibility import (
    MAX_GAP_S,
    MAX_RATIOS,
    Check,
    CounterCheck,
    EventCheck,
    Plausibility,
    RatioCheck,
    Values,
    _counter,
    _get,
    _power,
    judge_ratios,
)
from ..capability_test.procedure import INCONCLUSIVE, OFF_BY

#: The wallbox's own fields the checks read, as the device names them, and
#: the inverter's load, which `values` adds.
FIELDS = (
    "phase_a_voltage",
    "phase_b_voltage",
    "phase_c_voltage",
    "phase_a_current",
    "phase_b_current",
    "phase_c_current",
    "charging_power",
    "session_energy",
    "lifetime_energy",
    "control_pilot_voltage",
    "charging_status_raw",
    "unnamed_register_21313",
    "output_current_setting",
)

CHARGING = 3
#: Statuses with a car plugged in and nothing drawn, and with nothing plugged in.
CONNECTED = (2, 4, 5, 6, 7)
UNPLUGGED = (1, 8)

#: How much the wallbox's power must step for the inverter's load to be judged.
STEP_W = 1000.0

#: The most 21313 changes a log keeps.
MAX_LOG = 60


def values(
    reading: Mapping[str, float | None], load_w: float | None = None
) -> dict[str, float | None]:
    """Return the checks' fields from a wallbox's decoded readings.

    The energies are in kWh, the unit `CounterCheck` integrates a power into.
    """
    out: dict[str, float | None] = {name: reading.get(name) for name in FIELDS}
    for name in ("session_energy", "lifetime_energy"):
        wh = reading.get(name)
        out[f"{name}_kwh"] = None if wh is None else wh / 1000.0
    out["load_power"] = load_w
    return out


def _vi(values: Values) -> tuple[float, float] | None:
    """Return (power, sum of voltage times current) over the three phases."""
    power = _get(values, "charging_power")
    if power is None:
        return None
    total = 0.0
    for phase in "abc":
        voltage = _get(values, f"phase_{phase}_voltage")
        current = _get(values, f"phase_{phase}_current")
        if voltage is None or current is None:
            return None
        total += voltage * current
    return power, total


def _no_fall(
    previous: Values, current: Values, _at: datetime
) -> tuple[bool, str] | None:
    """Judge that a counter does not fall while the status stays charging."""
    if previous.get("charging_status_raw") != CHARGING:
        return None
    if _get(current, "charging_status_raw") != CHARGING:
        return None
    for name in ("session_energy", "lifetime_energy"):
        was, now = _get(previous, name), _get(current, name)
        if was is None or now is None:
            continue
        if now < was:
            return False, f"{name} fell from {was:g} to {now:g} Wh in a session"
    return True, ""


def _pilot(previous: Values, current: Values, _at: datetime) -> tuple[bool, str] | None:
    """Judge the pilot against the status: 6 V charging, 9 V connected, 12 V free."""
    status = _get(current, "charging_status_raw")
    pilot = _get(current, "control_pilot_voltage")
    if status is None or pilot is None:
        return None
    status_int = int(status)
    if status_int == CHARGING:
        low, high = 4.5, 7.5
    elif status_int in CONNECTED:
        low, high = 7.5, 10.5
    elif status_int in UNPLUGGED:
        # 12 V unplugged; a car connected and idle reads 9 V, which the
        # status does not always tell from "idle", so both are accepted.
        low, high = 7.5, 13.5
    else:
        return None
    if low <= pilot <= high:
        return True, ""
    return False, f"status {status_int} with the pilot at {pilot:g} V"


@dataclass
class LoadFollows(Check):
    """The inverter's load moves by the wallbox's power step, within a tenth."""

    ratios: list[float] = field(default_factory=list)
    tolerance: float = 0.1
    _previous: tuple[float, float, float] | None = None

    def observe(self, values: Values, at: datetime) -> None:
        """Keep the load's step over the power's, when the power steps."""
        power, load = _get(values, "charging_power"), _get(values, "load_power")
        now = at.timestamp()
        previous, self._previous = (
            self._previous,
            ((power, load, now) if power is not None and load is not None else None),
        )
        if previous is None or power is None or load is None:
            return
        was_power, was_load, was_at = previous
        if now - was_at > MAX_GAP_S or abs(power - was_power) < STEP_W:
            return
        self.ratios.append((load - was_load) / (power - was_power))
        del self.ratios[:-MAX_RATIOS]

    def verdict(self) -> tuple[str | None, str]:
        """Judge the median once there are enough steps."""
        if len(self.ratios) < self.minimum:
            return None, f"{len(self.ratios)} of {self.minimum} power steps"
        verdict, middle, factor = judge_ratios(
            self.ratios, tolerance=self.tolerance, signed=True
        )
        detail = f"median ratio {middle:.3f} over {len(self.ratios)} steps"
        if factor is not None:
            detail += f", a factor of {factor:g}"
        return verdict, detail

    def state(self) -> dict[str, Any]:
        """Return the ratios kept."""
        return {"ratios": [round(r, 5) for r in self.ratios]}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept ratios back."""
        self.ratios = [float(r) for r in state.get("ratios") or []][-MAX_RATIOS:]


def checks() -> list[Check]:
    """Return a fresh set of the wallbox's checks."""
    return [
        RatioCheck(
            name="wallbox power times voltage and current",
            needs="a car drawing 500 W",
            minimum=20,
            fields=("charging_power", "phase_a_voltage", "phase_a_current"),
            compute=_vi,
            floor=500.0,
            tolerance=0.05,
        ),
        CounterCheck(
            name="wallbox session energy against power",
            needs="a session that delivers 0.5 kWh",
            minimum=3,
            fields=("session_energy_kwh", "charging_power"),
            counter="session_energy_kwh",
            rate=_power("charging_power"),
            step=0.5,
            tolerance=0.1,
        ),
        CounterCheck(
            name="wallbox lifetime energy against session",
            needs="a session that delivers 0.5 kWh",
            minimum=3,
            fields=("session_energy_kwh", "lifetime_energy_kwh"),
            counter="session_energy_kwh",
            rate=_counter("lifetime_energy_kwh"),
            integrate=False,
            step=0.5,
            tolerance=0.1,
        ),
        EventCheck(
            name="wallbox energy counters never fall",
            needs="a charging session",
            minimum=20,
            fields=("session_energy", "lifetime_energy", "charging_status_raw"),
            judge=_no_fall,
            failure=OFF_BY,
        ),
        EventCheck(
            name="wallbox control pilot against status",
            needs="a car plugged in, and one charging",
            minimum=20,
            fields=("control_pilot_voltage", "charging_status_raw"),
            judge=_pilot,
            failure=INCONCLUSIVE,
        ),
        LoadFollows(
            name="inverter load includes the wallbox",
            needs="the wallbox's power stepping by 1 kW",
            minimum=3,
            fields=("charging_power", "load_power"),
        ),
    ]


class WallboxPlausibility(Plausibility):
    """The wallbox's checks, and a log of what register 21313 holds."""

    def __init__(self) -> None:
        """Start with nothing seen."""
        super().__init__()
        self.checks = checks()
        #: Changes of 21313: status, value, minutes into the session, Wh, A.
        self.log: list[dict[str, Any]] = []
        self._last_21313: float | None = None
        self._session_start: float | None = None

    def observe(self, values: Values, at: datetime) -> None:
        """Feed the checks and the 21313 log."""
        super().observe(values, at)
        now = at.timestamp()
        status = _get(values, "charging_status_raw")
        if status == CHARGING and self._session_start is None:
            self._session_start = now
        elif status != CHARGING:
            self._session_start = None
        word = _get(values, "unnamed_register_21313")
        if word is None or word == self._last_21313:
            return
        self._last_21313 = word
        minutes = (
            None
            if self._session_start is None
            else round((now - self._session_start) / 60, 1)
        )
        self.log.append(
            {
                "at": at.isoformat(),
                "value": word,
                "status": status,
                "session_minutes": minutes,
                "session_wh": _get(values, "session_energy"),
                "setting_a": _get(values, "output_current_setting"),
            }
        )
        del self.log[:-MAX_LOG]

    def document(self) -> dict[str, Any]:
        """Return the publishable block, the 21313 log included."""
        out = super().document()
        out["register_21313"] = list(self.log)
        return out

    def as_dict(self) -> dict[str, Any]:
        """Return everything to keep across a restart."""
        out = super().as_dict()
        out["log"] = list(self.log)
        return out

    @classmethod
    def from_dict(cls, state: Mapping[str, Any] | None) -> WallboxPlausibility:
        """Return a collection from `as_dict`, or a fresh one if it does not fit."""
        out = cls()
        if not state or state.get("schema") != 1:
            return out
        base = Plausibility.from_dict(state)
        out.observations, out.first, out.last = base.observations, base.first, base.last
        out._present = base._present
        kept = state.get("checks") or {}
        for check in out.checks:
            if check.name in kept:
                check.load(kept[check.name])
        out.log = [dict(row) for row in state.get("log") or []][-MAX_LOG:]
        return out
