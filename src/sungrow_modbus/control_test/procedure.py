"""What the control test is: its budgets, probes, verdicts and results.

Everything here is data or a pure function. The steps that read and write
live beside it, one module per phase, and `engine.ControlTest` puts them
together; the package docstring says what the procedure is for.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
import math
import time
from typing import Any, NamedTuple, Protocol

from ..inverter.capabilities import Capability
from ..inverter.derived import RUNNING_STATES

#: Bumped when the shape of the published `control_test` block changes, not
#: when a driver does. Carried into the block so a reader of an old document
#: knows which fields to expect.
#:
#: 2 writes 13074 at the factor `export_scale` measured on this device, and
#: says so in `conditions.export_write_scale`. A block at 1 wrote it divided
#: by ten everywhere, so its 13074 row from a 1:1 firmware is a refusal of a
#: tenth of the probe value, not a finding about the register.
BLOCK_SCHEMA = 2

# -- budgets -----------------------------------------------------------------
#
# Ten minutes, spent deliberately. The phases below add to 480 rather than to
# 600, and the 120 seconds of slack is not an oversight: a phase budgeted to
# the cap is a phase that kills the run on a slow link and loses the findings
# it already had, which is the same reasoning as `blocks.NARROW_BUDGET`.
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
PV_CUT_BUDGET = 180.0
"""Added to the behavioural phase only when the run may cut PV: a window
before, one during and one after, the ramp down before the second
(`PV_CUT_SETTLE`) and the MPPT search before the third (`PV_RECOVERY`)."""

# -- effect statistics -------------------------------------------------------
#
# Every threshold here exists because the input is the sky. See `_bracket`.

SAMPLE_INTERVAL = 2.0
"""Seconds between samples inside a window. Faster than any coordinator tier."""

WINDOW = 20.0
"""Seconds per window, so ten samples. A median of ten survives four outliers."""

SETTLE = 8.0
"""Seconds discarded after a write, before the window that measures it."""

PV_CUT_SETTLE = 35.0
"""Seconds discarded after `0xAA`, before the window that measures the cut.

The cut is a ramp, not a step. On fwitten's SH10RT-V112 (B001.V000.P023,
2026-10-29) DC power held for 6 s after the write and reached 0 W 20 s after
it. `SETTLE` put the window on the ramp: a median of 259 W against a 700 W
house, reported as nothing measurable. Twenty seconds plus margin for a
slower ramp at higher power."""

PV_RECOVERY = 75.0
"""Seconds discarded after PV is allowed again, before the window after.

The owner who found register 31211 measured PV back 30 to 60 s after `0x55`:
the inverter searches for the maximum power point again from scratch. A
`SETTLE` there would measure the search and call it drift."""

DRIFT_ABS_W = 150.0
DRIFT_FRACTION = 0.15
STABLE_MAD_W = 200.0
#: The timed windows (`Options.charge_window`, `Options.discharge_window`).
#: The inverter judges a window by its own clock, read from holding 5000-5005,
#: and a schedule is not acted on the instant it is written, so the window is
#: wide around now and the settle is long.
WINDOW_BUDGET = 300.0
WINDOW_SETTLE = 60.0
WINDOW_RECOVERY = 60.0
CHARGE_WINDOW_BEFORE = 5
"""Minutes the charging window starts before the inverter's now."""
CHARGE_WINDOW_AFTER = 20
"""Minutes it ends after: longer than the check, so it never ends mid-way."""
CHARGE_WINDOW_SOC_STEP = 10
"""Percent above the battery's level the window's target is set, so it has
something to charge towards and stops soon after if the restore fails."""
WINDOW_START_W = 300.0
"""Charge power a window must add to count as having started one."""

EFFECT_FLOOR_W = 200.0
SIGNIFICANCE = 3.0

# -- restore -----------------------------------------------------------------

