"""Readings checked against each other and against physics, over days.

The capability test's leg B catches a wrong scale on a register the run
writes. Most registers are only read, and a sensor whose scale is a decade off
reads a plausible number every time: 4.2 kWh instead of 42, 23 V instead of
230. Nothing in a single reading can tell. Two readings that must agree can:
a power that is its voltage times its current, a daily counter that rises by
what its power integrated to, a meter whose phases add up to its total.

This module holds those relations. It is fed one poll's readings at a time
(`Plausibility.observe`), keeps what each check saw, and says per check what
the collection has established so far, in the capability test's own verdict
words, so the ledger's counters and summary count it with the writes:

- `MATCH` once enough observations agree;
- `SCALED` when their median is a clean decade off, `SIGN_INVERTED` when it is
  minus one: the findings this exists for;
- `INCONCLUSIVE` when the median is neither. Losses, reactive power and
  polling skew move these ratios by percents, so a ratio that is merely off
  is a question for a person, never a failure;
- `NO_EFFECT` for a tracker that reads 0 V in full daylight.

Each check names what it needs (`Check.needs`) and counts only the moments
that meet it, so a collection over days answers what one reading cannot: the
battery check needs a battery moving, the energy checks a kilowatt-hour of
flow, the reset check a midnight.

Read only. Nothing here talks to a device, to Home Assistant or to a file;
the state is a plain mapping (`as_dict`, `from_dict`) for a driver to keep.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..hybrid_inverter.derived import RUNNING_STATES
from .procedure import (
    DECADES,
    INCONCLUSIVE,
    MATCH,
    NO_EFFECT,
    OFF_BY,
    SCALED,
    SIGN_INVERTED,
    median,
)

#: Bumped when the shape of `as_dict` changes. A stored state of another
#: schema is dropped, and the collection starts again.
SCHEMA = 1

#: How a plausibility row is marked in a folded ledger's summary.
KIND = "plausibility"

Values = Mapping[str, float | None]

#: A gap between two observations longer than this breaks every integral: a
#: capability test paused polling, or Home Assistant was down, and what flowed
#: in between is not known.
MAX_GAP_S = 300.0

#: The most ratios a check keeps. The median of the last few hundred is as
#: good as the median of all, and a state kept for weeks stays small.
MAX_RATIOS = 240

#: A tracker counts as producing when its voltage is above this.
TRACKER_LIVE_V = 50.0

#: Daylight, for the tracker check: total DC power at least this.
DAYLIGHT_W = 1000.0


def _get(values: Values, name: str) -> float | None:
    value = values.get(name)
    return None if value is None else float(value)


def _all(values: Values, *names: str) -> tuple[float, ...] | None:
    found = tuple(_get(values, name) for name in names)
    if any(value is None for value in found):
        return None
    return tuple(value for value in found if value is not None)


def judge_ratios(
    ratios: Iterable[float], *, tolerance: float, signed: bool
) -> tuple[str, float, float | None]:
    """Return (verdict, median, factor) for a check's ratios.

    `factor` is the decade a `SCALED` verdict found, else None. `signed`
    checks may report a sign inversion; the others compare magnitudes.
    """
    middle = median(list(ratios))
    if abs(middle - 1.0) <= tolerance:
        return MATCH, middle, None
    if signed and abs(middle + 1.0) <= tolerance:
        return SIGN_INVERTED, middle, None
    for decade in DECADES:
        if abs(abs(middle) / decade - 1.0) <= tolerance:
            return SCALED, middle, decade
    return INCONCLUSIVE, middle, None


@dataclass
class Check:
    """One relation, and what the collection has seen of it."""

    name: str
    needs: str
    """What the house must be doing for an observation to count."""
    minimum: int
    """Observations before a verdict is given."""
    fields: tuple[str, ...]
    """The fields it reads; a device without one of them does not run it."""

    def observe(self, values: Values, at: datetime) -> None:
        """Take one poll's readings."""
        raise NotImplementedError

    def verdict(self) -> tuple[str | None, str]:
        """Return (verdict, detail); None until `minimum` is reached."""
        raise NotImplementedError

    def state(self) -> dict[str, Any]:
        """Return what has to be kept across a restart."""
        raise NotImplementedError

    def load(self, state: Mapping[str, Any]) -> None:
        """Take a kept state back."""
        raise NotImplementedError


