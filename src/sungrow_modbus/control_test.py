"""Write a setting, read it back, and find out whether the scale is right.

The capability survey answers *what is here*. It cannot answer *and does
writing to it work*, because every register it touches it only reads. This is
the other half: a bounded procedure that writes each control, reads it back on
two independent legs, watches what the inverter actually does while the sun is
up, puts everything back, and says what it found.

**The one idea the whole module turns on.** `NumberField.encode` and `decode`
share the same factor, so a factor-10 error in this library is *invisible* to a
readback through this library -- write 700 W, get 700 W back, whatever the
factor is. A test built only on `Component.write` plus a refresh is
tautological. So every value is checked on three legs:

* **A, plumbing** -- library write, library read. Did it land at all, at the
  right address, and did the device keep it.
* **B, scale** -- the raw register word, against `spec_units_per_count` below,
  which is typed by hand from *Communication Protocol of Residential Hybrid
  Inverter* V1.1.11 and **never reads `field.scale`**. That independence is
  the entire point; a column derived from the thing under test proves nothing.
* **C, behaviour** -- what the inverter does with the engineering value. The
  only leg that can catch a firmware whose idea of the scale differs from the
  document's, because there the raw word is right and leg B is happy.

Nothing here talks to Home Assistant, opens a file, prints, or parses an
argument. It takes a `SungrowInverter`, a clock it can be lied to about, and a
progress callback; `scripts/sungrow_control_test.py` and the integration's
`control_test.py` are the two drivers that give it those.

**The rule that outranks every other rule in this file:** a restore is never
budgeted, never deadlined, and never skipped. Every early exit goes through it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Sequence
from dataclasses import dataclass, field as dataclass_field
import logging
import math
import time
from typing import Any, NamedTuple, Protocol

from modbus_connection import ModbusError, ModbusExceptionError, ServerDeviceBusyError

from .battery import ceiling as battery_ceiling
from .capabilities import Capability
from .derived import RUNNING_STATES
from .device import SungrowInverter

_LOGGER = logging.getLogger(__name__)

#: Bumped when the shape of the published `control_test` block changes, not
#: when a driver does. Carried into the block so a reader of an old document
#: knows which fields to expect.
BLOCK_SCHEMA = 1

# -- budgets -----------------------------------------------------------------
#
# Ten minutes, spent deliberately. The phases below add to 480 rather than to
# 600, and the 120 seconds of slack is not an oversight: `blocks.NARROW_BUDGET`
# learned this the expensive way, that a phase budgeted to the cap is a phase
# that kills the run on a slow link and loses the findings it already had.
#
# Every deadline is absolute and computed once at the start, never
# cumulatively, so a preflight that overruns eats its own slack and never the
# readback's.

RUN_BUDGET = 600.0
PREFLIGHT_BUDGET = 45.0
READBACK_BUDGET = 180.0
EFFECT_BUDGET = 210.0
VERIFY_BUDGET = 45.0
RESTART_BUDGET = 300.0

# -- effect statistics -------------------------------------------------------
#
# Every threshold here exists because the input is the sky. See `_bracket`.

SAMPLE_INTERVAL = 2.0
"""Seconds between samples inside a window. Faster than any coordinator tier."""

WINDOW = 20.0
"""Seconds per window, so ten samples. A median of ten survives four outliers."""

SETTLE = 8.0
"""Seconds discarded after a write, before the window that measures it."""

DRIFT_ABS_W = 150.0
DRIFT_FRACTION = 0.15
STABLE_MAD_W = 200.0
EFFECT_FLOOR_W = 200.0
SIGNIFICANCE = 3.0

# -- restore -----------------------------------------------------------------

SNAPSHOT_PAUSE = 1.0
"""Seconds between attempts at reading a control's before-state. Three
attempts, because on a link somebody else is polling the first one can simply
miss -- and missing it once used to cost that control the entire run."""

RESTORE_ATTEMPTS = 5
RESTORE_PAUSE = 2.0
"""Five attempts, two seconds apart. The 2026-09-07 hardware run lost the link
*during a restore* and left a register at 210 W, so this is sized for a link
that drops between any two steps rather than for one that works."""

# -- restart -----------------------------------------------------------------

RESTART_STOP_DEADLINE = 90.0
RESTART_DWELL = 10.0

#: How long to allow between the start command and a running state.
#:
#: **Measured, not guessed, and the first guess was less than half of it.** The
#: reference SH10RT reported a stopped state 2 seconds after the stop command
#: and took about four minutes to come back -- roughly two of those sitting in
#: `0x0020 Starting`. The original 180 seconds, divided into ten attempts of
#: eighteen, expired while the inverter was booting perfectly normally.
#:
#: Seven minutes because one machine is one machine: this is the only reading
#: this project has, the FAQ's figure for a *physical* cold boot is five
#: minutes, and the cost of waiting too long is a slow diagnostic where the
#: cost of waiting too little is telling somebody their inverter is dead.
RESTART_RUNNING_DEADLINE = 420.0
RESTART_GENERATING_DEADLINE = 120.0
RESTART_POLL = 2.0

#: How long to let a *stopped* inverter sit before sending the start again.
#:
#: Only a stopped one. An inverter that is `Starting` has taken the command and
#: is working on it, and re-sending into that is at best noise.
RESTART_RESEND_AFTER = 60.0

STOP_WORD = 0xCE
START_WORD = 0xCF
"""Register 13000, holding side. Table 4 of the specification, where the
register is Start/Stop; the input side of the same address is the running
state, which is why the writable field is `control.start_stop` and not
`running_state_raw`."""

#: Words in a running-state label that mean the inverter is not working.
#:
#: Derived from `derived.RUNNING_STATES` rather than typed out, and that is not
#: tidiness. **0x0000 means "Running"** -- the obvious guess, that zero means
#: off, is wrong and would have had this procedure refuse to run on every
#: healthy inverter, then mistake a working one for a stopped one during a
#: restart. A list derived from the labels cannot drift from them, and a new
#: code added to the map is classified the moment it is named.
STOPPED_WORDS = ("stop", "standby", "shutdown", "uninitialized")
RUNNING_WORDS = ("running", "off-grid charge")

#: A state that is neither, and pretending it does not exist was expensive.
#:
#: `0x0020 Starting` contains neither "stop" nor "running", so it fell between
#: both sets and the wait could not tell a booting inverter from a silent one.
#: Measured 2026-09-19: the reference SH10RT sat in it for minutes after a start
#: command, while the procedure re-sent that command ten times and then told its
#: owner the inverter had not come back and to start it by hand. It had come
#: back; it was booting.
STARTING_WORDS = ("starting",)

RUNNING_STATES_STOPPED = frozenset(
    code
    for code, label in RUNNING_STATES.items()
    if any(word in label.lower() for word in STOPPED_WORDS)
)


def is_starting(word: int | None) -> bool:
    """Whether the inverter is on its way up.

    Evidence that a start command was accepted, which is exactly what a wait
    needs in order to keep waiting instead of giving up or shouting.
    """
    if word is None:
        return False
    label = RUNNING_STATES.get(int(word))
    return label is not None and any(part in label.lower() for part in STARTING_WORDS)


def is_running(word: int | None) -> bool:
    """Whether this running-state word means the inverter is working.

    Strict on purpose: an unknown code is not running, because a procedure that
    writes to an inverter should not proceed on a state nobody has a name for.
    """
    if word is None:
        return False
    label = RUNNING_STATES.get(int(word))
    if label is None:
        return False
    return any(part in label.lower() for part in RUNNING_WORDS)


# -- verdicts ----------------------------------------------------------------
#
# One word per outcome, and each one names a different next step. The vocabulary
# is the report; a caller that has to interpret a boolean has been given less
# than was measured.

MATCH = "matched"
SCALED = "off by a clean decade"
SLOPE_WRONG = "two points, wrong slope"
OFF_BY = "off by something else"
CLAMPED = "the device clamped it"
REFUSED = "refused with an exception"
UNCHANGED = "the device kept its old value"
DROPPED = "the link dropped"
SKIPPED = "not run"

CONFIRMED = "the inverter did as it was told"
EFFECT_SCALED = "the inverter acted on a value off by a decade"
SIGN_INVERTED = "right magnitude, wrong direction"
NO_EFFECT = "nothing measurable happened"
INCONCLUSIVE = "could not tell"

#: Why something was skipped. A skip is a recorded non-result, never a pass.
OUT_OF_TIME = "out of time"
NOT_CAPABLE = "the device does not have it"
UNSAFE_STATE = "the house was in no state for it"
USER_DECLINED = "not asked for"
NO_BOUNDS = "its bounds could not be resolved"
NO_SNAPSHOT = "its current value could not be read"
NO_WINDOW = "no probe value can show a decade error here"

#: Which side a finding implicates, when it can be told.
LIBRARY = "library"
DEVICE = "device"

# -- exit codes --------------------------------------------------------------

CODES = {
    0: "every planned check ran and every readback matched",
    1: "nothing ran -- could not connect, or could not identify the device",
    2: "this cannot run here -- another client is polling, wrong device, "
    "inverter not running, or no PV and --allow-dark was not given",
    3: "ran, but checks were skipped or inconclusive",
    4: "a scale finding: at least one value came back off by a decade",
    5: "something was not restored, or the inverter may still be stopped",
}

#: Worst last. Note where 4 sits: a run that found a decade error is a
#: **successful** run -- it found the thing it exists to find -- so it ranks
#: below the codes that mean nothing was measured. 5 outranks everything,
#: because it is the only code where the house is left changed.
SEVERITY = (0, 3, 4, 1, 2, 5)


class Probe(NamedTuple):
    """One control, and everything needed to test it without trusting it.

    `spec_units_per_count` is the load-bearing field and the only one that is
    not derived: it is typed by hand from V1.1.11, cited in the comment beside
    each row, and compared against the register map by a test rather than read
    from it. If it were taken from `field.scale` this whole module would be
    checking that a number equals itself.

    The bounds mirror `scripts/writes.py` exactly, which a test asserts. That
    duplication is deliberate and is the trade already made for `IDENTIFY_UNITS`
    and for `fingerprint.PROBES`: the library cannot import a file from
    `scripts/`, and a table two copies of which are kept equal by a test beats a
    module that only works inside a checkout.
    """

    field: str
    component: str
    spec_register: int
    spec_units_per_count: float
    unit: str
    minimum: float = 0.0
    maximum: float = 0.0
    step: float = 1.0
    minimum_field: str | None = None
    maximum_field: str | None = None
    maximum_from_battery: bool = False
    exact: tuple[int, ...] = ()
    """Legal words for an enumeration. Non-empty means there is no scale
    question here at all: the check is word equality, and a value outside this
    tuple is never written."""
    requires: Capability | None = None
    preferred: float | None = None
    """A probe value chosen by hand where the arithmetic would pick a worse
    one. Still validated against the admissibility rules, never trusted."""


#: The controls this procedure writes, safest first, in the order it writes
#: them. The order matters twice over: the readback phase walks it forwards, and
#: the restore walks it backwards.
PROBES: tuple[Probe, ...] = (
    # Spec reg 13059, U16, 0.0~50.0, **0.1 %** per count.
    #
    # Probe 3 %: raw 30, so a decade error either way lands inside 0..50 and is
    # therefore *measurable* rather than refused. It is also far below any
    # plausible state of charge, which is what keeps it from commanding a grid
    # charge -- see `_guard_soc`.
    Probe(
        field="battery_min_soc",
        component="fast_holding",
        spec_register=13059,
        spec_units_per_count=0.1,
        unit="%",
        minimum=0,
        maximum=50,
        step=1,
        requires=Capability.BATTERY,
        preferred=3,
    ),
    # Spec reg 13058, U16, 50.0~100.0, **0.1 %** per count.
    #
    # No decade window exists: 10x50 is above 100 and 100/10 is below 50, so a
    # scale error here can only ever surface as an exception. Reported as
    # `NO_WINDOW` rather than quietly passing, because "matched" on this row
    # means less than it does on the others.
    Probe(
        field="battery_max_soc",
        component="fast_holding",
        spec_register=13058,
        spec_units_per_count=0.1,
        unit="%",
        minimum=50,
        maximum=100,
        step=1,
        requires=Capability.BATTERY,
        preferred=95,
    ),
    # Spec reg 13100, U16, 0~100, **1 % per count** -- whole percent, sitting
    # between two 0.1 % gauges. This is the trap the module exists for, and it
    # is the one register whose effect can never be observed at all: it governs
    # what the battery keeps back for a grid outage. Leg B is the only evidence
    # obtainable about it, ever.
    Probe(
        field="battery_reserved_soc_for_backup",
        component="fast_holding",
        spec_register=13100,
        spec_units_per_count=1,
        unit="%",
        minimum=0,
        maximum=100,
        step=1,
        requires=Capability.BATTERY,
        preferred=7,
    ),
    # Spec reg 33047, U16, **0.01 kW = 10 W per count**. The YAML's comment at
    # `legacy/modbus_sungrow.yaml:1328` says "scale=100" and its code says
    # `scale: 10`; the code is right and the parenthetical is an arithmetic
    # slip. Confirmed on hardware, which read `[20, 10]` as 200 W and 100 W.
    Probe(
        field="battery_max_charge_power",
        component="fast_holding",
        spec_register=33047,
        spec_units_per_count=10,
        unit="W",
        minimum=10,
        maximum_from_battery=True,
        step=100,
        requires=Capability.BATTERY,
    ),
    # Spec reg 33048, U16, 0.01 kW per count.
    Probe(
        field="battery_max_discharge_power",
        component="fast_holding",
        spec_register=33048,
        spec_units_per_count=10,
        unit="W",
        minimum=10,
        maximum_from_battery=True,
        step=100,
        requires=Capability.BATTERY,
    ),
    # Spec reg 13074, U16, **1 W per count**, bounds read from registers 5622
    # and 5623 because the inverter states them and a table would not.
    #
    # This stays 1 even though the register is written in tens of watts, and
    # the distinction is the whole point of leg B. `spec_units_per_count`
    # describes what the register **contains**, which is watts: 10000 back
    # against a 10000 W maximum. The decade lives on the write side alone,
    # where the firmware multiplies the word before storing it, and
    # `registers.AsymmetricNumberField` is what absorbs it. So after that fix a
    # 900 W write leaves the raw word at 900 and this row reads `matched`;
    # before it, the word was 9000 and this row read `SCALED`. Setting this to
    # 10 to "agree with the write scale" would make the run green against a
    # library that had gone wrong again -- the exact tautology the column
    # exists to avoid.
    Probe(
        field="export_power_limit",
        component="fast_holding",
        spec_register=13074,
        spec_units_per_count=1,
        unit="W",
        minimum_field="export_power_limit_min",
        maximum_field="export_power_limit_max",
        step=100,
        preferred=600,
    ),
    # Spec reg 13052, U16, **1 W per count**, "0-100% of BDC rated power".
    #
    # One register below 33047's neighbourhood in purpose and a decade away
    # from it in units. `scripts/writes.py:149-155` names this as the single
    # most likely future 10x error in the map, which is why it gets both a
    # two-point slope and a behavioural check.
    Probe(
        field="battery_forced_charge_discharge_power",
        component="fast_holding",
        spec_register=13052,
        spec_units_per_count=1,
        unit="W",
        maximum_from_battery=True,
        step=100,
        requires=Capability.BATTERY,
    ),
    # Spec reg 33149 and 33150, 10 W per count, **undocumented in V1.1.11**.
    # The scale is the YAML's, field-proven over years rather than specified,
    # and the reference SH10RT reads 200 W and 100 W. Probed low so that a
    # threshold left high by a failed restore cannot stop a charge starting.
    Probe(
        field="battery_charging_start_power",
        component="fast_holding",
        spec_register=33149,
        spec_units_per_count=10,
        unit="W",
        minimum=0,
        maximum=1000,
        step=10,
        requires=Capability.BATTERY_START_POWER,
        preferred=60,
    ),
    Probe(
        field="battery_discharging_start_power",
        component="fast_holding",
        spec_register=33150,
        spec_units_per_count=10,
        unit="W",
        minimum=0,
        maximum=1000,
        step=10,
        requires=Capability.BATTERY_START_POWER,
        preferred=80,
    ),
)

#: The two enumerations the effect phase drives. Not in `PROBES`, because they
#: are not scale questions and must never be written by the readback walk: one
#: of them makes the inverter *do* something, and it is written only inside the
#: forced charge check, only after the power beside it has been verified.
EMS_MODE = Probe(
    field="ems_mode_selection_raw",
    component="fast_holding",
    spec_register=13050,
    spec_units_per_count=1,
    unit="",
    exact=(0, 2, 3, 4),
)
FORCED_CMD = Probe(
    field="battery_forced_charge_discharge_cmd_raw",
    component="fast_holding",
    spec_register=13051,
    spec_units_per_count=1,
    unit="",
    exact=(0xAA, 0xBB, 0xCC),
    requires=Capability.BATTERY,
)
EXPORT_MODE = Probe(
    field="export_power_limit_mode_raw",
    component="fast_holding",
    spec_register=13087,
    spec_units_per_count=1,
    unit="",
    exact=(0x55, 0xAA),
)

EMS_FORCED = 2
FORCE_CHARGE = 0xAA
FORCE_DISCHARGE = 0xBB
FORCE_STOP = 0xCC
MODE_ON = 0xAA
# There is deliberately no MODE_OFF or EMS_SELF_CONSUMPTION constant. Nothing
# here restores a register to a *default*; it restores the value the snapshot
# found, which is not the same thing and is the only version that is safe. A
# named default is an invitation to write the other one.

#: Writable registers this procedure deliberately does not probe, and why.
#:
#: A test requires every name in `scripts/writes.py`'s writable set to be either
#: in `PROBES` or in here, so a control added to the integration cannot quietly
#: escape the procedure -- it fails the suite until somebody decides which of
#: the two it is.
NOT_PROBED: dict[str, str] = {
    "backup_mode_raw": (
        "a mode flag with no scale to get wrong, and turning it on changes what "
        "happens to the house in an outage"
    ),
    "load_adjustment_mode_enable_raw": (
        "a mode flag with no scale to get wrong, and it switches a real load"
    ),
    "load_adjustment_mode_selection_raw": (
        "an enumeration with no scale to get wrong, and each option changes what "
        "the load output does"
    ),
    "export_power_limit_mode_raw": (
        "written only when the run was given leave to enable export limiting, "
        "and then only to put it back"
    ),
    "ems_mode_selection_raw": (
        "written by the forced charge check, not by the readback walk"
    ),
    "battery_forced_charge_discharge_cmd_raw": (
        "written by the forced charge check, not by the readback walk"
    ),
}


# -- picking a value that can actually show a decade error -------------------

#: Values a device might already be holding, so writing one proves nothing when
#: the device ignores the write. Avoided rather than forbidden: `_admissible`
#: rejects them, and `choose_probe` steps away rather than giving up.
ROUND_NUMBERS = frozenset({0, 5, 10, 50, 100, 500, 1000, 5000, 10000})

TWO_SIDED = "a decade error either way would be visible"
ONE_SIDED_UP = "only a ten-times-too-large value would be visible"
ONE_SIDED_DOWN = "only a ten-times-too-small value would be visible"
DECADE_OUT_OF_RANGE = "no decade error would be visible; it could only be refused"


def _admissible(
    value: float,
    lo: float,
    hi: float,
    step: float,
    factor: float,
    current: float | None,
) -> bool:
    """Whether a probe value can carry evidence.

    Six conditions, and each one exists because its absence produces a result
    that *looks* like a measurement:

    * zero is the worst probe there is, because ten times zero and a tenth of
      zero are both zero;
    * out of bounds is refused, and a refusal says nothing about scale;
    * the value the register already holds cannot distinguish a device that
      wrote it from a device that ignored the write;
    * a value off the step or off the factor comes back rounded. On a scale-10
      field `encode` rounds half to even -- 205 W lands at 200 and 215 W at 220
      -- so a probe on a half-step produces an off-by-one raw that reads
      exactly like a finding and is not one;
    * a round number is what a device is most likely to be sitting on already.
    """
    if value == 0:
        return False
    if not lo <= value <= hi:
        return False
    if current is not None and math.isclose(value, current):
        return False
    if step and not math.isclose(value % step, 0.0, abs_tol=1e-9):
        return False
    if factor and not math.isclose((value / factor) % 1.0, 0.0, abs_tol=1e-9):
        return False
    return value not in ROUND_NUMBERS


def visibility(value: float, lo: float, hi: float) -> str:
    """Say which decade errors this value would make visible.

    A decade error is worth far more as an *accepted wrong value* than as an
    exception: exception 0x04 is what the inverter also returns for a value
    that is legitimately out of range, so a refusal cannot tell the two apart.
    The window where both `10*v` and `v/10` stay inside the bounds is where the
    evidence is.
    """
    up = value * 10 <= hi
    down = value / 10 >= lo and value / 10 > 0
    if up and down:
        return TWO_SIDED
    if up:
        return ONE_SIDED_UP
    if down:
        return ONE_SIDED_DOWN
    return DECADE_OUT_OF_RANGE


def choose_probe(
    probe: Probe,
    lo: float,
    hi: float,
    current: float | None,
    taken: Iterable[float] = (),
) -> tuple[float | None, str]:
    """Return a value to write, and what it would be able to show.

    Prefers the top of the decade window, because the largest signal is the one
    least likely to be lost in a clamp or a rounding. A hand-picked `preferred`
    wins where it is admissible and unused, since a few of these registers have
    a value that is obviously better than arithmetic would find -- 3 % for a
    minimum state of charge is chosen to sit below any real battery level, not
    because it is near a window edge.

    `taken` makes every value in a run unique, which is how a wrong address
    becomes visible: reading 800 out of the export register when 600 was
    written there names the mix-up instead of reporting two unrelated failures.
    """
    seen = {float(value) for value in taken}
    step = probe.step or 1.0
    factor = probe.spec_units_per_count

    if probe.preferred is not None:
        candidate = float(probe.preferred)
        if candidate not in seen and _admissible(
            candidate, lo, hi, step, factor, current
        ):
            return candidate, visibility(candidate, lo, hi)

    # The window first, then the whole range: a value that can show a decade
    # error is worth more than one that merely fits.
    windows = ((max(lo, 10 * lo), min(hi, hi / 10)), (lo, hi))
    for low, high in windows:
        if high < low:
            continue
        top = math.floor(high / step) * step
        bottom = math.ceil(low / step) * step
        candidate = top
        while candidate >= bottom:
            if candidate not in seen and _admissible(
                candidate, lo, hi, step, factor, current
            ):
                return candidate, visibility(candidate, lo, hi)
            candidate -= step
    return None, DECADE_OUT_OF_RANGE


# -- telling a decade error from a rounding ----------------------------------

DECADES = (10.0, 0.1, 100.0, 0.01)


def classify_ratio(observed: float, expected: float) -> tuple[str, float | None]:
    """Say whether `observed` is `expected` off by a whole decade.

    Quantised first, and that ordering is the whole subtlety. These registers
    hold small integers, and a decade below an expected 7 is **1**, not 0.7 --
    the device rounded, because a register cannot hold a fraction. A ratio test
    on those two numbers gives 0.143 and a logarithm gives -0.845, neither of
    them anywhere near a decade, so a purely multiplicative test reports the
    clearest possible finding as "off by something else".

    The logarithm is still worth keeping for large raws, where quantisation is
    invisible and a device might be off by a decade *and* a little.
    """
    if expected == 0 or observed == 0:
        return (MATCH if observed == expected else OFF_BY), None
    for decade in DECADES:
        if observed == round(expected * decade):
            return SCALED, decade
    exponent = math.log10(abs(observed) / abs(expected))
    nearest = round(exponent)
    if nearest != 0 and abs(exponent - nearest) < 0.02:
        return SCALED, 10.0**nearest
    if observed == expected:
        return MATCH, 1.0
    return OFF_BY, observed / expected


# -- statistics over a sky that will not sit still ---------------------------


def median(values: Sequence[float]) -> float:
    """Return the middle value, where a mean would be the obvious choice.

    PV output is not noisy in the way a mean assumes. A cloud edge is a step
    change and the maximum-power-point search is a spike, so a window of ten
    samples routinely contains two or three values that belong to a different
    world from the other seven. A median of ten survives four of them; a mean
    survives none, and the failure is silent -- it returns a number.
    """
    if not values:
        raise ValueError("no samples")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def mad(values: Sequence[float]) -> float:
    """Median absolute deviation: spread, measured the way the centre was.

    Reported raw rather than scaled to a standard deviation. It is used as a
    threshold, not as a distribution parameter, and multiplying it by 1.4826
    would only imply a normality that a cloudy afternoon does not have.
    """
    if not values:
        raise ValueError("no samples")
    centre = median(values)
    return median([abs(value - centre) for value in values])


# -- what a run produces -----------------------------------------------------


class ProbeResult(NamedTuple):
    """One control, written and read back on both legs."""

    field: str
    register: int
    spec_units_per_count: float
    unit: str
    original: float | None
    written: float | None
    library_read: float | None
    raw_word: int | None
    expected_raw: int | None
    ratio: float | None
    slope: float | None
    expected_slope: float | None
    verdict: str
    visibility: str
    implicates: str | None
    detail: str | None


class EffectResult(NamedTuple):
    """One behavioural check, bracketed by two readings of the same state."""

    check: str
    observable: str
    commanded: float | None
    commanded_unit: str
    before: float | None
    during: float | None
    after: float | None
    before_mad: float | None
    during_mad: float | None
    after_mad: float | None
    drift: float | None
    delta: float | None
    ratio: float | None
    verdict: str
    detail: str | None


class RestoreResult(NamedTuple):
    """One register put back, or not."""

    field: str
    original: float | int | None
    readback: float | int | None
    restored: bool
    attempts: int
    detail: str | None


class RestartResult(NamedTuple):
    """What a stop and start cost, in seconds, on this machine.

    Every field here is a number this project has never had. The recovery time
    after a Modbus stop is undocumented upstream and unmeasured in this repo;
    the only timing anywhere in it is the five minutes the FAQ gives for a
    physical cold boot, which is a different thing entirely.
    """

    stopped_after: float | None
    running_after: float | None
    generating_after: float | None
    stop_word_seen: int | None
    polls_refused_connection: int
    settings_survived: bool | None
    verdict: str
    detail: str | None


class Outcome(NamedTuple):
    """Everything one run established, and what it could not."""

    code: int
    probes: tuple[ProbeResult, ...]
    effects: tuple[EffectResult, ...]
    restores: tuple[RestoreResult, ...]
    restart: RestartResult | None
    conditions: dict[str, Any]
    unestablished: tuple[str, ...]

    @property
    def findings(self) -> tuple[ProbeResult | EffectResult, ...]:
        """The rows a reader must not miss, scale errors first."""
        scale = [row for row in self.probes if row.verdict in (SCALED, SLOPE_WRONG)]
        acted = [
            row for row in self.effects if row.verdict in (EFFECT_SCALED, SIGN_INVERTED)
        ]
        return (*scale, *acted)

    @property
    def not_restored(self) -> tuple[RestoreResult, ...]:
        """Anything the house is still carrying. Reported first, always."""
        return tuple(row for row in self.restores if not row.restored)


# -- the parts a driver supplies ---------------------------------------------


class Clock(Protocol):
    """Time, injectable, so a test does not wait out a ten-minute budget."""

    def monotonic(self) -> float:
        """Seconds from an arbitrary origin, monotonic."""

    async def sleep(self, seconds: float) -> None:
        """Wait, or pretend to."""


class RealClock:
    """The clock a run against hardware uses."""

    def monotonic(self) -> float:
        """Return the event loop's idea of now."""
        return time.monotonic()

    async def sleep(self, seconds: float) -> None:
        """Wait for real."""
        await asyncio.sleep(seconds)