SNAPSHOT_PAUSE = 1.0
"""Seconds between attempts at reading a control's before-state. Three
attempts, because on a link somebody else is polling the first one can simply
miss -- and a control whose before-state is not read is struck off the plan
for the whole run."""

RESTORE_ATTEMPTS = 5
RESTORE_PAUSE = 2.0
"""Five attempts, two seconds apart, sized for a link that drops between any
two steps rather than for one that works: a link lost *during a restore* is
measured, and it left a register at a probe value."""

# -- restart -----------------------------------------------------------------

#: How long to wait for a stopped state, and for generation after the start.
#:
#: Both measured at seconds (a stop in about 2, generation within 20), and
#: both given five minutes anyway: a link that drops while the inverter
#: switches can cost several 10 s request timeouts in a row, and a deadline
#: that expires on a machine doing as it was told reports a fault that is not
#: there.
RESTART_STOP_DEADLINE = 300.0
RESTART_DWELL = 10.0

#: How long to allow between the start command and a running state.
#:
#: **Measured, not guessed.** The reference SH10RT reported a stopped state 2
#: seconds after the stop command and took about four minutes to come back --
#: roughly two of those sitting in `0x0020 Starting`.
#:
#: **Twice as long in the dark.** With no PV, fwitten's SH10RT-V112 took 381
#: seconds and gerd's SH8.0RT-V112 369, against 197 and 180 in daylight --
#: four start commands before the state moved. Ten minutes is about one and
#: a half times the slowest measured, because the cost of waiting too long is
#: a slow diagnostic where the cost of waiting too little is telling somebody
#: their inverter is dead while it boots.
RESTART_RUNNING_DEADLINE = 600.0
RESTART_GENERATING_DEADLINE = 300.0
RESTART_POLL = 2.0

#: Seconds between `on_wait` calls while a restart is being waited out, so a
#: terminal shows a run that is alive through minutes of nothing to report.
WAIT_TICK = 10.0

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
#: off, is wrong and would have this procedure refuse to run on a healthy
#: inverter behind a dongle, then mistake a working one for a stopped one
#: during a restart. A list derived from the labels cannot drift from them,
#: and a new code added to the map is classified the moment it is named.
STOPPED_WORDS = ("stop", "standby", "shutdown", "uninitialized")
RUNNING_WORDS = ("running", "off-grid charge")

#: A state that is neither, and the wait has to recognise it.
#:
#: `0x0020 Starting` contains neither "stop" nor "running", so without its own
#: set it falls between both and a wait cannot tell a booting inverter from a
#: silent one. The reference SH10RT sits in it for minutes after a start
#: command; a wait that does not know it re-sends the command into a machine
#: already booting and then reports that it never came back.
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

#: What a dry run's 0 means. Code 0's own sentence -- "every planned check
#: ran and every readback matched" -- is false for a run that wrote nothing,
#: and a dry run printed it. 0 stays the code, because "the plan resolved" is
#: the success a dry run exists to report.
DRY_RUN_MEANS = "dry run: the plan resolved, and nothing was written"

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

    The bounds mirror `scripts/generate/tables/writes.py` exactly, which a test asserts.
    That duplication is deliberate: the library cannot import a file from
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
    raw_only: bool = False
    """Written as a raw word to its register, never through the field. For
    registers the library maps read only -- outside Sungrow's document, so
    the integration offers no control for them -- which the run may still
    write with leave, and must always be able to put back."""
    leave: str | None = None
    """The `Options` flag a run needs before this register is snapshotted at
    all. A register nothing will write is not worth a read, and a snapshot
    of it is a restore of something never changed."""


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
    # Spec reg 33047, U16, **0.01 kW = 10 W per count**. The YAML's NOTE above
    # "Battery max charge power" says "scale=100" and its code says
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
    # This stays 1 even though most firmware writes the register in tens of
    # watts, and the distinction is the whole point of leg B.
    # `spec_units_per_count` describes what the register **contains**, which
    # is watts: 10000 back against a 10000 W maximum. The decade lives on the
    # write side alone, where a multiplying firmware scales the word before
    # storing it; the run writes at the factor `export_scale` measured, so a
    # right 900 W write leaves the raw word at 900 and this row reads
    # `matched`, and a wrong one leaves 9000 or 90 and reads `SCALED`. Setting
    # this to 10 to "agree with the write scale" would make the run green
    # against a library that had gone wrong -- the exact tautology the column
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
    # The same quantity as 33047/33048 and a decade away from them in units.
    # The note above this field in `scripts/generate/tables/writes.py` names
    # that as exactly what a hand-typed table gets wrong, which is why it gets
    # both a two-point slope and a behavioural check.
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
#: Register 31211, outside the specification (#554, #738): `0xAA` cuts PV,
#: `0x55` lets it run. An enumeration like the three above, written only by the
#: PV cut check and judged by what PV does, never by the readback walk.
PV_CUT = Probe(
    field="pv_generation_cut_raw",
    component="pv_generation_cut",
    spec_register=31211,
    spec_units_per_count=1,
    unit="",
    exact=(0x55, 0xAA),
    requires=Capability.PV_GENERATION_CUT,
)