@dataclass
class RatioCheck(Check):
    """Two expressions of one quantity, compared at every poll.

    `compute` returns (left, right), or None when an input is missing; the
    ratio left/right is kept when |right| is at least `floor`, where noise
    no longer dominates it.
    """

    compute: Callable[[Values], tuple[float, float] | None] = lambda _v: None
    floor: float = 300.0
    tolerance: float = 0.15
    signed: bool = False
    ratios: list[float] = field(default_factory=list)

    def observe(self, values: Values, at: datetime) -> None:
        """Keep left/right when right stands clear of the floor."""
        pair = self.compute(values)
        if pair is None:
            return
        left, right = pair
        if abs(right) < self.floor:
            return
        ratio = left / right
        self.ratios.append(ratio if self.signed else abs(ratio))
        del self.ratios[:-MAX_RATIOS]

    def verdict(self) -> tuple[str | None, str]:
        """Judge the median ratio once there are enough."""
        if len(self.ratios) < self.minimum:
            return None, f"{len(self.ratios)} of {self.minimum} observations"
        verdict, middle, factor = judge_ratios(
            self.ratios, tolerance=self.tolerance, signed=self.signed
        )
        detail = f"median ratio {middle:.3f} over {len(self.ratios)} observations"
        if factor is not None:
            detail += f", a factor of {factor:g}"
        return verdict, detail

    def state(self) -> dict[str, Any]:
        """Return the ratios kept."""
        return {"ratios": [round(r, 5) for r in self.ratios]}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept ratios back."""
        self.ratios = [float(r) for r in state.get("ratios") or []][-MAX_RATIOS:]


@dataclass
class CounterCheck(Check):
    """An energy counter against what should have filled it.

    `counter` is a counter field in kWh at 0.1 kWh resolution. Its rise is
    compared with `rate`: a power in W integrated over time
    (`integrate=True`), or another counter's rise (`integrate=False`). The
    trail starts at a step of the counter, so its quantisation costs nothing
    at the start, and closes once it has risen `step` kWh; the ratio of the
    other side to the counter's rise is kept. A gap, a missing value or a
    counter that falls (the midnight reset) starts the trail again.
    """

    counter: str = ""
    rate: Callable[[Values], float | None] = lambda _v: None
    integrate: bool = True
    step: float = 1.0
    tolerance: float = 0.2
    ratios: list[float] = field(default_factory=list)
    _previous: float | None = None
    _base: float | None = None
    _other: float = 0.0
    _last_at: float | None = None
    _last_rate: float | None = None

    def _restart(self) -> None:
        self._base = None
        self._other = 0.0

    def observe(self, values: Values, at: datetime) -> None:
        """Advance the trail by one poll."""
        now = at.timestamp()
        count = _get(values, self.counter)
        rate = self.rate(values)
        gap = self._last_at is None or now - self._last_at > MAX_GAP_S
        previous, self._previous = self._previous, count
        last_at, self._last_at = self._last_at, now
        last_rate, self._last_rate = self._last_rate, rate
        if count is None or rate is None or gap or previous is None:
            self._restart()
            return
        if count < previous:
            self._restart()
            return
        if self._base is None:
            if count > previous:
                # The counter just stepped: a trail starting here owes
                # nothing to its resolution.
                self._base = count
                self._other = rate if not self.integrate else 0.0
            return
        if self.integrate:
            assert last_at is not None and last_rate is not None
            hours = (now - last_at) / 3600.0
            self._other += (max(rate, 0.0) + max(last_rate, 0.0)) / 2 * hours / 1000.0
        risen = count - self._base
        if risen < self.step:
            return
        other = self._other if self.integrate else rate - self._other
        if other > 0:
            self.ratios.append(other / risen)
            del self.ratios[:-MAX_RATIOS]
        self._base = count
        self._other = 0.0 if self.integrate else rate

    def verdict(self) -> tuple[str | None, str]:
        """Judge the median of the closed trails."""
        if len(self.ratios) < self.minimum:
            return (
                None,
                f"{len(self.ratios)} of {self.minimum} trails of {self.step:g} kWh",
            )
        verdict, middle, factor = judge_ratios(
            self.ratios, tolerance=self.tolerance, signed=False
        )
        detail = f"median ratio {middle:.3f} over {len(self.ratios)} trails"
        if factor is not None:
            detail += f", a factor of {factor:g}"
        return verdict, detail

    def state(self) -> dict[str, Any]:
        """Return the closed trails; an open trail is not worth keeping."""
        return {"ratios": [round(r, 5) for r in self.ratios]}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept trails back."""
        self.ratios = [float(r) for r in state.get("ratios") or []][-MAX_RATIOS:]