@dataclass(frozen=True)
class Options:
    """What a run has been given leave to do.

    Every one of these defaults to the cautious answer, and each is a separate
    flag rather than a level, because they are not ordered: somebody who will
    allow a restart is not thereby somebody who will allow export limiting.
    """

    allow_dark: bool = False
    """Run with no PV. Half the procedure is meaningless; the readback half
    still means everything it ever did."""

    enable_export_limit: bool = False
    """Turn on feed-in limitation for the test, and off again afterwards.
    Off by default because this is the one setting whose failed restore leaves
    the house generating less than it could."""

    restart: bool = False
    """Stop and start the inverter, and time it."""

    simulated: bool = False
    """Stamp the result as evidence about nothing. A simulator stores raw words
    with no scale semantics, so legs A and B agree there by construction."""

    dry_run: bool = False
    """Resolve everything, write nothing, and report what would have happened."""

    restart_only: bool = False
    """Measure the stop and start, and nothing else.

    The readback and behavioural phases write nine registers between them, and
    none of that is needed to time a reboot. A house lending its inverter for
    the one measurement this project still lacks should not have to accept the
    other twenty as the price -- and fewer writes before deliberately stopping
    somebody's inverter is the safer order in any case.

    Preflight still runs, because the snapshot is what answers whether the
    settings survived the restart.
    """

    run_budget: float = RUN_BUDGET