#: The forced-charging schedule's registers the charge window check writes
#: (V1.1.16 33208-33214): the enable, the days, the first window and its
#: target. Counted in ones, so no scale question; snapshotted only with leave.
CHARGE_ENABLE = Probe(
    field="forced_charging_raw",
    component="forced_charging",
    spec_register=33208,
    spec_units_per_count=1,
    unit="",
    exact=(0x55, 0xAA),
    requires=Capability.FORCED_CHARGING,
    leave="charge_window",
)
CHARGE_WINDOW: tuple[Probe, ...] = (
    CHARGE_ENABLE,
    *(
        Probe(
            field=field,
            component="forced_charging",
            spec_register=register,
            spec_units_per_count=1,
            unit=unit,
            requires=Capability.FORCED_CHARGING,
            leave="charge_window",
        )
        for field, register, unit in (
            ("forced_charging_days_raw", 33209, ""),
            ("forced_charging_start_1_hour", 33210, "h"),
            ("forced_charging_start_1_minute", 33211, "min"),
            ("forced_charging_end_1_hour", 33212, "h"),
            ("forced_charging_end_1_minute", 33213, "min"),
            ("forced_charging_target_soc_1", 33214, "%"),
        )
    ),
)

#: Both discharge schedules' windows (#785): weekday 33151-33158, weekend
#: 33180-33187, outside Sungrow's document and read only in the library, so
#: written and put back by raw word. The weekend enable (33179) is never
#: written: the check moves every window, whichever day's applies.
DISCHARGE_WINDOW: tuple[Probe, ...] = tuple(
    Probe(
        field=f"{day}_discharge_{part}_{number}_{unit}",
        component=f"discharge_{day}",
        spec_register=base + 4 * (number - 1) + offset,
        spec_units_per_count=1,
        unit="h" if unit == "hour" else "min",
        requires=Capability.DISCHARGE_SCHEDULE,
        raw_only=True,
        leave="discharge_window",
    )
    for day, base in (("weekday", 33151), ("weekend", 33180))
    for number in (1, 2)
    for offset, (part, unit) in enumerate(
        (("start", "hour"), ("start", "minute"), ("end", "hour"), ("end", "minute"))
    )
)