@dataclass
class EventCheck(Check):
    """Something that must or must not happen, counted as it does.

    `judge` sees the previous and the current readings and returns True (a
    pass), False (a failure, with a sentence) or None (nothing to judge).
    One failure decides the verdict: these are rules, not ratios.
    """

    judge: Callable[[Values, Values, datetime], tuple[bool, str] | None] = (
        lambda _p, _c, _a: None
    )
    failure: str = OFF_BY
    passes: int = 0
    failures: list[str] = field(default_factory=list)
    _previous: dict[str, float | None] | None = None
    _last_at: float | None = None

    def observe(self, values: Values, at: datetime) -> None:
        """Judge the step from the previous poll to this one."""
        now = at.timestamp()
        previous = self._previous
        gap = self._last_at is None or now - self._last_at > MAX_GAP_S
        self._previous = {name: _get(values, name) for name in self.fields}
        self._last_at = now
        if previous is None or gap:
            return
        judged = self.judge(previous, values, at)
        if judged is None:
            return
        ok, sentence = judged
        if ok:
            self.passes += 1
        elif sentence not in self.failures:
            self.failures.append(sentence)
            del self.failures[:-5]

    def verdict(self) -> tuple[str | None, str]:
        """Return a failure, or a pass once enough events agree."""
        if self.failures:
            return self.failure, "; ".join(self.failures)
        if self.passes < self.minimum:
            return None, f"{self.passes} of {self.minimum} events"
        return MATCH, f"{self.passes} events, none against"

    def state(self) -> dict[str, Any]:
        """Return the counts and the failures."""
        return {"passes": self.passes, "failures": list(self.failures)}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept counts back."""
        self.passes = int(state.get("passes") or 0)
        self.failures = [str(f) for f in state.get("failures") or []]


@dataclass
class RunningStates(Check):
    """Every running-state code seen, and how often; an unknown one is a finding."""

    seen: dict[str, int] = field(default_factory=dict)

    def observe(self, values: Values, at: datetime) -> None:
        """Count this poll's code."""
        word = _get(values, "running_state_raw")
        if word is None:
            return
        key = f"0x{int(word):04X}"
        self.seen[key] = self.seen.get(key, 0) + 1

    def verdict(self) -> tuple[str | None, str]:
        """Unknown codes are named; known ones listed with their counts."""
        unknown = [code for code in self.seen if int(code, 16) not in RUNNING_STATES]
        listing = ", ".join(
            f"{code} {RUNNING_STATES.get(int(code, 16), 'unknown')}: {count}"
            for code, count in sorted(self.seen.items())
        )
        if unknown:
            return OFF_BY, f"codes not in the table: {', '.join(unknown)} ({listing})"
        if sum(self.seen.values()) < self.minimum:
            return None, listing or "nothing seen yet"
        return MATCH, listing

    def state(self) -> dict[str, Any]:
        """Return the codes and their counts."""
        return {"seen": dict(self.seen)}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept counts back."""
        self.seen = {str(k): int(v) for k, v in (state.get("seen") or {}).items()}


@dataclass
class TrackerCheck(Check):
    """Whether a third or fourth tracker carries a string, seen in daylight.

    The capability grants the tracker on a voltage that is not `0xFFFF`, and
    a tracker with nothing on it reads 0 at night like a real one does. In
    full daylight a real one does not.
    """

    tracker: str = ""
    live: int = 0
    dark: int = 0

    def observe(self, values: Values, at: datetime) -> None:
        """Count daylight polls with and without a voltage."""
        voltage = _get(values, f"{self.tracker}_voltage")
        dc = _get(values, "total_dc_power")
        if voltage is None or dc is None or dc < DAYLIGHT_W:
            return
        if voltage >= TRACKER_LIVE_V:
            self.live += 1
        else:
            self.dark += 1

    def verdict(self) -> tuple[str | None, str]:
        """Present once it has carried power; absent after a daylight of 0 V."""
        if self.live:
            return MATCH, f"{self.live} daylight polls with a voltage"
        if self.dark < self.minimum:
            return None, f"{self.dark} of {self.minimum} daylight polls"
        return NO_EFFECT, f"0 V in {self.dark} daylight polls: no string on it"

    def state(self) -> dict[str, Any]:
        """Return the two counts."""
        return {"live": self.live, "dark": self.dark}

    def load(self, state: Mapping[str, Any]) -> None:
        """Take kept counts back."""
        self.live = int(state.get("live") or 0)
        self.dark = int(state.get("dark") or 0)


# -- the relations -------------------------------------------------------------


def _balance(values: Values) -> tuple[float, float] | None:
    """Load against what feeds it: PV, plus the battery, less the export."""
    found = _all(
        values, "load_power", "total_dc_power", "battery_power", "export_power_raw"
    )
    if found is None:
        return None
    load, pv, battery, export = found
    return load, pv + battery - export


def _battery_vi(values: Values) -> tuple[float, float] | None:
    found = _all(values, "battery_voltage", "battery_current", "battery_power")
    if found is None:
        return None
    volts, amps, power = found
    return volts * amps, power


def _mppt_vi(values: Values) -> tuple[float, float] | None:
    total = _get(values, "total_dc_power")
    if total is None:
        return None
    product = 0.0
    for number in (1, 2, 3, 4):
        pair = _all(values, f"mppt{number}_voltage", f"mppt{number}_current")
        if pair is not None:
            product += pair[0] * pair[1]
        elif number <= 2:
            return None
    return product, total


def _ac_vi(values: Values) -> tuple[float, float] | None:
    total = _get(values, "total_active_power")
    if total is None:
        return None
    product = 0.0
    phases = 0
    for phase in ("a", "b", "c"):
        pair = _all(values, f"phase_{phase}_voltage", f"phase_{phase}_current")
        if pair is not None:
            product += pair[0] * abs(pair[1])
            phases += 1
    if not phases:
        return None
    return product, total


def _meter_phases(values: Values) -> tuple[float, float] | None:
    found = _all(
        values,
        "meter_phase_a_active_power",
        "meter_phase_b_active_power",
        "meter_phase_c_active_power",
        "meter_active_power",
    )
    if found is None:
        return None
    a, b, c, total = found
    return a + b + c, total


def _meter_export(values: Values) -> tuple[float, float] | None:
    found = _all(values, "meter_active_power", "export_power_raw")
    if found is None:
        return None
    return found[0], found[1]


def _power(name: str, sign: float = 1.0) -> Callable[[Values], float | None]:
    def rate(values: Values) -> float | None:
        value = _get(values, name)
        return None if value is None else max(sign * value, 0.0)

    return rate


def _counter(name: str) -> Callable[[Values], float | None]:
    def rate(values: Values) -> float | None:
        return _get(values, name)

    return rate


#: (daily counter, total counter): the same energy at two resolutions.
COUNTER_PAIRS: tuple[tuple[str, str], ...] = (
    ("daily_pv_generation", "total_pv_generation"),
    ("daily_imported_energy", "total_imported_energy"),
    ("daily_exported_energy", "total_exported_energy"),
    ("daily_battery_charge", "total_battery_charge"),
    ("daily_battery_discharge", "total_battery_discharge"),
    ("daily_exported_energy_from_pv", "total_exported_energy_from_pv"),
    ("daily_battery_charge_from_pv", "total_battery_charge_from_pv"),
    ("daily_direct_energy_consumption", "total_direct_energy_consumption"),
)

#: (daily counter, power field, sign that makes the power positive into it).
COUNTER_POWERS: tuple[tuple[str, str, float], ...] = (
    ("daily_pv_generation", "total_dc_power", 1.0),
    ("daily_imported_energy", "export_power_raw", -1.0),
    ("daily_exported_energy", "export_power_raw", 1.0),
    ("daily_battery_charge", "battery_power", -1.0),
    ("daily_battery_discharge", "battery_power", 1.0),
)

DAILY = tuple(daily for daily, _total in COUNTER_PAIRS)
TOTALS = tuple(total for _daily, total in COUNTER_PAIRS)


def _totals_rise(
    previous: Values, current: Values, _at: datetime
) -> tuple[bool, str] | None:
    """Judge that no lifetime counter fell."""
    judged = False
    for name in TOTALS:
        before, now = _get(previous, name), _get(current, name)
        if before is None or now is None:
            continue
        judged = True
        if now < before:
            return False, f"{name} fell from {before:g} to {now:g}"
    return (True, "") if judged else None


def _near_midnight(at: datetime) -> bool:
    minutes = at.hour * 60 + at.minute
    return minutes >= 23 * 60 + 30 or minutes <= 30


def _daily_resets(
    previous: Values, current: Values, at: datetime
) -> tuple[bool, str] | None:
    """Judge that a daily counter falls only at midnight, to almost nothing."""
    verdict: tuple[bool, str] | None = None
    for name in DAILY:
        before, now = _get(previous, name), _get(current, name)
        if before is None or now is None or now >= before:
            continue
        if not _near_midnight(at):
            return False, f"{name} fell from {before:g} to {now:g} at {at:%H:%M}"
        if now > 0.5:
            return False, f"{name} reset to {now:g}, not to zero, at {at:%H:%M}"
        verdict = (True, "")
    return verdict


@dataclass
class SocDirection(EventCheck):
    """The state of charge moves the way the battery's power says.

    The battery's energy is integrated from its power (positive while
    discharging). Once a kilowatt-hour has moved one way and the level has
    moved a whole percent, the level must have gone the other way.
    """

    _energy: float = 0.0
    _soc: float | None = None
    _at: float | None = None
    _power: float | None = None

    def observe(self, values: Values, at: datetime) -> None:
        """Integrate, and judge when enough has moved."""
        now = at.timestamp()
        soc = _get(values, "battery_level")
        power = _get(values, "battery_power")
        if (
            soc is None
            or power is None
            or self._at is None
            or self._power is None
            or self._soc is None
            or now - self._at > MAX_GAP_S
        ):
            self._energy, self._soc, self._at, self._power = 0.0, soc, now, power
            return
        self._energy += (power + self._power) / 2 * (now - self._at) / 3600.0 / 1000.0
        self._at, self._power = now, power
        moved = soc - self._soc
        if abs(self._energy) < 1.0 or abs(moved) < 1.0:
            return
        if (self._energy > 0) == (moved < 0):
            self.passes += 1
        else:
            sentence = (
                f"{abs(self._energy):.1f} kWh "
                f"{'out of' if self._energy > 0 else 'into'} the battery, "
                f"and the level went from {self._soc:g} to {soc:g} %"
            )
            if sentence not in self.failures:
                self.failures.append(sentence)
                del self.failures[:-5]
        self._energy, self._soc = 0.0, soc


def checks() -> list[Check]:
    """Return a fresh set of every check, in the order a person reads them."""
    out: list[Check] = [
        RatioCheck(
            name="power balance",
            needs="a house load of 500 W",
            minimum=30,
            fields=(
                "load_power",
                "total_dc_power",
                "battery_power",
                "export_power_raw",
            ),
            compute=_balance,
            floor=500.0,
            tolerance=0.2,
            signed=True,
        ),
        RatioCheck(
            name="battery voltage times current",
            needs="the battery moving 300 W",
            minimum=20,
            fields=("battery_voltage", "battery_current", "battery_power"),
            compute=_battery_vi,
        ),
        RatioCheck(
            name="tracker voltage times current",
            needs="PV above 300 W",
            minimum=20,
            fields=("mppt1_voltage", "mppt1_current", "total_dc_power"),
            compute=_mppt_vi,
            tolerance=0.1,
        ),
        RatioCheck(
            name="phase voltage times current",
            needs="the inverter delivering 1000 W",
            minimum=20,
            fields=("phase_a_voltage", "phase_a_current", "total_active_power"),
            compute=_ac_vi,
            floor=1000.0,
            tolerance=0.25,
        ),
        RatioCheck(
            name="meter phases add up",
            needs="300 W through the meter",
            minimum=20,
            fields=("meter_phase_a_active_power", "meter_active_power"),
            compute=_meter_phases,
            tolerance=0.1,
            signed=True,
        ),
        RatioCheck(
            name="meter against export power",
            needs="300 W through the meter",
            minimum=20,
            fields=("meter_active_power", "export_power_raw"),
            compute=_meter_export,
            tolerance=0.1,
        ),
    ]
    for daily, power, sign in COUNTER_POWERS:
        out.append(
            CounterCheck(
                name=f"{daily} against power",
                needs="three kilowatt-hours of flow",
                minimum=3,
                fields=(daily, power),
                counter=daily,
                rate=_power(power, sign),
            )
        )
    for daily, total in COUNTER_PAIRS:
        out.append(
            CounterCheck(
                name=f"{total} against {daily}",
                needs="2 kWh on the daily counter",
                minimum=2,
                fields=(daily, total),
                counter=daily,
                rate=_counter(total),
                integrate=False,
                step=2.0,
                tolerance=0.15,
            )
        )
    out += [
        EventCheck(
            name="lifetime counters never fall",
            needs="a day of polls",
            minimum=1440,
            fields=TOTALS,
            judge=_totals_rise,
        ),
        EventCheck(
            name="daily counters reset at midnight",
            needs="a midnight",
            minimum=1,
            fields=DAILY,
            judge=_daily_resets,
        ),
        SocDirection(
            name="battery level follows its power",
            needs="1 kWh into or out of the battery",
            minimum=2,
            fields=("battery_level", "battery_power"),
        ),
        RunningStates(
            name="running states",
            needs="a day of polls",
            minimum=1440,
            fields=("running_state_raw",),
        ),
    ]
    for tracker in ("mppt3", "mppt4"):
        out.append(
            TrackerCheck(
                name=f"{tracker} carries a string",
                needs="PV above 1000 W",
                minimum=30,
                fields=(f"{tracker}_voltage", "total_dc_power"),
                tracker=tracker,
            )
        )
    return out


#: Every field any check reads: what a driver collects for `observe`.
FIELDS: tuple[str, ...] = tuple(
    sorted(
        {name for check in checks() for name in check.fields}
        | {
            "mppt2_voltage",
            "mppt2_current",
            "mppt3_current",
            "mppt4_current",
            "phase_b_voltage",
            "phase_b_current",
            "phase_c_voltage",
            "phase_c_current",
            "meter_phase_c_active_power",
            "meter_phase_b_active_power",
        }
    )
)


class Plausibility:
    """Every check, fed one poll at a time, and kept as a plain mapping."""

    def __init__(self) -> None:
        """Start with nothing seen."""
        self.checks = checks()
        self.observations = 0
        self.first: str | None = None
        self.last: str | None = None
        #: Checks whose first field has been read at least once. A field that
        #: is None at every poll is absent on this model (MPPT3 on an
        #: SH10RT), and a check that needs it is left out of the summary
        #: rather than reported as waiting for something that never comes.
        self._present: set[str] = set()

    def observe(self, values: Values, at: datetime) -> None:
        """Feed one poll to every check."""
        self.observations += 1
        stamp = at.isoformat()
        self.first = self.first or stamp
        self.last = stamp
        for check in self.checks:
            if values.get(check.fields[0]) is not None:
                self._present.add(check.name)
            check.observe(values, at)

    def applies(self, check: Check) -> bool:
        """Whether this device has what `check` reads."""
        return check.name in self._present

    def summary(self) -> dict[str, dict[str, Any]]:
        """Return a row per applicable check, in the ledger's summary shape."""
        rows: dict[str, dict[str, Any]] = {}
        for check in self.checks:
            if not self.applies(check):
                continue
            verdict, detail = check.verdict()
            rows[check.name] = {
                "kind": KIND,
                "verdict": verdict,
                "detail": detail,
                "needs": check.needs,
                "established": verdict is not None,
                "read_at": self.last,
            }
        return rows

    def unsettled(self) -> list[tuple[str, str]]:
        """Return (check, what it needs) for every check still without a verdict."""
        return [
            (name, row["needs"])
            for name, row in self.summary().items()
            if row["verdict"] is None
        ]

    def document(self) -> dict[str, Any]:
        """Return the publishable block: verdicts and counts, no readings."""
        return {
            "schema": SCHEMA,
            "observations": self.observations,
            "first": self.first,
            "last": self.last,
            "checks": {
                name: {k: v for k, v in row.items() if k != "kind"}
                for name, row in self.summary().items()
            },
        }

    def as_dict(self) -> dict[str, Any]:
        """Return everything to keep across a restart."""
        return {
            "schema": SCHEMA,
            "observations": self.observations,
            "first": self.first,
            "last": self.last,
            "present": sorted(self._present),
            "checks": {check.name: check.state() for check in self.checks},
        }

    @classmethod
    def from_dict(cls, state: Mapping[str, Any] | None) -> Plausibility:
        """Return a collection from `as_dict`, or a fresh one if it does not fit."""
        out = cls()
        if not state or state.get("schema") != SCHEMA:
            return out
        out.observations = int(state.get("observations") or 0)
        out.first = state.get("first")
        out.last = state.get("last")
        out._present = set(state.get("present") or [])
        kept = state.get("checks") or {}
        for check in out.checks:
            if check.name in kept:
                check.load(kept[check.name])
        return out