Progress = Callable[[float, str], None]


class Guard(Exception):
    """A refusal to run, carrying the exit code it should end in.

    Refusing is a result. Every message here is written to be the whole
    explanation, because in Home Assistant it is the only thing the person who
    pressed the button will see.
    """

    def __init__(self, message: str, code: int = 2) -> None:
        """Record the message and the code the run should end in."""
        super().__init__(message)
        self.code = code


# -- the before-state, persisted before anything is written ------------------


@dataclass
class Snapshot:
    """What every control held before the run touched it.

    Persisted, flushed and its location announced **before the first write**.
    That ordering is the whole value of it: a snapshot written afterwards
    describes a house that has already been changed, and a snapshot held only
    in memory dies with the process that was going to use it.

    A field whose original value could not be read is dropped from the plan
    rather than carried. Never write what you cannot put back.
    """

    taken_at: float
    values: dict[str, float | int] = dataclass_field(default_factory=dict)
    raw: dict[str, int] = dataclass_field(default_factory=dict)
    bounds: dict[str, list[float]] = dataclass_field(default_factory=dict)
    unreadable: dict[str, str] = dataclass_field(default_factory=dict)
    battery_ceiling: float | None = None
    stopped_at: float | None = None
    """Set the moment before 0xCE goes out and cleared only once the inverter
    has been *seen* running again. A snapshot that still carries it is the one
    thing a recovery path must lead with."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe copy, for a file or Home Assistant's store."""
        return {
            "taken_at": self.taken_at,
            "values": dict(self.values),
            "raw": dict(self.raw),
            "bounds": {name: list(pair) for name, pair in self.bounds.items()},
            "unreadable": dict(self.unreadable),
            "battery_ceiling": self.battery_ceiling,
            "stopped_at": self.stopped_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Snapshot:
        """Rebuild a snapshot saved by `to_dict`."""
        return cls(
            taken_at=float(data.get("taken_at", 0.0)),
            values=dict(data.get("values", {})),
            raw=dict(data.get("raw", {})),
            bounds={
                name: list(pair) for name, pair in dict(data.get("bounds", {})).items()
            },
            unreadable=dict(data.get("unreadable", {})),
            battery_ceiling=data.get("battery_ceiling"),
            stopped_at=data.get("stopped_at"),
        )


#: What the restore walks, and in this order. Reverse of the order things are
#: written, with one rule that outranks the reversal: the forced-charge command
#: goes back to Stop **first**, before anything else, because it is the only
#: register in the set that makes the inverter do something rather than merely
#: describe a limit. Putting a power back while the inverter is still forcing a
#: charge at the old one is a worse intermediate state than any other.
RESTORE_FIRST = (FORCED_CMD.field, EMS_MODE.field)
RESTORE_LAST = (EXPORT_MODE.field,)


def restore_order(fields: Iterable[str]) -> tuple[str, ...]:
    """Return the fields to restore, in the order it is safe to restore them.

    The state-of-charge pair is the part that has to be computed rather than
    fixed. The inverter enforces `min < max`, so whichever direction the pair
    is moving decides which half must move first -- restore them in the wrong
    order and the device refuses one of the two writes, leaving the house with
    exactly one of the run's values still in place.
    """
    remaining = [name for name in fields]
    first = [name for name in RESTORE_FIRST if name in remaining]
    last = [name for name in RESTORE_LAST if name in remaining]
    middle = [name for name in remaining if name not in first and name not in last]
    return (*first, *middle, *last)


def soc_pair_order(
    current_min: float | None,
    current_max: float | None,
    target_min: float | None,
    target_max: float | None,
) -> tuple[str, ...]:
    """Return the two state-of-charge fields in an order that never crosses.

    Moving the minimum up past a maximum that has not moved yet is refused, and
    so is moving the maximum down past a minimum that has not moved yet. Raising
    the ceiling first, or lowering the floor first, is always safe.
    """
    low, high = "battery_min_soc", "battery_max_soc"
    if None in (current_min, current_max, target_min, target_max):
        return (low, high)
    if target_min > current_min:  # type: ignore[operator]
        return (high, low)
    return (low, high)


#: Components the observables live in, refreshed together so a sample is one
#: moment rather than three.
SAMPLE_COMPONENTS = ("realtime_input", "fast_input", "battery_power")
STATE_COMPONENTS = ("medium_input", "slowest_input", "fast_holding")

#: How far a probe value must stay below the state of charge before it is safe.
#: A minimum raised above where the battery actually sits is an instruction to
#: charge, and on a hybrid permitted to charge from the grid that is an
#: instruction to buy electricity.
SOC_MARGIN = 5.0

#: Above this the pack is tapering on its own and a charge check measures the
#: taper rather than the setting; below `SOC_MARGIN` above the floor there is
#: nothing to discharge.
SOC_CHARGE_CEILING = 90.0

#: How far below the current state of charge the ceiling check puts `max_soc`.
#:
#: Small on purpose. The register is a *charge* ceiling, so the inverter stops
#: charging rather than discharging to meet it -- but two percent is a cheap
#: way of not depending on that, and it is still far outside the resolution of
#: the reading.
SOC_CEILING_MARGIN = 2.0

#: The lowest state of charge the ceiling check will run at.
#:
#: `battery_max_soc` cannot go below 50 %, so there has to be room for
#: `soc - SOC_CEILING_MARGIN` above that floor. This is that, plus enough that
#: a reading drifting mid-check cannot push the target under the bound.
SOC_CEILING_FLOOR = 55.0

#: What counts as "stopped" for a check whose expected outcome is that
#: something ceases. Absolute watts rather than a fraction: the quantity is
#: heading for zero, and a percentage of zero is not a tolerance.
STOPPED_W = 200.0

#: The least export that makes a limit check worth running, derived rather than
#: chosen. The check caps export at `EXPORT_FRACTION` of what it measures, so
#: the drop it has to see is `1 - EXPORT_FRACTION` of that -- and a drop is only
#: a reading when it clears `EFFECT_FLOOR_W` and the house's own noise.
#:
#: `200 / 0.6` is 333 W, and the factor of three on top is headroom for a MAD
#: the floor does not cover.
#:
#: **It was a flat 2000 W until 2026-09-19**, which was a round number with no
#: derivation behind it, and it turned out to be the thing standing between the
#: check and its first measurement: a house with 2332 W of PV and 451 W of load
#: can export 1881 W and no more. Worth being plain that this was loosened
#: after a measurement failed to clear it -- the defence is that the new value
#: is computed from the tolerances the verdict already uses, and that at 1881 W
#: the drop under test is 1130 W against a 200 W floor.
#: The step `scripts/writes.py` gives the export limit, and the smallest cap
#: that can therefore be asked for.
EXPORT_STEP_W = 100.0

#: What the behavioural checks command, in watts, for the forced charge, the
#: forced discharge and the export cap alike.
#:
#: **Chosen, not derived**, and the history is the argument for choosing. The
#: derivation asked each house's own hardware what a safe fraction was, which
#: is a good instinct and produced a forced charge of 5800 W against a 5883 W
#: pack the first time a battery was small enough for its decade window to run
#: out. A number that has to be read against three other functions to know what
#: it will be is a number nobody checks; this one is legible from here.
#:
#: 1250 W is large enough to clear `EFFECT_FLOOR_W` several times over, so a
#: window can tell it from the house breathing, and small enough to be
#: unremarkable on any inverter this integration supports -- about a tenth of a
#: 10 kW machine and a fifth of a 5 kW one. It is clamped to the register's own
#: bounds before use, so a pack that cannot take it gets what it can take.
FORCED_EFFECT_W = 1250.0

#: How far below the battery's *stated* ceiling a manufactured discharge aims.
#:
#: The ceiling is read once, at preflight, and it is not a constant of the
#: hardware: a BMS throttles as the pack fills and as it warms, and the same
#: house read 10000 W in the afternoon and 3200 W at 99.8 % that night. A
#: setpoint written against a ceiling read minutes earlier is therefore clamped
#: to whatever the limit has become, which is what happened at bar12 -- 3158 W
#: asked, 3150 W accepted, and the whole export check abandoned over 8 W.
FORCE_EXPORT_HEADROOM = 0.05

#: The largest shortfall that counts as a clamp rather than a finding.
#:
#: A clamp is the device saying "not that much"; a decade error is the device
#: saying something entirely different, and it is short by about 90 %. Ten per
#: cent separates them with room to spare, and the decade verdicts are checked
#: first regardless, so this can never swallow one.
CLAMP_TOLERANCE = 0.1

#: The least export a limit check can be run against.
#:
#: The cap has to be *under* the export by more than the floor, or curtailing to
#: it changes nothing measurable. A quarter more for headroom, because the house
#: moves while the windows are taken.
MIN_EXPORT_W = 1.25 * (FORCED_EFFECT_W + EFFECT_FLOOR_W)


def export_cap(exporting: float, step: float = EXPORT_STEP_W) -> float:
    """Return the cap to ask for, which is simply `FORCED_EFFECT_W`.

    It was a tenth of the room, and that had a real reason: register 13074
    applied **ten times** what it was given, so a cap set to a sensible fraction
    of current export became a multiple of it, bound on nothing, and the check
    reported that nothing happened -- the same answer a device ignoring the
    write would give. Asking for a tenth meant the decade case still curtailed,
    which made this an independent second detector of the bug.

    That reason has expired, and saying why matters more than the change. The
    decade is **compensated in the library now**, by
    `registers.AsymmetricNumberField`, and confirmed on three houses. So a tenth
    of the room no longer produces a tenth-sized cap on the wire: it produces a
    tenth-sized cap in reality, curtailing the house ten times harder than
    anyone asked for, to detect something that is already fixed and already
    guarded by leg B at commit time.

    What is lost is narrower than "leg C stops catching the decade", and the
    precision matters. A firmware that decuples is the *expected* one and is
    compensated, so it lands on 1250 W and confirms. A firmware that does **not**
    decuple gets 125 W where 1250 was asked, which binds harder rather than
    less, and still reads as `EFFECT_SCALED` -- and that is the error mode that
    matters now, because it is what an unexpected firmware would do to a build
    that compensates.

    The case genuinely given up is a build where the compensation is **broken or
    removed** and the firmware decuples anyway: the cap then lands at 12500 W,
    binds on nothing, and reads `NO_EFFECT`, indistinguishable from an ignored
    write. The old tenth-of-the-room cap would still have bound and shown the
    decade. That is accepted because leg B sees exactly that regression from the
    raw word, and `tests/test_writes.py` fails on it at commit time rather than
    on somebody's roof -- and because the price of keeping the detector is
    curtailing every honest house tenfold on every run.

    `exporting` and `step` are kept in the signature because the caller clamps
    to the register's live bounds and the report quotes both.
    """
    del exporting, step  # kept for the caller's contract; the cap is stated now
    return FORCED_EFFECT_W


MIN_PV_W = 200.0
"""Below this there is nothing to limit and nothing to divert, so the effect
phase is measuring noise. The readback phase does not care and still runs."""


class Sample(NamedTuple):
    """One moment of the house, read from three components at once."""

    at: float
    pv: float | None
    battery: float | None
    export: float | None
    load: float | None
    soc: float | None


class ControlTest:
    """One run: preflight, readback, effect, restore, and maybe a restart.

    Construct it with a connected `SungrowInverter` whose tiers have been read
    at least once, call `async_run`, and read the `Outcome`. The object holds
    the snapshot for the whole run, which is what makes `async_restore` callable
    on its own after something went wrong.
    """

    def __init__(
        self,
        inverter: SungrowInverter,
        *,
        options: Options | None = None,
        on_progress: Progress | None = None,
        clock: Clock | None = None,
        on_snapshot: Callable[[Snapshot], Awaitable[None]] | None = None,
    ) -> None:
        """Prepare a run. Nothing is read and nothing is written until `async_run`."""
        self.inverter = inverter
        self.options = options or Options()
        self.clock = clock or RealClock()
        self._progress = on_progress
        self._on_snapshot = on_snapshot
        self.snapshot = Snapshot(taken_at=0.0)
        self.capabilities: frozenset[Capability] = frozenset()
        self.plan: tuple[Probe, ...] = ()
        self.conditions: dict[str, Any] = {}
        self.direct: bool | None = True
        """Whether this endpoint is the inverter's own port rather than a
        dongle, or `None` where the link would not say. Decides whether the
        readback legs can be believed: a WiNet-S forwards a write and then
        answers the old value when it is read back, so through one "write it
        and read it back" settles nothing. `None` is not `False` -- it means
        the question could not be put, and the report says so rather than
        discarding legs A and B on a guess."""
        self.unestablished: list[str] = []
        self._written: dict[str, float] = {}
        self._last_refused: str | None = None
        self.refusals: dict[str, str] = {}
        """Field name to the exception a write came back with, verbatim.

        Kept because "refused" is not a finding on its own: the device saying a
        value is out of range and the device saying it is busy are different
        facts, and only one of them is about the register.
        """
        self._taken: list[float] = []
        self.accepted_forced_w: float | None = None
        """What the pack actually took for the last forced command.

        Not the same as what was asked for: a BMS clamps to its own live limit,
        which moves with charge and temperature. The effect checks compare
        measured power against what was *accepted*, because comparing against a
        figure the device already declined would report the clamp as a finding.
        """
        """Every value this run has written anywhere, so no two controls get the
        same one. Held on the run rather than in the readback walk, because the
        behavioural phase picks a value too -- and the first hardware dry run
        had it choose 700 W for a forced charge when 700 W had already gone to
        the charge limit, which is exactly the collision that makes a write to
        the wrong address invisible."""
        self._deadlines: dict[str, float] = {}
        self._done = 0
        self._total = 1
        self._codes: set[int] = {0}

    # -- progress and budget -------------------------------------------------

    def _step(self, label: str) -> None:
        """Advance the progress bar by one counted unit."""
        self._done += 1
        if self._progress is not None:
            self._progress(min(self._done / self._total, 1.0), label)

    def _plan_budget(self) -> None:
        """Fix every phase deadline now, against one origin.

        Absolute rather than cumulative, and that is the point: a preflight that
        overruns spends its own slack and leaves the readback's deadline exactly
        where it was. Cumulative budgets let the first slow phase eat the phase
        that would have found something.
        """
        start = self.clock.monotonic()
        share = self.options.run_budget / RUN_BUDGET
        running = start
        for name, budget in (
            ("preflight", PREFLIGHT_BUDGET),
            ("readback", READBACK_BUDGET),
            ("effect", EFFECT_BUDGET),
            ("verify", VERIFY_BUDGET),
        ):
            running += budget * share
            self._deadlines[name] = running
        self._deadlines["restart"] = running + RESTART_BUDGET

    def _expired(self, phase: str) -> bool:
        """Whether this phase is out of time. Never consulted by the restore."""
        return self.clock.monotonic() >= self._deadlines.get(phase, math.inf)

    def _note(self, sentence: str) -> None:
        """Record something this run could not establish."""
        if sentence not in self.unestablished:
            self.unestablished.append(sentence)

    def _worst(self, code: int) -> None:
        """Remember a code, so the run ends in the most serious one seen."""
        self._codes.add(code)

    @property
    def code(self) -> int:
        """The most serious outcome this run reached."""
        return max(self._codes, key=SEVERITY.index)

    # -- reading -------------------------------------------------------------

    async def _refresh(self, *names: str) -> None:
        """Re-read some components, tolerating a component that will not answer.

        Tolerated rather than raised: a poll losing one block is normal on this
        hardware, and a run that aborts on the first missing optional component
        would never complete on an inverter without a battery.
        """
        for name in names:
            try:
                await self.inverter.component(name).async_update()
            except (ModbusError, TimeoutError, OSError) as err:
                _LOGGER.debug("control test: %s did not answer: %s", name, err)

    def _value(self, name: str) -> Any:
        """Return a decoded field, or None where the device has no such field."""
        try:
            return self.inverter.field(name)
        except AttributeError:
            return None

    async def _raw(self, probe: Probe) -> int | None:
        """Read the register's own word, which is leg B's whole evidence.

        Deliberately not routed through the component: the component would
        decode it with the very factor under test, and a value that has been
        through that factor cannot be used to check it.
        """
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        if resolved is None:
            return None
        if resolved.count != 1:
            # Every control in `PROBES` is one U16, which a test asserts. A
            # wider one would need its word order applied here, and applying
            # the map's word order would put the map back into leg B.
            return None
        try:
            words = await self.inverter.async_read_words("holding", resolved.address, 1)
        except (ModbusError, TimeoutError, OSError) as err:
            _LOGGER.debug("control test: raw read of %s failed: %s", probe.field, err)
            return None
        return words[0]

    async def _sample(self) -> Sample:
        """Read one moment of the house."""
        await self._refresh(*SAMPLE_COMPONENTS)
        return Sample(
            at=self.clock.monotonic(),
            pv=self._value("total_dc_power"),
            battery=self._value("battery_power"),
            export=self._value("export_power_raw"),
            load=self._value("load_power"),
            soc=self._value("battery_level"),
        )

    # -- preflight -----------------------------------------------------------

    def _battery_ceiling(self) -> float | None:
        """Return what this battery will take, by the one shared ladder."""
        capacity = None
        if Capability.SUNGROW_BATTERY in self.capabilities:
            capacity = self._value("battery_capacity_high_precision")
        return battery_ceiling(
            sungrow_capacity_kwh=capacity,
            bms_max_charging_current_a=self._value("bms_max_charging_current"),
            battery_voltage_v=self._value("battery_voltage"),
            bdc_rated_power_w=self._value("bdc_rated_power"),
        )

    def _bounds(self, probe: Probe) -> tuple[float, float] | None:
        """Resolve one control's real bounds, asking the device where it knows.

        The inverter knows its own limits better than a table does, and for the
        export limit it states them outright in registers 5622 and 5623. The
        YAML package read them from there rather than hardcoding them and was
        right to; a hardcoded ceiling is a value that is wrong on some model
        nobody owns yet.
        """
        low = probe.minimum
        high = probe.maximum
        if probe.minimum_field is not None:
            value = self._value(probe.minimum_field)
            if value is None:
                return None
            low = float(value)
        if probe.maximum_field is not None:
            value = self._value(probe.maximum_field)
            if value is None:
                return None
            high = float(value)
        if probe.maximum_from_battery:
            ceiling = self.snapshot.battery_ceiling
            if ceiling is None:
                return None
            high = float(ceiling)
        if high <= low:
            return None
        return low, high

    #: The address that tells a cable from a dongle. Sungrow does not forward
    #: the 6100 block over a WiNet-S, so a refusal is the transport answering.
    #: `fingerprint.PROBES` reads the same address for the survey.
    DIRECT_ONLY = 6099

    #: Three attempts, a second apart, for the same reason `SNAPSHOT_PAUSE`
    #: has them: on a link somebody else is polling, one read can simply miss.
    TRANSPORT_ATTEMPTS = 3
    TRANSPORT_PAUSE = 1.0

    async def _detect_transport(self) -> bool | None:
        """Whether this endpoint is the inverter's own port rather than a dongle.

        Worth its own read, because it decides what the run may claim. A WiNet-S
        forwards a write and then answers a **stale** value when the register is
        read back -- measured at gerd, where cable and dongle disagreed about
        33047 before anything was written, and a write sent over the dongle
        arrived while the dongle went on reporting the old figure.

        So through a dongle, "write it and read it back" is not evidence: it
        cannot tell a dropped write from a cache, in either direction. Leg C is
        untouched, since watching real power change needs no readback at all.

        **And waiting does not fix it**, which is the measurement that decides
        this rather than a guess. Polled every 5 s for two minutes, the same
        dongle never once reported a value the cable had confirmed -- and the
        figure it kept returning was hours old, not seconds. So there is no
        settling time the tool could sit out to earn legs A and B back on a
        dongle, and offering one would only make a stale answer look ripe.

        **Three answers, not two**, and the third is the point. This used to
        read the register once and treat *any* failure as a dongle, which is
        wrong in the one direction that costs something: a lost read is not a
        refusal. Measured 2026-09-20 on the reference SH10RT -- a cable, no
        communication module fitted at all, 1.9 ms median -- where a run made
        while Home Assistant was polling produced a document whose survey half
        said "direct to the inverter's LAN port" and whose control test said
        dongle, and which therefore stamped its own readback table "not
        evidence". Over a VPN, where this project has measured 10-second
        timeouts against milliseconds elsewhere, that would be the common case
        rather than the unlucky one.

        So a *refusal* -- the device answering with an exception code -- is
        evidence and means a dongle, while a connection lost, a timeout or a
        desync is the link failing to carry the question and is evidence of
        nothing. `ServerDeviceBusyError` sits with the latter: it means ask me
        later, not there is no such register. Undetermined returns `None`,
        which the report renders as an unknown rather than as a dongle,
        because asserting a dongle discards legs A and B.
        """
        for attempt in range(self.TRANSPORT_ATTEMPTS):
            try:
                await self.inverter.async_read_words("input", self.DIRECT_ONLY, 2)
            except ServerDeviceBusyError:
                pass
            except ModbusExceptionError:
                return False
            except (ModbusError, TimeoutError, OSError):
                pass
            else:
                return True
            if attempt < self.TRANSPORT_ATTEMPTS - 1:
                await self.clock.sleep(self.TRANSPORT_PAUSE)
        return None

    def _guards(self) -> None:
        """Refuse a run the house is in no state for.

        In Home Assistant this list is the only protection a button press has,
        because a button has no confirmation dialog. So every refusal is worded
        as the whole explanation rather than as a code, and every one of them
        is checked *before* the snapshot is spent.
        """
        state = self._value("running_state_raw")
        if state is None:
            raise Guard(
                "The inverter did not report a running state, so this run cannot "
                "tell whether it is safe to write to it.",
                code=1,
            )
        if not is_running(int(state)):
            label = RUNNING_STATES.get(
                int(state), f"an unknown code, 0x{int(state):04X}"
            )
            raise Guard(
                f"The inverter reports {label!r} rather than running. Every "
                "measurement here is about what it does while it works, so start "
                "it and try again."
            )
        pv = self._value("total_dc_power")
        self.conditions["pv_w"] = pv
        if not self.options.allow_dark and (pv is None or pv < MIN_PV_W):
            raise Guard(
                f"Only {pv or 0:.0f} W of PV. The behavioural half of this test "
                "measures what the inverter does with the sun it has, so run it "
                "while it is generating, or ask for the readback half alone."
            )
        soc = self._value("battery_level")
        self.conditions["soc_percent"] = soc
        if Capability.BATTERY in self.capabilities and soc is None:
            raise Guard(
                "This inverter has a battery but did not report its state of "
                "charge, and every battery guard here is computed from it."
            )

    async def _snapshot_read(
        self, probe: Probe
    ) -> tuple[float | int | None, int | None]:
        """Read one control's current value and raw word, retrying the read.

        Retried because the first hardware run showed why it has to be. On an
        inverter that something else was already polling, one read of the export
        power limit dropped -- and a single attempt meant that control was
        struck off the plan for the *whole run*, reported as "could not be
        read", while a read by hand a minute later answered perfectly.

        A dropped read on a contended link is a moment, not a state. That is the
        same thing `probe.py` learned when it started re-rounding the components
        a survey had missed rather than taking the first answer as final.
        """
        for attempt in (1, 2, 3):
            await self._refresh(probe.component)
            value = self._value(probe.field)
            raw = await self._raw(probe)
            if value is not None and raw is not None:
                return value, raw
            if attempt < 3:
                await self.clock.sleep(SNAPSHOT_PAUSE)
        _LOGGER.debug("control test: %s would not read before the run", probe.field)
        return None, None

    def _safe_soc_probe(self, probe: Probe, value: float) -> bool:
        """Whether a state-of-charge probe stays below where the battery sits.

        The one guard with a bill attached. A minimum state of charge raised
        above the level the battery is actually at is an instruction to charge,
        and a hybrid permitted to charge from the grid will do exactly that --
        with real money, and on some firmware it keeps going past the restore
        until it reaches the setting.
        """
        if probe.field not in ("battery_min_soc", "battery_reserved_soc_for_backup"):
            return True
        soc = self.conditions.get("soc_percent")
        if soc is None:
            return False
        return value < float(soc) - SOC_MARGIN

    async def _preflight(self) -> None:
        """Read everything, resolve the plan, and persist the before-state."""
        self._step("reading the inverter")
        await self._refresh(*STATE_COMPONENTS, *SAMPLE_COMPONENTS)
        self.capabilities = self.inverter.capabilities()
        self.direct = await self._detect_transport()
        self.conditions["direct_connection"] = self.direct
        if self.direct is False:
            self._note(
                "this endpoint is a WiNet-S rather than the inverter's own "
                "port, and a WiNet-S answers a register stale after "
                "forwarding a write to it -- so every readback verdict here "
                "describes what the dongle reported, not what the register "
                "holds. Waiting does not help: polled every 5 s for two "
                "minutes one never reported a value the cable had confirmed. "
                "The behavioural checks are unaffected"
            )
        elif self.direct is None:
            self._note(
                "the transport could not be settled: register 6100 was "
                "neither answered nor refused in "
                f"{self.TRANSPORT_ATTEMPTS} attempts -- the reads failed on "
                "the link itself, which is what contention looks like from "
                "this end. A cable answers that register and a dongle "
                "refuses it, but a lost read says neither. So the readback "
                "table below is reported as measured and carries whatever "
                "weight an unknown transport deserves: if this endpoint is "
                "in fact a dongle, those verdicts describe its cache rather "
                "than the register. The behavioural checks are unaffected"
            )
        self.conditions["capabilities"] = sorted(
            capability.value for capability in self.capabilities
        )
        self.conditions["model"] = self.inverter.model
        self._guards()

        snapshot = Snapshot(taken_at=self.clock.monotonic())
        snapshot.battery_ceiling = self._battery_ceiling()
        self.snapshot = snapshot
        self.conditions["battery_ceiling_w"] = snapshot.battery_ceiling

        plan: list[Probe] = []
        for probe in (*PROBES, EMS_MODE, FORCED_CMD, EXPORT_MODE):
            if probe.requires is not None and probe.requires not in self.capabilities:
                self._note(
                    f"{probe.field}: {NOT_CAPABLE} "
                    f"({probe.requires.value} did not answer)"
                )
                continue
            value, raw = await self._snapshot_read(probe)
            if value is None or raw is None:
                snapshot.unreadable[probe.field] = NO_SNAPSHOT
                self._note(f"{probe.field}: {NO_SNAPSHOT}, so it was never written")
                self._worst(3)
                continue
            snapshot.values[probe.field] = value
            snapshot.raw[probe.field] = raw
            if probe in (EMS_MODE, FORCED_CMD, EXPORT_MODE):
                continue
            bounds = self._bounds(probe)
            if bounds is None:
                self._note(f"{probe.field}: {NO_BOUNDS}")
                self._worst(3)
                continue
            snapshot.bounds[probe.field] = list(bounds)
            plan.append(probe)
        self.plan = tuple(plan)

        if self._on_snapshot is not None:
            # Before the first write, and the caller is expected to flush. A
            # snapshot that reaches the disk after the first write describes a
            # house that has already been changed.
            await self._on_snapshot(snapshot)
        self._step("the before-state is saved")

    # -- readback: legs A and B ----------------------------------------------

    WRITE_SETTLE = 1.5
    """Seconds between a write and the read that checks it. The YAML package
    used one second for its switch verification and a tenth for its selects,
    and both worked; this is the larger of the two with room for a dongle."""

    #: Controls worth a second probe value a decade below the first. A single
    #: point cannot tell a correct scale from a clamp that happens to sit on it
    #: -- both read back as the value asked for. Two points give a slope, and a
    #: clamp has a slope of zero, which no scale error can imitate.
    TWO_POINT = frozenset(
        {
            "battery_max_charge_power",
            "battery_max_discharge_power",
            "battery_forced_charge_discharge_power",
            "export_power_limit",
        }
    )

    def _expected_raw(self, probe: Probe, value: float) -> int:
        """Return what the register should hold, by the specification.

        No offset term: none of these registers has one, which V1.1.11 states
        for each. Taking the offset from `field.offset` would be the same
        mistake as taking the scale from `field.scale`.
        """
        return round(value / probe.spec_units_per_count)

    def _implicates(self, probe: Probe) -> str:
        """Say which side a decade error is on, where that can be told.

        If the map's factor already disagrees with the specification, this
        library encoded the value wrongly and the static test should have caught
        it long before any hardware was involved. If the two agree and the
        register still holds something else, the *device* is the one doing the
        arithmetic differently -- which is a finding about firmware, and the one
        worth publishing.
        """
        component = self.inverter.component(probe.component)
        resolved = component.resolved_fields.get(probe.field)
        scale = getattr(resolved.field, "scale", None) if resolved else None
        if scale is not None and not math.isclose(
            float(scale), probe.spec_units_per_count
        ):
            return LIBRARY
        return DEVICE

    async def _write(self, probe: Probe, value: float) -> str | None:
        """Write one control. Returns a verdict word on failure, None on success.

        The refusal is recorded with **which exception came back**, in
        `self.refusals`, because "refused" on its own is not a finding. An
        exception 0x04 is the device saying the value is out of range, which is
        a fact about the register; 0x06 is the device saying it is busy, which
        on a link something else is polling is a fact about the afternoon. The
        survey has named exception types since an open port 502 turned out not
        to be an inverter, and the control test lacked it until a refusal of
        `battery_min_soc` on 2026-09-15 could not be explained, then failed to
        reproduce on 2026-09-19.
        """
        if self.options.dry_run:
            return None
        try:
            await self.inverter.component(probe.component).write(probe.field, value)
        except ModbusError as err:
            _LOGGER.debug("control test: %s refused %s: %s", probe.field, value, err)
            self.refusals[probe.field] = f"{type(err).__name__}: {err}"
            self._last_refused = probe.field
            return REFUSED
        except (TimeoutError, OSError) as err:
            _LOGGER.debug("control test: %s dropped on %s: %s", probe.field, value, err)
            self.refusals[probe.field] = f"{type(err).__name__}: {err}"
            self._last_refused = probe.field
            return DROPPED
        self._written[probe.field] = value
        return None

    async def _probe_once(
        self, probe: Probe, value: float, bounds: tuple[float, float]
    ) -> ProbeResult:
        """Write one value and read it back on both legs."""
        original = self.snapshot.values.get(probe.field)
        expected = self._expected_raw(probe, value)
        blank = ProbeResult(
            field=probe.field,
            register=probe.spec_register,
            spec_units_per_count=probe.spec_units_per_count,
            unit=probe.unit,
            original=original,
            written=value,
            library_read=None,
            raw_word=None,
            expected_raw=expected,
            ratio=None,
            slope=None,
            expected_slope=1.0 / probe.spec_units_per_count,
            verdict=MATCH,
            visibility=visibility(value, *bounds),
            implicates=None,
            detail=None,
        )

        failure = await self._write(probe, value)
        if failure is not None:
            self._worst(3)
            return blank._replace(
                verdict=failure, detail=self.refusals.get(probe.field)
            )
        if self.options.dry_run:
            return blank._replace(
                verdict=SKIPPED, detail="dry run: nothing was written"
            )

        await self.clock.sleep(self.WRITE_SETTLE)
        await self._refresh(probe.component)
        library_read = self._value(probe.field)
        raw = await self._raw(probe)
        if raw is None:
            self._worst(3)
            return blank._replace(library_read=library_read, verdict=DROPPED)

        held = self.snapshot.raw.get(probe.field)
        if raw == held and expected != held:
            self._worst(3)
            return blank._replace(
                library_read=library_read, raw_word=raw, verdict=UNCHANGED
            )

        verdict, ratio = classify_ratio(raw, expected)
        implicates = self._implicates(probe) if verdict == SCALED else None
        detail = None
        if verdict == SCALED:
            self._worst(4)
        elif verdict == OFF_BY and library_read is not None:
            low, high = bounds
            if math.isclose(float(library_read), low) or math.isclose(
                float(library_read), high
            ):
                verdict = CLAMPED
                detail = "the readback sits exactly on a bound"
            self._worst(3)
        return blank._replace(
            library_read=library_read,
            raw_word=raw,
            ratio=ratio,
            verdict=verdict,
            implicates=implicates,
            detail=detail,
        )

    async def _readback(self) -> list[ProbeResult]:
        """Walk the plan, writing and checking each control, then putting it back.

        Each control is restored the moment its own check is done rather than at
        the end of the phase, so at no point is the house carrying more than one
        of this run's values.
        """
        results: list[ProbeResult] = []
        taken = self._taken
        for probe in self.plan:
            if self._expired("readback"):
                results.append(self._skipped(probe, OUT_OF_TIME))
                self._worst(3)
                continue
            # Unpacked rather than `tuple(...)`, which gives `tuple[float, ...]`
            # and loses the one thing that matters: these are a *pair*. The
            # snapshot stores them as a list because it is written to JSON, so
            # the pair-ness is a convention until something checks it. This
            # raises rather than passing a three-element bound down the call.
            low, high = self.snapshot.bounds[probe.field]
            bounds = (low, high)
            current = self.snapshot.values.get(probe.field)
            value, seen = choose_probe(probe, low, high, current, taken)
            if value is None:
                results.append(self._skipped(probe, "no admissible probe value"))
                self._worst(3)
                continue
            if not self._safe_soc_probe(probe, value):
                results.append(self._skipped(probe, UNSAFE_STATE))
                self._note(
                    f"{probe.field}: not written, because every admissible value "
                    "was too close to the battery's actual level to be safe"
                )
                self._worst(3)
                continue
            taken.append(value)
            self._step(f"{probe.field}, writing {value:g} {probe.unit}".strip())
            lifted = await self._lift_export_mode(probe)
            first = await self._probe_once(probe, value, bounds)
            if seen == DECADE_OUT_OF_RANGE:
                self._note(
                    f"{probe.field}: its bounds have no room for a value ten times "
                    "larger or smaller, so a scale error here could only ever show "
                    "as a refusal"
                )
            if probe.field in self.TWO_POINT and first.verdict in (MATCH, SCALED):
                first = await self._slope(probe, first, bounds, taken)
            results.append(first)
            await self._put_back(probe)
            if lifted:
                # Straight back down, before the next probe rather than at the
                # end of the phase. While it is up the house is capped at
                # whatever 13074 holds, and 13074 is holding a probe value --
                # so every second of this is a second of real curtailment.
                #
                # Back to the *snapshot's* word, not to a named "off". Nothing
                # in this module restores a register to a default, because a
                # default is a guess about what the owner wanted and the
                # snapshot is a measurement of it.
                was = self.snapshot.values.get(EXPORT_MODE.field)
                if was is not None:
                    await self._write(EXPORT_MODE, float(was))
        return results

    async def _slope(
        self,
        probe: Probe,
        first: ProbeResult,
        bounds: tuple[float, float],
        taken: list[float],
    ) -> ProbeResult:
        """Add a second point a decade down, and check the slope between them."""
        second_value = first.written / 10 if first.written else None
        # Checked against the register's own resolution rather than against the
        # entity's step. The step is what a slider offers a person, and a decade
        # below a step-sized value is usually not step-sized itself -- 70 W is a
        # tenth of 700 W and not a multiple of the 100 W the number entity moves
        # in. The register holds tens of watts and will take it, which is all
        # this second point needs; the *first* point stays on the step, because
        # that one is meant to be a value a user could also have written.
        if second_value is None or not _admissible(
            second_value,
            bounds[0],
            bounds[1],
            probe.spec_units_per_count,
            probe.spec_units_per_count,
            None,
        ):
            return first._replace(
                detail="one point only: no admissible second value a decade away"
            )
        taken.append(second_value)
        self._step(f"{probe.field}, second point {second_value:g} {probe.unit}".strip())
        second = await self._probe_once(probe, second_value, bounds)
        if second.raw_word is None or first.raw_word is None:
            return first._replace(
                detail="one point only: the second read did not answer"
            )
        span = first.written - second_value  # type: ignore[operator]
        if span == 0:
            return first
        slope = (first.raw_word - second.raw_word) / span
        expected = 1.0 / probe.spec_units_per_count
        verdict = first.verdict
        detail = first.detail
        if math.isclose(slope, 0.0, abs_tol=1e-9):
            verdict = CLAMPED
            detail = "two points, one answer: the device is clamping"
            self._worst(3)
        elif not math.isclose(slope, expected, rel_tol=0.01):
            verdict = SLOPE_WRONG
            self._worst(4)
        return first._replace(slope=slope, verdict=verdict, detail=detail)

    def _skipped(self, probe: Probe, reason: str) -> ProbeResult:
        """Return a recorded non-result: never a pass, never a failure."""
        return ProbeResult(
            field=probe.field,
            register=probe.spec_register,
            spec_units_per_count=probe.spec_units_per_count,
            unit=probe.unit,
            original=self.snapshot.values.get(probe.field),
            written=None,
            library_read=None,
            raw_word=None,
            expected_raw=None,
            ratio=None,
            slope=None,
            expected_slope=1.0 / probe.spec_units_per_count,
            verdict=SKIPPED,
            visibility=DECADE_OUT_OF_RANGE,
            implicates=None,
            detail=reason,
        )

    async def _lift_export_mode(self, probe: Probe) -> bool:
        """Switch feed-in limitation on for an export-limit probe, if allowed.

        Without this, leg B never runs on register 13074 at a house whose mode
        is off -- which is most of them. The register ignores writes entirely
        while 13087 is off, so the probe reports `UNCHANGED` and the one leg
        that can catch a cap read a decade *too large* is simply not performed.
        Leg C cannot cover for it: a cap ten times too big leaves the export
        where it was, which is indistinguishable from the write doing nothing.

        So the register with the only firmware quirk this project has found was
        also the one whose readback was routinely unavailable. That is the gap
        this closes, and it is closed only where the owner granted
        `--enable-export-limit`, because switching this on curtails a real
        house.

        Returns whether it was lifted, so the caller can put it straight back.
        """
        if probe.field != "export_power_limit" or not self.options.enable_export_limit:
            return False
        if self.snapshot.values.get(EXPORT_MODE.field) == MODE_ON:
            return False
        return await self._write(EXPORT_MODE, MODE_ON) is None

    async def _put_back(self, probe: Probe) -> None:
        """Restore one control immediately after its own check."""
        original = self.snapshot.values.get(probe.field)
        if original is None or probe.field not in self._written:
            return
        if await self._write(probe, float(original)) is None:
            self._written.pop(probe.field, None)

    # -- effect: leg C -------------------------------------------------------

    EFFECT_TOLERANCE = 0.25
    """How far a measured power may sit from the value that commanded it and
    still count as obedience. Generous on purpose: the question this leg
    answers is which *decade* the inverter is working in, and a check tight
    enough to argue about 15 % would spend its verdicts on taper and ramp rate."""

    DECADE_TOLERANCE = 0.35
    """How loosely a measured power may sit around ten times, or a tenth of,
    what was commanded. A decade is a factor of ten; nothing needs precision
    here, and a tight window would turn a clear finding into `OFF_BY`."""

    async def _window(
        self, observable: Callable[[Sample], float | None]
    ) -> list[float]:
        """Collect one window of samples, discarding the ones that did not read."""
        values: list[float] = []
        deadline = self.clock.monotonic() + WINDOW
        while self.clock.monotonic() < deadline:
            sample = await self._sample()
            value = observable(sample)
            if value is not None:
                values.append(float(value))
            await self.clock.sleep(SAMPLE_INTERVAL)
        return values

    def _decade(self, observed: float, commanded: float) -> float | None:
        """Return the decade `observed` sits at relative to `commanded`, if any."""
        if commanded == 0:
            return None
        for decade in DECADES:
            if math.isclose(
                observed, commanded * decade, rel_tol=self.DECADE_TOLERANCE
            ):
                return decade
        return None

    async def _bracket(
        self,
        check: str,
        observable: Callable[[Sample], float | None],
        observable_label: str,
        commanded: float | None,
        apply: Callable[[], Awaitable[str | None]],
        undo: Callable[[], Awaitable[None]],
        *,
        setpoint: bool,
        expect_stop: bool = False,
        commanded_unit: str = "W",
    ) -> EffectResult:
        """Measure one setting's effect, bracketed by two readings of the same state.

        The bracket is the whole answer to a fluctuating input. Before and after
        are two estimates of the *same* undisturbed house, so requiring them to
        agree is a test of whether the sky held still, asked of the sky rather
        than of a model of it. When they disagree the run says so and claims
        nothing -- a cloud that arrived during the measurement is a reason to
        have no opinion, never a reason to fail the inverter.
        """
        blank = EffectResult(
            check=check,
            observable=observable_label,
            commanded=commanded,
            commanded_unit=commanded_unit,
            before=None,
            during=None,
            after=None,
            before_mad=None,
            during_mad=None,
            after_mad=None,
            drift=None,
            delta=None,
            ratio=None,
            verdict=INCONCLUSIVE,
            detail=None,
        )
        if self.options.dry_run:
            return blank._replace(
                verdict=SKIPPED, detail="dry run: nothing was written"
            )

        before = await self._window(observable)
        if not before:
            return blank._replace(detail="nothing answered before the write")
        before_mid, before_mad = median(before), mad(before)

        # Rejected here, before the write is spent. A window this unstable
        # cannot carry a verdict however carefully the rest is measured, and
        # finding that out first costs nothing but the window itself.
        if before_mad > max(STABLE_MAD_W, 0.2 * abs(before_mid)):
            self._worst(3)
            self._note(
                f"{check}: not measured -- the house moved by {before_mad:.0f} W "
                "on its own before anything was written"
            )
            return blank._replace(
                before=before_mid,
                before_mad=before_mad,
                detail="the input was already unstable",
            )

        failure = await apply()
        if failure is not None:
            # Undone even though the change failed. `apply` is several writes,
            # and one of them failing means some of the others landed -- so the
            # only safe reading of a failure here is that something may have
            # been changed. The end-of-run restore would catch it anyway; this
            # keeps the window between them from existing.
            # Read **before** the undo, and that ordering is the whole point.
            # `undo` writes too, and on this register it fails as readily as
            # `apply` does -- so reading afterwards reported the exception from
            # putting the old value back, while claiming to describe the write
            # that failed. Measured: the export limit's refusal came back
            # naming `write_register(13073, 10000)`, which is the original, not
            # the cap the check had just tried to set.
            because = self.refusals.get(self._last_refused or "", "")
            await undo()
            self._worst(3)
            detail = f"the write {failure}"
            if because:
                detail = f"{detail}: {because}"
            return blank._replace(
                before=before_mid, before_mad=before_mad, detail=detail
            )
        try:
            await self.clock.sleep(SETTLE)
            during = await self._window(observable)
        finally:
            await undo()
        await self.clock.sleep(SETTLE)
        after = await self._window(observable)

        if not during or not after:
            self._worst(3)
            return blank._replace(
                before=before_mid,
                before_mad=before_mad,
                detail="a window did not read",
            )
        during_mid, during_mad_ = median(during), mad(during)
        after_mid, after_mad_ = median(after), mad(after)
        drift = abs(after_mid - before_mid)
        delta = during_mid - before_mid
        measured = blank._replace(
            before=before_mid,
            during=during_mid,
            after=after_mid,
            before_mad=before_mad,
            during_mad=during_mad_,
            after_mad=after_mad_,
            drift=drift,
            delta=delta,
        )
        return self._verdict(
            measured,
            check,
            observable_label,
            setpoint=setpoint,
            commanded=commanded,
            expect_stop=expect_stop,
        )

    def _verdict(
        self,
        measured: EffectResult,
        check: str,
        observable_label: str,
        *,
        setpoint: bool,
        commanded: float | None,
        expect_stop: bool,
    ) -> EffectResult:
        """Decide what three windows mean, given everything already measured.

        Separated from `_bracket` because it is the part with no `await` in it:
        `_bracket` opens windows, writes, waits and puts things back, and this
        reads the numbers that came out. They were one 188-line method, and the
        decisions were the half nobody could find.

        The order of the questions is the design, not an accident:

        1. **Drift first.** Before and after are two readings of the same
           undisturbed house, and when they disagree nothing else is worth
           asking -- the change cannot be attributed to the setting. The answer
           is `INCONCLUSIVE`, never a failure.
        2. **Then the decade**, for a setpoint, because a value off by a clean
           factor of ten is a finding and must not be reported as "close
           enough" by a tolerance wide enough to swallow it.
        3. **Then obedience**, and then the inverted sign, which is a named
           result rather than a confusing failure.
        4. **`expect_stop` is its own branch** because zero has no decades:
           there is no setpoint to be off by, only whether the thing went away.

        `self._worst` and `self._note` are called here rather than returned,
        which is why this is a method: the exit code and the "could not
        establish" list are properties of the run, not of one measurement.
        """
        before_mid = measured.before
        during_mid = measured.during
        after_mid_ = measured.after
        before_mad = measured.before_mad
        after_mad_ = measured.after_mad
        drift = measured.drift
        delta = measured.delta
        assert before_mid is not None and during_mid is not None
        assert before_mad is not None and after_mad_ is not None
        assert drift is not None and delta is not None
        del after_mid_

        if drift > max(DRIFT_ABS_W, DRIFT_FRACTION * abs(before_mid)):
            self._worst(3)
            self._note(
                f"{check}: not measured -- the house was {drift:.0f} W different "
                "afterwards, so the change cannot be attributed to the setting"
            )
            return measured._replace(detail="the input drifted across the measurement")

        if setpoint and commanded:
            decade = self._decade(during_mid, commanded)
            if decade is not None and decade != 1.0:
                self._worst(4)
                return measured._replace(
                    verdict=EFFECT_SCALED,
                    ratio=decade,
                    detail=f"commanded {commanded:.0f} W, measured {during_mid:.0f} W",
                )
            if math.isclose(during_mid, commanded, rel_tol=self.EFFECT_TOLERANCE):
                return measured._replace(
                    verdict=CONFIRMED, ratio=during_mid / commanded
                )
            if math.isclose(during_mid, -commanded, rel_tol=self.EFFECT_TOLERANCE):
                self._worst(4)
                return measured._replace(verdict=SIGN_INVERTED, ratio=-1.0)

        if expect_stop:
            # A check whose expected outcome is that something ceases, rather
            # than that it lands on a number. There is no setpoint to compare
            # against and no decade to be off by -- zero has no decades -- so
            # the question is only whether the quantity went away and came
            # back. `before` doubles as the significance floor: stopping a
            # charge that was never running establishes nothing.
            if abs(before_mid) < STOPPED_W:
                self._worst(3)
                self._note(
                    f"{check}: not measured -- {observable_label} was only "
                    f"{before_mid:.0f} W to begin with, so there was nothing to stop"
                )
                return measured._replace(detail="there was nothing to stop")
            if abs(during_mid) <= STOPPED_W:
                return measured._replace(verdict=CONFIRMED)
            self._worst(3)
            return measured._replace(
                verdict=NO_EFFECT,
                detail=f"{observable_label} carried on at {during_mid:.0f} W",
            )

        significant = abs(delta) > max(
            SIGNIFICANCE * max(before_mad, after_mad_), EFFECT_FLOOR_W
        )
        if not significant:
            self._worst(3)
            return measured._replace(
                verdict=NO_EFFECT,
                detail="nothing moved by more than the house moves on its own",
            )
        if commanded and not setpoint:
            # A cap, not a setpoint. Obedience means the quantity came down to
            # about the cap; it cannot mean it came down *to* the cap exactly,
            # because what it was capped from is not under anybody's control.
            if math.isclose(during_mid, commanded, rel_tol=self.EFFECT_TOLERANCE):
                return measured._replace(
                    verdict=CONFIRMED, ratio=during_mid / commanded
                )
            decade = self._decade(during_mid, commanded)
            if decade is not None and decade != 1.0:
                self._worst(4)
                return measured._replace(verdict=EFFECT_SCALED, ratio=decade)
        self._worst(3)
        return measured._replace(
            detail="something changed, but not to the value that was commanded"
        )

    def _charging(self, sample: Sample) -> float | None:
        """Charge power, positive when charging.

        `battery_power` is negative while charging, which is the inverter's own
        convention and not a mistake to correct silently -- a check that flips
        the sign without saying so would report `SIGN_INVERTED` for a device
        behaving exactly as documented.
        """
        return None if sample.battery is None else -float(sample.battery)

    def _discharging(self, sample: Sample) -> float | None:
        """Discharge power, positive when discharging."""
        return None if sample.battery is None else float(sample.battery)

    def _exporting(self, sample: Sample) -> float | None:
        """Export power, positive when exporting."""
        return None if sample.export is None else float(sample.export)

    async def _forced(
        self, direction: int, power: float, *, allow_clamp: bool = False
    ) -> str | None:
        """Command a forced charge or discharge, power first.

        The ordering is a rule, not a preference. The power register is written
        and its raw word checked **before** the command register is touched, so
        a mis-scaled power is caught while it is still only a number in a
        register -- rather than after the inverter has started acting on it.
        """
        probe = next(
            row
            for row in PROBES
            if row.field == "battery_forced_charge_discharge_power"
        )
        failure = await self._write(probe, power)
        if failure is not None:
            return failure
        raw = await self._raw(probe)
        expected = self._expected_raw(probe, power)
        if raw is None:
            return DROPPED
        self.accepted_forced_w = float(raw) * probe.spec_units_per_count
        if raw != expected:
            verdict, _ratio = classify_ratio(raw, expected)
            # A clamp is not a failure when the caller only needs *enough*
            # power rather than an exact figure. `_force_export` is that
            # caller: it wants the house exporting, and the device saying "I
            # will give you 3150 of the 3158 you asked for" is a yes.
            #
            # The decade verdicts are classified first and excluded here, so
            # this can never absorb the error the whole procedure exists to
            # find: a decade short is 90 % short, nowhere near the tolerance.
            short = expected - raw
            clamped = (
                allow_clamp
                and verdict not in (SCALED,)
                and 0 < raw < expected
                and short <= CLAMP_TOLERANCE * expected
            )
            if not clamped:
                self._note(
                    f"forced charge was not commanded: register "
                    f"{probe.spec_register} holds {raw} where {expected} was "
                    f"expected ({verdict})"
                )
                return verdict
            self._note(
                f"the battery clamped the manufactured discharge: asked for "
                f"{power:.0f} W, the pack accepted {self.accepted_forced_w:.0f} W "
                f"-- its own limit moves with charge and temperature, and the "
                f"check went ahead against what it accepted"
            )
        if (failure := await self._write(EMS_MODE, EMS_FORCED)) is not None:
            return failure
        return await self._write(FORCED_CMD, direction)

    async def _unforce(self) -> None:
        """Stop forcing, in the order that leaves no intermediate state worth having."""
        await self._write(FORCED_CMD, FORCE_STOP)
        original = self.snapshot.values.get(EMS_MODE.field)
        if original is not None:
            await self._write(EMS_MODE, float(original))
        probe = next(
            row
            for row in PROBES
            if row.field == "battery_forced_charge_discharge_power"
        )
        power = self.snapshot.values.get(probe.field)
        if power is not None:
            await self._write(probe, float(power))

    def _forced_power(self) -> float | None:
        """Return the power the forced checks command: `FORCED_EFFECT_W`, clamped.

        It used to be derived from the battery's own ceiling, so that ten times
        the commanded power was still inside what the pack was rated for. The
        instinct was right and the implementation had a hole: it borrowed
        `choose_probe`, which falls back from the decade window to the whole
        range once earlier probes have spent the window's values. That is
        correct for a readback, where the number is only written and read, and
        wrong here, where it is *commanded*. At a house with a 5883 W ceiling it
        resolved a 5800 W forced charge -- at night, 5.8 kW off the grid.

        A stated constant cannot do that. It is clamped to the register's live
        bounds, so a pack too small for 1250 W gets what it can take rather than
        a refusal, and `None` when the bounds cannot hold anything at all.
        """
        probe = next(
            (
                row
                for row in self.plan
                if row.field == "battery_forced_charge_discharge_power"
            ),
            None,
        )
        if probe is None:
            return None
        low, high = self.snapshot.bounds[probe.field]
        if high <= 0 or high < low:
            return None
        power = min(max(FORCED_EFFECT_W, low), high)
        if power <= 0:
            return None
        if power not in self._taken:
            self._taken.append(power)
        return power

    async def _effects(self) -> list[EffectResult]:
        """Run the behavioural checks the house is actually in a state for."""
        results: list[EffectResult] = []
        if self.options.simulated:
            # Not a shortcut to save time, though it does. A simulator stores
            # raw words and computes no power flows, so every window would read
            # the same seeded number before, during and after -- which this
            # phase would correctly report as "nothing measurable happened", a
            # verdict that says something about the simulator and nothing about
            # any inverter. Skipping it is the honest answer; running it would
            # fill a report with rows that look like evidence.
            self._note(
                "no behavioural checks: a simulator has no power flows to change, "
                "so there was nothing for a setting to have an effect on"
            )
            return results
        soc = self.conditions.get("soc_percent")
        power = self._forced_power()
        minimum = self.snapshot.values.get("battery_min_soc")

        if power is None:
            self._note(
                "no behavioural check of the battery: its forced charge power could "
                "not be resolved, so nothing could be commanded"
            )
        else:
            if soc is not None and float(soc) < SOC_CHARGE_CEILING:
                if not self._expired("effect"):
                    self._step(f"forced charge at {power:g} W")
                    results.append(
                        await self._bracket(
                            "forced charge",
                            self._charging,
                            "battery charge power",
                            power,
                            lambda: self._forced(FORCE_CHARGE, power),
                            self._unforce,
                            setpoint=True,
                        )
                    )
            else:
                self._note(
                    "no forced charge check: the battery is too full for a charge "
                    "to measure the setting rather than the pack's own taper"
                )
            floor = float(minimum) if minimum is not None else 0.0
            if soc is not None and float(soc) > floor + SOC_MARGIN:
                if not self._expired("effect"):
                    self._step(f"forced discharge at {power:g} W")
                    results.append(
                        await self._bracket(
                            "forced discharge",
                            self._discharging,
                            "battery discharge power",
                            power,
                            lambda: self._forced(FORCE_DISCHARGE, power),
                            self._unforce,
                            setpoint=True,
                        )
                    )
            else:
                self._note(
                    "no forced discharge check: the battery is at or near its "
                    "minimum state of charge, so there is nothing to discharge"
                )

        results.extend(await self._soc_ceiling_effect())
        results.extend(await self._export_effect())
        if self._expired("effect"):
            self._worst(3)
            self._note("the behavioural phase ran out of time before every check ran")
        return results

    async def _soc_ceiling_effect(self) -> list[EffectResult]:
        """Lower the charge ceiling under the battery and watch the charge stop.

        The only safe behavioural test of a state-of-charge limit, and the
        reason is the direction: it **stops** a charge rather than commanding
        one. The mirror-image test on `battery_min_soc` -- raise the floor above
        where the battery sits -- is an instruction to buy electricity, which is
        why the guards refuse it and why it is not written.

        What it establishes that a readback cannot: that this register is a
        ceiling the inverter actually enforces, not merely a number it stores.
        A scale error here is invisible to leg C in either direction, though --
        95 % and 9.5 % are both below a charging battery, so both would stop the
        charge. That is leg B's to catch, and the report says so rather than
        letting a `CONFIRMED` here be read as more than it is.

        Preconditions, all of which self-skip: the battery must be charging
        (nothing to stop otherwise), the state of charge must leave room above
        the register's own 50 % floor, and `battery_max_soc` must be in the plan.
        """
        probe = next((row for row in self.plan if row.field == "battery_max_soc"), None)
        if probe is None:
            return []
        soc = self.conditions.get("soc_percent")
        if soc is None or float(soc) < SOC_CEILING_FLOOR:
            self._note(
                "no charge-ceiling check: the battery is too low for the ceiling "
                f"to be put under it, since {probe.field} cannot go below "
                f"{probe.minimum:g} %"
            )
            return []
        sample = await self._sample()
        charging = self._charging(sample) or 0.0
        if charging < STOPPED_W:
            self._note(
                f"no charge-ceiling check: the battery was not charging "
                f"({charging:.0f} W), so there was no charge to stop"
            )
            return []
        if self._expired("effect"):
            return []

        original = self.snapshot.values.get(probe.field)
        target = float(soc) - SOC_CEILING_MARGIN
        low, high = self.snapshot.bounds[probe.field]
        target = min(max(target, low), high)
        self._step(f"charge ceiling at {target:g} %")

        async def apply() -> str | None:
            return await self._write(probe, target)

        async def undo() -> None:
            if original is not None:
                await self._write(probe, float(original))

        return [
            await self._bracket(
                "charge ceiling",
                self._charging,
                "battery charge power",
                target,
                apply,
                undo,
                # The one check whose commanded value is not a power. Reported
                # as "62.4 W" on its first hardware run, which is a state of
                # charge wearing the wrong unit -- and the table it appears in
                # is full of real watts, so nothing about it looked wrong.
                commanded_unit="%",
                setpoint=False,
                expect_stop=True,
            )
        ]

    async def _force_export(self, sample: Sample) -> float | None:
        """Make the house export by discharging the battery, or say why not.

        The export limit check needs power actually leaving, and most houses
        never offer it: a battery soaks up the surplus while the sun is up, and
        at night there is no surplus. That left a register carrying a real
        factor-10 error measurable only on a lucky afternoon.

        Discharging is the lever that works whenever the battery has charge,
        including after dark. Commanding more than the house is using sends the
        difference to the grid by definition -- no weather required.

        Returns the power it commanded, or None with a note saying which
        precondition was not met. Note what this costs: a minute of somebody's
        battery through a round trip. Small, but not nothing, which is why it
        is only reached when the house is not exporting on its own.
        """
        if Capability.BATTERY not in self.capabilities:
            self._note(
                "could not make the house export: no battery to discharge, and it "
                "was not exporting on its own"
            )
            return None

        soc = self.conditions.get("soc_percent")
        floor = float(self.snapshot.values.get("battery_min_soc") or 0.0)
        if soc is None or float(soc) <= floor + SOC_MARGIN:
            self._note(
                "could not make the house export: the battery is at "
                f"{soc}% against a floor of {floor:g}%, so there is nothing to "
                "spend on making one"
            )
            return None

        # Enough to cover the house and clear the threshold with room to spare,
        # because load moves while the windows are being taken. Derived from the
        # same figure the verdict uses rather than picked.
        load = abs(sample.load or 0.0)
        # Rounded to a whole watt, and not for tidiness. These registers hold
        # integers, and `NumberField.encode` takes a fast path on a factor-1
        # field -- `raw = int(value)`, which **truncates**. A fractional command
        # therefore lands one count low, fails its own verification, and the
        # discharge is abandoned with "off by something else". It went unnoticed
        # while this arithmetic happened to come out whole.
        want = float(round(load + MIN_EXPORT_W * 1.5))
        ceiling = self.snapshot.battery_ceiling
        if ceiling is not None:
            # Aim below the ceiling rather than at it. The figure was read at
            # preflight and the pack's real limit drifts underneath it, so
            # asking for the last few per cent is asking to be clamped.
            usable = float(round(ceiling * (1.0 - FORCE_EXPORT_HEADROOM) / 10.0)) * 10
            want = min(want, usable)
        if want - load < MIN_EXPORT_W:
            self._note(
                f"could not make the house export: {want:.0f} W is the most this "
                f"battery will give against a {load:.0f} W house, which leaves "
                f"{want - load:.0f} W of export where a cap needs "
                f"{MIN_EXPORT_W:.0f} W to bind"
            )
            return None

        self._step(f"discharging {want:g} W to make the house export")
        failure = await self._forced(FORCE_DISCHARGE, want, allow_clamp=True)
        if failure is not None:
            await self._unforce()
            self._note(f"could not make the house export: the discharge {failure}")
            return None
        await self.clock.sleep(SETTLE)
        # What the pack accepted, not what was asked for: a clamp is allowed
        # here, so the figure the report quotes has to be the real one.
        return self.accepted_forced_w if self.accepted_forced_w is not None else want

    async def _export_effect(self) -> list[EffectResult]:
        """Limit the export, if the house is exporting and limiting is allowed.

        Worth being plain about what this can and cannot show. A cap is only
        observable while the uncapped quantity exceeds it, so a limit read ten
        times too large leaves the export exactly where it was -- which is
        indistinguishable from the write doing nothing, from the mode being off,
        and from a cloud. This check can catch a limit applied a decade too
        *small*; the decade too large is leg B's to find, and only leg B's.
        """
        probe = next(
            (row for row in self.plan if row.field == "export_power_limit"), None
        )
        if probe is None:
            return []
        mode = self.snapshot.values.get(EXPORT_MODE.field)
        if mode != MODE_ON and not self.options.enable_export_limit:
            self._note(
                "no export limit check: feed-in limitation is switched off on this "
                "inverter, and this run was not given leave to switch it on"
            )
            return []
        sample = await self._sample()
        exporting = self._exporting(sample) or 0.0

        # Not exporting on its own? Make it, rather than skipping. The discharge
        # is held across all three windows deliberately: released between them,
        # the "after" reading would be measuring the discharge stopping rather
        # than the limit being lifted, and the drift gate would fail a check
        # that had worked.
        discharging: float | None = None
        if exporting < MIN_EXPORT_W:
            discharging = await self._force_export(sample)
            if discharging is None:
                return []
            exporting = self._exporting(await self._sample()) or 0.0
            if exporting < MIN_EXPORT_W:
                await self._unforce()
                self._note(
                    f"no export limit check: discharging {discharging:.0f} W still "
                    f"only produced {exporting:.0f} W of export, under the "
                    f"{MIN_EXPORT_W:.0f} W a cap needs to bind against"
                )
                return []

        if self._expired("effect"):
            if discharging is not None:
                await self._unforce()
            return []
        target = export_cap(exporting, probe.step or EXPORT_STEP_W)
        low, high = self.snapshot.bounds[probe.field]
        target = min(max(target, low), high)
        self._step(f"export limit at {target:g} W")

        async def apply() -> str | None:
            if (
                mode != MODE_ON
                and (failure := await self._write(EXPORT_MODE, MODE_ON)) is not None
            ):
                return failure
            return await self._write(probe, target)

        async def undo() -> None:
            original = self.snapshot.values.get(probe.field)
            if original is not None:
                await self._write(probe, float(original))
            if mode is not None and mode != MODE_ON:
                await self._write(EXPORT_MODE, float(mode))

        try:
            result = await self._bracket(
                "export power limit",
                self._exporting,
                "export power",
                target,
                apply,
                undo,
                setpoint=False,
            )
        finally:
            if discharging is not None:
                await self._unforce()
        if discharging is not None:
            note = f"export was made by discharging {discharging:.0f} W"
            result = result._replace(
                detail=f"{result.detail}; {note}" if result.detail else note
            )
        return [result]

    # -- restore: the part that is never budgeted ----------------------------

    def _probe_for(self, name: str) -> Probe | None:
        """Find a probe row by field name, enumerations included."""
        for probe in (*PROBES, EMS_MODE, FORCED_CMD, EXPORT_MODE):
            if probe.field == name:
                return probe
        return None

    async def async_restore(
        self, snapshot: Snapshot | None = None
    ) -> list[RestoreResult]:
        """Put every control back, and prove it went back.

        No deadline is consulted anywhere in here, and that is deliberate to the
        point of being the module's first rule. Every early exit -- an expired
        budget, a guard, a cancellation, an exception -- arrives here, and a
        restore that could be cut short by a clock would turn a run that ran out
        of time into a house left changed.

        A field that will not go back does not stop the others. The 2026-09-07
        run lost its link *during* a restore and left one register at 210 W;
        the answer is not to try harder on that field but to make sure its
        failure cannot take the rest with it.
        """
        snapshot = snapshot or self.snapshot
        names = [name for name in snapshot.values if self._probe_for(name) is not None]
        order = list(restore_order(names))
        if "battery_min_soc" in order and "battery_max_soc" in order:
            pair = soc_pair_order(
                self._value("battery_min_soc"),
                self._value("battery_max_soc"),
                snapshot.values.get("battery_min_soc"),
                snapshot.values.get("battery_max_soc"),
            )
            order = [name for name in order if name not in pair]
            order.extend(pair)

        results: list[RestoreResult] = []
        for name in order:
            probe = self._probe_for(name)
            original = snapshot.values.get(name)
            if probe is None or original is None:
                continue
            results.append(await self._restore_one(probe, float(original)))
        if any(not row.restored for row in results):
            self._worst(5)
        return results

    async def _restore_one(self, probe: Probe, original: float) -> RestoreResult:
        """Put one control back, and prove it: read first, write only if needed.

        Reading first is not an optimisation. The first hardware run reported
        `export_power_limit` as **not restored** -- the run's most serious
        verdict, the one that means a house is left changed -- when the register
        was holding its original value the whole time. The inverter had silently
        ignored the write of the probe value, so there was nothing to undo, and
        then refused the write of the original, so the restore called itself
        failed.

        A restore is a statement about where the register *is*, not about
        whether a write succeeded. Asking the register settles it, and it also
        means a control this run never managed to change cannot be reported as
        one it failed to change back.
        """
        await self._refresh(probe.component)
        current = self._value(probe.field)
        if current is not None and math.isclose(
            float(current), original, rel_tol=1e-6, abs_tol=1e-6
        ):
            return RestoreResult(
                field=probe.field,
                original=original,
                readback=current,
                restored=True,
                attempts=0,
                detail="already holding its original value",
            )

        detail: str | None = None
        for attempt in range(1, RESTORE_ATTEMPTS + 1):
            failure = await self._write(probe, original)
            if failure is None:
                await self.clock.sleep(self.WRITE_SETTLE)
                await self._refresh(probe.component)
                readback = self._value(probe.field)
                if readback is not None and math.isclose(
                    float(readback), original, rel_tol=1e-6, abs_tol=1e-6
                ):
                    return RestoreResult(
                        field=probe.field,
                        original=original,
                        readback=readback,
                        restored=True,
                        attempts=attempt,
                        detail=None,
                    )
                detail = f"wrote it back but read {readback!r}"
            else:
                detail = f"the write {failure}"
            if attempt < RESTORE_ATTEMPTS:
                await self.clock.sleep(RESTORE_PAUSE)
        _LOGGER.warning(
            "control test could not restore %s to %s: %s", probe.field, original, detail
        )
        return RestoreResult(
            field=probe.field,
            original=original,
            readback=self._value(probe.field),
            restored=False,
            attempts=RESTORE_ATTEMPTS,
            detail=detail,
        )

    # -- restart -------------------------------------------------------------

    async def _running_word(self) -> int | None:
        """Read the running state, treating a dropped link as a reading of nothing.

        During a stop the inverter may drop the connection entirely, so a
        connection error here is not a failure of the poll -- it is one of the
        two ways "not running" looks from this end. The two are counted
        separately, because a model whose stopped code differs would otherwise
        be indistinguishable from a hang.
        """
        try:
            await self.inverter.component("realtime_input").async_update()
        except (ModbusError, TimeoutError, OSError):
            return None
        value = self._value("running_state_raw")
        return None if value is None else int(value)

    async def _await_state(
        self, deadline: float, wanted: Callable[[int], bool]
    ) -> tuple[float | None, int | None, int]:
        """Poll the running state until it satisfies `wanted`, or time runs out."""
        started = self.clock.monotonic()
        refused = 0
        while self.clock.monotonic() - started < deadline:
            word = await self._running_word()
            if word is None:
                refused += 1
            elif wanted(word):
                return self.clock.monotonic() - started, word, refused
            await self.clock.sleep(RESTART_POLL)
        return None, None, refused

    async def async_ensure_running(self) -> bool:
        """Start the inverter and keep trying. Safe to call from anywhere.

        The one method in this module a driver may call out of band, because it
        is what a shutdown hook and a repair flow both need: the inverter is
        never left stopped, whatever happened to the run that stopped it.

        **Waits on one deadline rather than re-sending on a short one.** The
        first version divided the whole allowance into ten attempts and wrote
        the start command at the top of each -- so against an inverter that
        takes minutes to boot it re-sent nine times into a machine already
        doing what it had been asked, ran out of its 180 seconds while the
        state still read `Starting`, and reported that the inverter had not
        come back. It had. Measured 2026-09-19 on the reference SH10RT, which
        needed about four minutes.

        So: send once, then watch. `Starting` is progress and resets nothing;
        only a state that is still *stopped* after `RESTART_RESEND_AFTER`
        earns another command, in case the first was lost rather than slow.
        """
        if await self._write(START_WORD_PROBE, START_WORD) is not None:
            _LOGGER.warning("control test: the start command itself was refused")
        started = self.clock.monotonic()
        last_sent = started
        seen_starting = False

        while self.clock.monotonic() - started < RESTART_RUNNING_DEADLINE:
            word = await self._running_word()
            if is_running(word):
                self.snapshot.stopped_at = None
                return True
            if is_starting(word):
                # Taken and working on it. Never re-send into this.
                seen_starting = True
                last_sent = self.clock.monotonic()
            elif (
                word is not None
                and word in RUNNING_STATES_STOPPED
                and self.clock.monotonic() - last_sent > RESTART_RESEND_AFTER
            ):
                _LOGGER.warning(
                    "control test: still stopped after %.0fs, sending start again",
                    RESTART_RESEND_AFTER,
                )
                await self._write(START_WORD_PROBE, START_WORD)
                last_sent = self.clock.monotonic()
            await self.clock.sleep(RESTART_POLL)

        _LOGGER.error(
            "control test: the inverter has not reported a running state after %.0fs%s",
            RESTART_RUNNING_DEADLINE,
            " -- it was still starting, so it is most likely still booting"
            if seen_starting
            else "",
        )
        self._worst(5)
        return False

    async def _await_generation(self) -> tuple[float | None, int]:
        """Wait until the inverter is producing again, and time it.

        Its own loop rather than another `_await_state`, because the two read
        different components: the running state is in `realtime_input` and the
        DC power is in `fast_input`. Polling one while asking about the other
        reads whatever was last refreshed, which would have timed how long the
        stale value took to be believed.
        """
        started = self.clock.monotonic()
        refused = 0
        while self.clock.monotonic() - started < RESTART_GENERATING_DEADLINE:
            try:
                await self.inverter.component("fast_input").async_update()
            except (ModbusError, TimeoutError, OSError):
                refused += 1
            else:
                power = self._value("total_dc_power")
                if power:
                    return self.clock.monotonic() - started, refused
            await self.clock.sleep(RESTART_POLL)
        return None, refused

    async def _restart(self) -> RestartResult:
        """Stop the inverter, start it again, and time all three transitions.

        Every number this returns is one the project has never had. The recovery
        time after a Modbus stop is undocumented upstream and unmeasured here;
        the only figure anywhere in the repository is the five minutes the FAQ
        gives for a physical cold boot, which is a different thing done a
        different way.
        """
        before = dict(self.snapshot.values)
        self.snapshot.stopped_at = self.clock.monotonic()
        if self._on_snapshot is not None:
            await self._on_snapshot(self.snapshot)

        self._step("stopping the inverter")
        if (failure := await self._write(START_WORD_PROBE, STOP_WORD)) is not None:
            self.snapshot.stopped_at = None
            return RestartResult(
                None, None, None, None, 0, None, SKIPPED, f"the stop {failure}"
            )

        stopped, word, refused = await self._await_state(
            RESTART_STOP_DEADLINE, lambda value: value in RUNNING_STATES_STOPPED
        )
        await self.clock.sleep(RESTART_DWELL)

        self._step("starting the inverter")
        running_from = self.clock.monotonic()
        started = await self.async_ensure_running()
        running = self.clock.monotonic() - running_from if started else None
        if not started:
            return RestartResult(
                stopped,
                None,
                None,
                word,
                refused,
                None,
                DROPPED,
                "the inverter did not come back; run --start-only",
            )

        generating, more_refused = await self._await_generation()
        await self._refresh("fast_holding")
        # Compared explicitly against None rather than for truth. Half of these
        # registers legitimately hold zero, and `value or default` treats a
        # restored 0 % as a missing reading -- which reported a perfectly
        # preserved set of settings as lost.
        survived = True
        for name, value in before.items():
            now = self._value(name)
            if now is None:
                continue
            if not math.isclose(float(now), float(value), rel_tol=1e-6, abs_tol=1e-6):
                survived = False
                break
        return RestartResult(
            stopped_after=stopped,
            running_after=running,
            generating_after=generating,
            stop_word_seen=word,
            polls_refused_connection=refused + more_refused,
            settings_survived=survived,
            verdict=CONFIRMED if stopped is not None else INCONCLUSIVE,
            detail=None if stopped is not None else "it never reported a stopped state",
        )

    # -- the run -------------------------------------------------------------

    def _count_steps(self) -> int:
        """Count this run's progress units. See `planned_steps`."""
        return planned_steps(self.options)

    async def _shielded(self, coro: Awaitable[Any]) -> Any:
        """Await something that must finish even if this run is being cancelled.

        Home Assistant cancels a background task when the entry unloads or the
        instance shuts down, and a restore interrupted halfway is the one
        outcome this module exists to prevent. The inner work runs as its own
        task so a cancellation delivered here does not reach it; this end
        absorbs a bounded number of cancellations while it finishes.
        """
        task = asyncio.ensure_future(coro)
        for _attempt in range(3):
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done():
                    raise
                _LOGGER.warning("control test: cancelled, but the restore continues")
        return await task

    async def async_run(self) -> Outcome:
        """Run the whole procedure and put everything back, whatever happens."""
        self._plan_budget()
        self._total = self._count_steps()
        probes: list[ProbeResult] = []
        effects: list[EffectResult] = []
        restores: list[RestoreResult] = []
        restart: RestartResult | None = None

        try:
            await self._preflight()
            if not self.options.restart_only:
                probes = await self._readback()
                effects = await self._effects()
        except Guard as guard:
            self._worst(guard.code)
            self.conditions["refused"] = str(guard)
            _LOGGER.warning("control test refused to run: %s", guard)
        except (ModbusError, TimeoutError, OSError) as err:
            self._worst(1)
            self.conditions["failed"] = f"{type(err).__name__}: {err}"
            _LOGGER.warning("control test stopped: %s", err)
        finally:
            if self.snapshot.values:
                restores = await self._shielded(self.async_restore())

        if (
            self.options.restart
            and self.snapshot.values
            and "refused" not in self.conditions
        ):
            restart = await self._restart()
        elif not self.options.restart and "refused" not in self.conditions:
            # Said out loud rather than left as a blank section. "What this run
            # could not establish" is generated from every skip, and a restart
            # that nobody asked for is a skip like any other -- a reader
            # otherwise cannot tell it from one the tool decided against.
            self._note(
                f"no restart: {USER_DECLINED}, so the recovery time on this "
                "model is not in this report"
            )

        if self.snapshot.unreadable:
            self._note(
                "not every control could be read before the run, so "
                f"{len(self.snapshot.unreadable)} of them were never written"
            )
        if self.options.restart_only:
            self._note(
                "only the restart was measured: nothing was written to any control, "
                "so this run establishes nothing about their scales"
            )
        if self.options.simulated:
            self._note(
                "this run was made against a simulator, which stores raw words with "
                "no scale of its own -- no measurement in it is evidence about hardware"
            )
        self.conditions["simulated"] = self.options.simulated
        self.conditions["dry_run"] = self.options.dry_run
        return Outcome(
            code=self.code,
            probes=tuple(probes),
            effects=tuple(effects),
            restores=tuple(restores),
            restart=restart,
            conditions=dict(self.conditions),
            unestablished=tuple(self.unestablished),
        )


def planned_steps(options: Options) -> int:
    """Count the progress units a run will report, before any are spent.

    Counted up front because a bar whose total grows halfway through is worse
    than no bar at all -- which `fingerprint.async_build` already learned when
    the register dump turned out to be two thirds of a survey.

    Part of it is necessarily an estimate: how many controls a device turns out
    to have is not known until the preflight has read it. So the count is
    deliberately generous and `_step` clamps the fraction at one, which makes a
    bar that may finish early and never one that overflows.

    A caller sharing one bar between this and something else needs the number
    without building a runner, which is why it is a function.
    """
    # Two opening steps, one per probe, one more for each probe that gets a
    # second point a decade away, and one per behavioural check: forced charge,
    # forced discharge, the charge ceiling and the export limit.
    steps = 2 + len(PROBES) + len(ControlTest.TWO_POINT) + 4
    if options.restart:
        steps += 2
    return steps


def document(outcome: Outcome) -> dict[str, Any]:
    """Return the publishable block, which carries no serial and no host.

    Anonymous by construction rather than by redaction, which is the shape
    `collect._block_document` established: what goes in is register numbers,
    the values this run chose, the words that came back and the words that were
    expected. None of that identifies an installation, so there is nothing here
    for a filter to miss.

    The conditions are the exception worth naming: they carry a state of charge
    and a PV reading, which is a household's afternoon. They are already what a
    fingerprint publishes in its readings block, knowingly and with the address
    already gone, and a behavioural verdict cannot be read without them.
    """
    return {
        "schema": BLOCK_SCHEMA,
        "outcome": outcome.code,
        "outcome_means": CODES[outcome.code],
        "conditions": outcome.conditions,
        "readback": [row._asdict() for row in outcome.probes],
        "effects": [row._asdict() for row in outcome.effects],
        "restored": [row._asdict() for row in outcome.restores],
        "restart": outcome.restart._asdict() if outcome.restart else None,
        "not_established": list(outcome.unestablished),
    }


#: The start/stop register, wearing a `Probe` so the same write helper covers it.
#: Not in `PROBES` and not in `WRITABLE_FIELDS`: it is hand-written in
#: `components.InverterControl` because nothing reads it, and it is the one
#: register in the map that turns the inverter off.
START_WORD_PROBE = Probe(
    field="start_stop",
    component="control",
    spec_register=13000,
    spec_units_per_count=1,
    unit="",
    exact=(STOP_WORD, START_WORD),
)