#: Every enumeration the run snapshots, restores and never walks.
ENUMERATIONS: tuple[Probe, ...] = (
    EMS_MODE,
    FORCED_CMD,
    EXPORT_MODE,
    PV_CUT,
    *CHARGE_WINDOW,
    *DISCHARGE_WINDOW,
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
#: A test requires every name in `scripts/generate/tables/writes.py`'s writable set to
#: be either in `PROBES` or in here, so a control added to the integration cannot
#: quietly escape the procedure -- it fails the suite until somebody decides which of
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
    "pv_generation_cut_raw": (
        "a mode flag with no scale to get wrong, written only by the PV cut "
        "check, which judges it by what PV does"
    ),
    # The forced-charging schedule (V1.1.16 33208-33219). Every register in it
    # counts in ones, hours, minutes or whole percent, so there is no scale
    # for a readback to catch; and a window written into it can start the
    # battery charging from the grid at the time it names.
    **dict.fromkeys(
        (
            "forced_charging_raw",
            "forced_charging_days_raw",
            "forced_charging_target_soc_1",
            "forced_charging_target_soc_2",
            *(
                f"forced_charging_{part}_{window}_{unit}"
                for window in (1, 2)
                for part in ("start", "end")
                for unit in ("hour", "minute")
            ),
        ),
        "part of the forced-charging schedule: counted in ones with no scale to "
        "get wrong; written only by the charge window check, with leave, "
        "because a window written into it can charge from the grid",
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

    The recovery time after a Modbus stop is undocumented upstream, and the
    five minutes the FAQ gives is for a physical cold boot, a different thing.
    Each run adds one more model, firmware and time of day to the measurements
    the restart deadlines above are sized from.
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

    cut_pv: bool = False
    """Cut PV generation through register 31211 for about a minute.

    Off by default because it is the one check that takes generation away on
    purpose -- briefly, and where the register answers at all. It is what
    `capabilities.CONFIRMED_ON_FIRMWARE` is filled from: a write judged by
    what PV does, which no readback can stand in for."""

    charge_window: bool = False
    """Write a forced-charging window around the inverter's own clock and
    watch the battery start charging, then switch it off again.

    Off by default because it is a charge the house did not ask for, and with
    no sun it comes from the grid: a minute or two of it, towards a target a
    few percent above the battery's level. The window, target, days and enable
    are put back to their snapshot words afterwards, every one checked."""

    discharge_window: bool = False
    """Move both discharge windows, weekday and weekend, away from now and
    watch the battery stop discharging, then put them back.

    Off by default because the house imports from the grid while the battery
    is held. The registers are outside Sungrow's document, so this is the
    watched write that would let the integration offer them as controls."""

    simulated: bool = False
    """Stamp the result as evidence about nothing. A simulator stores raw words
    with no scale semantics, so legs A and B agree there by construction."""

    dry_run: bool = False
    """Resolve everything, write nothing, and report what would have happened."""

    restart_only: bool = False
    """Measure the stop and start, and nothing else.

    The readback and behavioural phases write a dozen registers between them,
    and none of that is needed to time a reboot. A house lending its inverter
    for that one measurement should not have to accept the rest as the price
    -- and fewer writes before deliberately stopping somebody's inverter is the
    safer order in any case.

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
#: charge at the old one is a worse intermediate state than any other. PV cut
#: comes straight after: it acts too, but by stopping, which costs only energy.
#: The forced-charging enable goes back with them, before its window, so a
#: half-restored schedule is one that is off.
RESTORE_FIRST = (FORCED_CMD.field, EMS_MODE.field, PV_CUT.field, CHARGE_ENABLE.field)
RESTORE_LAST = (EXPORT_MODE.field,)


def inverter_clock(words: Sequence[int]) -> datetime | None:
    """Decode holding 5000-5005, the inverter's own clock, or None.

    Year, month, day, hour, minute, second, local time. A window is judged by
    this clock, not by the machine running the test, so a window placed by the
    wrong one could miss now entirely. A word that makes no date is None.
    """
    if len(words) < 6:
        return None
    year, month, day, hour, minute, second = (int(word) for word in words[:6])
    try:
        return datetime(year, month, day, hour, minute, second)  # noqa: DTZ001
    except ValueError:
        return None


def window_around(
    now: datetime, before: int, after: int
) -> tuple[int, int, int, int] | None:
    """Return a window from `before` minutes before now to `after` after it.

    As (start hour, start minute, end hour, end minute), or None where it
    would cross midnight: a schedule window is one day's, and which way a
    wrapping one is read is not known.
    """
    minute = now.hour * 60 + now.minute
    start, end = minute - before, minute + after
    if start < 0 or end >= 24 * 60:
        return None
    return (*divmod(start, 60), *divmod(end, 60))


def window_away(now: datetime) -> tuple[int, int, int, int]:
    """Return a one-hour window that cannot contain now, far from it.

    Late in the evening for a morning run and early in the morning for an
    afternoon one, so a window that is still in place when somebody looks is
    plainly not the owner's.
    """
    return (22, 0, 23, 0) if now.hour < 12 else (1, 0, 2, 0)


def restore_order(fields: Iterable[str]) -> tuple[str, ...]:
    """Return the fields to restore, in the order it is safe to restore them.

    The state-of-charge pair is the part that has to be computed rather than
    fixed. The inverter enforces `min < max`, so whichever direction the pair
    is moving decides which half must move first -- restore them in the wrong
    order and the device refuses one of the two writes, leaving the house with
    exactly one of the run's values still in place.
    """
    remaining = list(fields)
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

#: What both neighbours of a stop must clear for the stop to stand on its own.
#:
#: A stop is judged by its bracket, not by drift: a window at zero between two
#: windows of real power is the setting's doing however far the sky moved the
#: two apart. A cloud dims PV; it does not take 2 kW to 0 W ±0 and give it back
#: on cue. At gerd's SH8.0RT-V112 (B001.V000.P022, 2026-10-30) two cuts read
#: 2066 -> 0 -> 2516 W and 3063 -> 0 -> 2201 W, and the drift gate called both
#: inconclusive. The same 500 W as `PV_CUT_MIN_W`, for the same reason.
STOP_BRACKET_W = 500.0

#: What the behavioural checks command, in watts, for the forced charge, the
#: forced discharge and the export cap alike.
#:
#: **Chosen, not derived.** A figure derived from each house's own hardware
#: walks up to the pack's ceiling once earlier probes have spent the decade
#: window's values -- a 5800 W forced charge against a 5883 W pack. A number
#: that has to be read against three other functions to know what it will be
#: is a number nobody checks; this one is legible from here.
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
#: to whatever the limit has become: measured at bar12, 3158 W asked and
#: 3150 W accepted, which without headroom and `CLAMP_TOLERANCE` abandons the
#: whole export check over 8 W.
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

#: How far above the house's load a manufactured export aims, in `MIN_EXPORT_W`.
FORCE_EXPORT_MARGIN = 1.5


def export_cap() -> float:
    """Return the cap to ask for, which is simply `FORCED_EFFECT_W`.

    Not a fraction of the current export. The write scale of 13074 is measured
    per device by `export_scale` and written at that factor, so the cap on the
    wire is the cap in reality, and a fraction small enough to stay binding
    under a decade error would curtail every honest house that much harder on
    every run.

    What leg C can still show: a write that lands a decade *small* -- 125 W
    where 1250 was asked -- binds harder and reads `EFFECT_SCALED`. A write
    that lands a decade *large* binds on nothing and reads `NO_EFFECT`,
    indistinguishable from an ignored write; leg B sees that from the raw word,
    and `tests/test_writes.py` fails on the library's half of it at commit time.
    """
    return FORCED_EFFECT_W


MIN_PV_W = 200.0

#: What the PV cut check needs to start from, and what it writes.
#:
#: Higher than `MIN_PV_W` because the answer is a stop: from 500 W a fall to
#: under `STOPPED_W` is two and a half times the steadiest window allowed, so
#: a cloud cannot fake it.
PV_CUT_MIN_W = 500.0
PV_CUT_ON = 0xAA
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


#: The start/stop register, wearing a `Probe` so the same write helper covers it.
#: Not in `PROBES` and not in `writes.WRITABLE_FIELDS`: it is hand-written in
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
