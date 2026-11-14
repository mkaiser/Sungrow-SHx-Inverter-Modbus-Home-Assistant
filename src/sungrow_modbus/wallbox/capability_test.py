"""The wallbox's capability test: write a setting, read it back, watch the car.

The inverter's capability test (`sungrow_modbus.capability_test`) asks whether a
write lands, at what scale, and what the inverter then does. This asks the
same of a wallbox, for the one setting whose scale is in dispute: the output
current, holding 21203. This project reads it as 0.1 A per count, discussion
#571 as 0.01 A. On a mains charger that is a factor of ten, the shape of
register 13074's error on the inverter.

**Nothing here is written for the wallbox until it has been measured**, and
nothing in `SungrowWallbox` writes: this module owns every write, through a
`WallboxPort` the driver supplies, so a wallbox control can only exist after a
run like this has settled its scale.

**What keeps it safe, in the order it matters:**

* *Only on a wallbox no inverter manages* (`Options.standalone`). Under a
  hybrid inverter's energy management the inverter drives the output current
  and overwrites a write within seconds; the charge is controlled through the
  inverter's block (`sungrow_modbus.hybrid_inverter.ev_charger`) instead.
  A setting that moves between two reads with nothing written is refused too.
* *Never a disable, never under 6 A, never 0.* At gerd's on 2026-11-13 a
  disable ended a charge the enable written back did not resume, and 5 A and
  0 left the wallbox suspended. `enable` and `below_minimum` now only record
  that they were not run.
* *The word written is safe under every candidate scale.* A count of 60 is
  6.0 A or 0.6 A; 80 is 8.0 A or 0.8 A; 100 is 10.0 A or 1.0 A. The wrong
  reading can only offer *less* than meant, never ten times more. `max_amps`
  caps the highest step and defaults to 10 A, far below a 32 A rating.
* *A snapshot is flushed before the first write* (`on_snapshot`); without one
  nothing is written. "No snapshot file for a day means no writes that day"
  is the driver's rule; this refuses to start without the means to keep it.
* *Writes need leave.* `Options.leave` defaults to False, which is a dry run.
* *The restore is never budgeted, never deadlined and never skipped.* It
  writes the snapshot's raw word, checks it by a raw read on a fresh session
  where the port has one, tries again, and an unrestored register is code 5,
  the one code that means a house is left changed.
* *The session is kept alive.* A wallbox drops a session after sixty seconds
  without Modbus traffic and applies its fallback current, so every wait here
  is a loop of reads.

**Three legs, as on the inverter**, with the wallbox's own differences:

* A, plumbing: the library's own decode of a read on the same session.
* B, scale: the raw word, read on a *fresh* session, because a holding read
  straight after a write in the same TLS session was measured to answer with
  another register's value. Against the word written; the two hypotheses are
  typed here by hand and never read from `field.scale`.
* C, behaviour: what the car draws, against what was offered. Only with a car
  charging. Without one A and B still run and the run says, as code 3, that
  the scale was not settled.

Nothing here talks to Home Assistant, opens a file or prints.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
import logging
import statistics
from typing import Any, NamedTuple, Protocol

from modbus_connection import ModbusError

from ..capability_test.procedure import Clock, RealClock
from .discovery import MODEL_NAME, model_name
from .registers import CHARGING_STATUS, WallboxLive, WallboxRatings, WallboxSettings

_LOGGER = logging.getLogger(__name__)

#: What a lost link looks like. A refusal is `ModbusError`; the rest says nothing
#: about the register, only about the afternoon.
_LOST = (ModbusError, TimeoutError, OSError)

# -- what is written, and what it is compared with ----------------------------

#: The two readings of the output current setting, in amperes per count. Typed
#: by hand: the first is this project's measurement of the setting beside the
#: rated current, the second is discussion #571's. Never `field.scale`.
SCALE_THIS_PROJECT = 0.1
SCALE_DISCUSSION_571 = 0.01

#: The currents to offer, in amperes under the first reading, lowest first.
#: Under the second reading each is a tenth of that, so none can overshoot.
PLAN_AMPS = (6.0, 8.0, 10.0)

#: The highest current a run may offer unless told otherwise.
DEFAULT_MAX_AMPS = 10.0

#: A pilot signal below this offers a car nothing (IEC 61851). A car that was
#: charging and stops when 6 A or more is offered, or draws nothing when the
#: setting is read as 0.01 A per count, is the signal this is looking for.
MIN_CURRENT_A = 6.0

#: How far the car's draw may sit from what was offered and still count as
#: following it.
TOLERANCE_A = 1.5

SETTLE_SECONDS = 25.0
SAMPLE_INTERVAL = 5.0
SAMPLES = 3
STATE_TIMEOUT = 60.0

RESTORE_ATTEMPTS = 5
RESTORE_PAUSE = 3.0

#: The start/stop register's words, by the library's reading: 0 starts and 1
#: stops. Used only when the register reads 0 while a car is charging, which
#: is the only reading that makes it a state.
START_WORD = 0
STOP_WORD = 1

CHARGING = 3

#: The charge point's enable register, holding 21211: 1 enabled, 0 disabled.
#: The opposite polarity to the start/stop register beside it.
ENABLED_WORD = 1
DISABLED_WORD = 0
DISABLED_STATUS = 8

#: The phase setting's two words (0 three phase, 1 single phase), and the
#: statuses in which nothing is flowing, so a contactor is not opened under
#: load: idle, standby, completed and disabled. Never while charging.
PHASE_WORDS = (0, 1)
IDLE_STATUSES = (1, 2, 6, 8)

#: The full-range follow check steps by this much between 6 A and the cap.
FOLLOW_STEP_A = 2.0

#: How long a car has to follow a step, and how long a pause or a resume may take.
FOLLOW_TIMEOUT = 60.0

#: An offer under the pilot minimum, for the below-minimum check. Under the
#: second reading of the scale it is 0.05 A: nothing a car could mistake.
BELOW_MINIMUM_A = 5.0

#: Why the run writes nothing to a wallbox not declared standalone.
MANAGED_REASON = (
    "a wallbox managed by an inverter ignores writes to its own registers: the "
    "inverter drives its output current and overwrites a write within seconds. "
    "Its charging is controlled through the inverter's wallbox block instead. "
    "Run this only on a wallbox no inverter manages (`standalone`)"
)

#: Why the enable check never disables. At gerd's on 2026-11-13 a disable
#: ended the charge, and the enable written back did not bring it back.
ENABLE_NEVER = (
    "the charge point is never disabled: a disable ended a charge that the "
    "enable written back did not resume (gerd, 2026-11-13)"
)

#: Why nothing under the pilot minimum is offered. 5 A and 0 left the wallbox
#: suspended until a current was written again (gerd, 2026-11-13; KevinD987).
BELOW_MINIMUM_NEVER = (
    "nothing under 6 A and never 0 is written: an offer under the minimum can "
    "leave the wallbox suspended until a current is written again"
)

#: The headroom the above-rating check offers over the rating.
ABOVE_RATING_A = 1.0

#: Every read stops for this long in the fallback check. The wallbox drops a
#: quiet session after sixty seconds; this leaves it fifteen to apply its
#: fallback current before the first look.
SILENCE_SECONDS = 75.0

#: A stop is seen when the status is not charging and the draw is under this.
STOPPED_DRAW_A = 1.0

# -- what a run can say --------------------------------------------------------

MATCHED = "matched"
MISMATCH = "the word read back is not the word written"
CONFIRMED = "the wallbox did as it was told"
DECADE = "the car stopped: the setting is read a decade too low"
INCONCLUSIVE = "could not tell"
SKIPPED = "skipped"
REFUSED = "refused"
DROPPED = "the link dropped"
CLAMPED = "clamped to the rating"
NOT_CLAMPED = "accepted above the rating, not clamped"

CODES = {
    0: "every planned check ran and every readback matched",
    1: "nothing ran -- could not read the wallbox",
    2: "this cannot run here -- wrong device, no snapshot to keep, or unsafe",
    3: "ran, but checks were skipped or inconclusive",
    4: "a scale finding: the setting is read a decade too low",
    5: "something was not restored",
}
DRY_RUN_MEANS = "dry run: the plan resolved, and nothing was written"
SEVERITY = (0, 3, 4, 1, 2, 5)


def _follows(offered: float) -> Callable[[Sample], bool]:
    """Return the test for a car that is charging at `offered`, within tolerance."""

    def test(sample: Sample) -> bool:
        return sample.status == CHARGING and abs(sample.draw_a - offered) <= TOLERANCE_A

    return test


def _mean(values: list[Any]) -> str:
    """Return the mean of some seconds as text, or a dash for none."""
    return f"{statistics.mean(values):.0f} s" if values else "-"


def _address(component: type[Any], name: str) -> int:
    """Return a field's protocol address from the library's own map."""
    address: int = component.declared_fields[name].address
    return address


OUTPUT_CURRENT = _address(WallboxSettings, "output_current_setting")
START_STOP = _address(WallboxSettings, "start_stop_raw")
ENABLED = _address(WallboxSettings, "charger_enabled_raw")
PHASE_SETPOINT = _address(WallboxSettings, "phase_mode_setpoint_raw")
PHASE_ACTUAL = _address(WallboxRatings, "phase_mode_raw")
MILEAGE = _address(WallboxSettings, "mileage_per_kwh")
RATED_CURRENT = _address(WallboxRatings, "rated_current")
PHASE_A_CURRENT = _address(WallboxLive, "phase_a_current")
PHASE_B_CURRENT = _address(WallboxLive, "phase_b_current")
PHASE_C_CURRENT = _address(WallboxLive, "phase_c_current")
CHARGING_POWER = _address(WallboxLive, "charging_power")
CHARGING_STATUS_ADDRESS = _address(WallboxLive, "charging_status_raw")
AVAILABLE_CURRENT = _address(WallboxLive, "available_current")


class WallboxPort(Protocol):
    """What the driver gives a run: reads, one write, and a fresh session."""

    #: Whether `read_fresh` really opens a new session. A port that cannot
    #: says False, and leg B is then not independent of the write.
    fresh: bool

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read words on the open session. Raises, never guesses."""

    async def read_fresh(self, space: str, address: int, count: int) -> list[int]:
        """Read words on a new session, so a stale answer cannot be given."""

    async def write(self, address: int, word: int) -> None:
        """Write one holding word. Raises `ModbusError` when refused."""


@dataclass(frozen=True)
class Options:
    """What a run has been given leave to do."""

    leave: bool = False
    """Write at all. False is a dry run: the plan is resolved and nothing is
    sent. The diagnosis's rule: a run with nobody at a terminal is a no."""

    max_amps: float = DEFAULT_MAX_AMPS
    """The highest current to offer, under the first reading of the scale."""

    start_stop: bool = False
    """Also stop and start the charge once. Off by default, because it is
    an interruption to a car."""

    enable: bool = False
    """Also disable the charge point and enable it again. Off by default; it
    stops a charge in progress, and is harmless on an idle wallbox."""

    phase: bool = False
    """Also switch the phase setting and back. Off by default, and refused
    unless nothing is flowing: a contactor does not open under load."""

    follow: bool = False
    """Step the offer from 6 A to the cap in 2 A steps and back down, timing
    how fast the car follows each. Needs a car charging."""

    below_minimum: bool = False
    """Offer 5 A, then 0, and see whether the wallbox refuses or the car
    pauses. Needs a car charging and `cap_explicit`."""

    above_rating: bool = False
    """Offer the rating plus 1 A, and see whether it is refused or clamped.
    Needs a car charging, `cap_explicit` and a cap of at least the rating."""

    phase_charging: bool = False
    """Switch the phase with a car charging, in the order evcc uses: stop,
    switch, start. The switch is written only once the stop is seen."""

    fallback: bool = False
    """Stop every read for 75 s and see what the car is given by the
    fallback. Needs a car charging and a cap no higher than the setting the
    house had."""

    mileage: bool = False
    """Write the mileage setting its own word: a no-op that shows the write
    path is open."""

    current: bool = True
    """Run the output current's own three steps (6, 8 and 10 A). Off once an
    earlier run has settled the scale, so a repeat does not offer them again."""

    cap_explicit: bool = False
    """Whether the owner chose `max_amps`. The checks that go beyond the
    default cap need it, so a default is never mistaken for consent."""

    standalone: bool = False
    """The owner says no inverter manages this wallbox. Without it nothing is
    written: a wallbox under an inverter's energy management has its output
    current driven by the inverter, which overwrites a write within seconds
    (gerd, 2026-11-14), and nothing on the wallbox alone tells the two apart."""


class Step(NamedTuple):
    """One thing the run did or declined to do, and what it found."""

    name: str
    verdict: str
    detail: str


class RestoreResult(NamedTuple):
    """One register put back, and whether it stayed back."""

    address: int
    original: int
    restored: bool
    attempts: int
    detail: str


class Outcome(NamedTuple):
    """Everything one run established, and what it could not."""

    code: int
    steps: tuple[Step, ...]
    restores: tuple[RestoreResult, ...]
    conditions: dict[str, Any]
    unestablished: tuple[str, ...]

    @property
    def not_restored(self) -> tuple[RestoreResult, ...]:
        """Anything the house is still carrying. Reported first, always."""
        return tuple(row for row in self.restores if not row.restored)


class Guard(Exception):
    """The run cannot proceed; carries the code it ends with."""

    def __init__(self, code: int, reason: str) -> None:
        """Say which code and why."""
        super().__init__(reason)
        self.code = code
        self.reason = reason


class Sample(NamedTuple):
    """The live registers at one moment."""

    status: int | None
    currents_a: tuple[float, float, float]
    power_w: int | None
    available_a: float | None

    @property
    def draw_a(self) -> float:
        """The highest phase current: what a single- or three-phase car draws."""
        return max(self.currents_a)


# -- the run --------------------------------------------------------------------


class WallboxCapabilityTest:
    """One run against one wallbox. Construct it, call `async_run`."""

    def __init__(
        self,
        port: WallboxPort,
        options: Options | None = None,
        *,
        clock: Clock | None = None,
        on_snapshot: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_step: Callable[[str], None] | None = None,
    ) -> None:
        """Bind a port; nothing is read or written until `async_run`."""
        self.port = port
        self.options = options or Options()
        self.clock: Clock = clock or RealClock()
        self._on_snapshot = on_snapshot
        self._on_step = on_step
        self.snapshot: dict[str, Any] = {"raw": {}, "touched": []}
        self.steps: list[Step] = []
        self.restores: list[RestoreResult] = []
        self.conditions: dict[str, Any] = {}
        self.unestablished: list[str] = []
        self.written: list[tuple[int, int]] = []
        self._codes: list[int] = [0]
        self._charging_at_start = False
        #: (offered A, available A, draw A) from every step that watched a car.
        self._pairs: list[tuple[float, float | None, float]] = []

    # -- helpers -----------------------------------------------------------

    def _step(self, label: str) -> None:
        if self._on_step is not None:
            self._on_step(label)

    def _worst(self, code: int) -> None:
        self._codes.append(code)

    @property
    def code(self) -> int:
        """The worst code so far, by `SEVERITY`."""
        return max(self._codes, key=SEVERITY.index)

    def _note(self, sentence: str) -> None:
        if sentence not in self.unestablished:
            self.unestablished.append(sentence)

    async def _read_one(self, space: str, address: int) -> int:
        return (await self.port.read(space, address, 1))[0]

    async def _sample(self) -> Sample:
        """Read the live registers; raises, because a lost link is not a zero."""
        span = CHARGING_POWER + 2 - PHASE_A_CURRENT
        block = await self.port.read("input", PHASE_A_CURRENT, span)
        currents = tuple(
            block[address - PHASE_A_CURRENT] * SCALE_THIS_PROJECT
            for address in (PHASE_A_CURRENT, PHASE_B_CURRENT, PHASE_C_CURRENT)
        )
        power = block[CHARGING_POWER - PHASE_A_CURRENT] | (
            block[CHARGING_POWER + 1 - PHASE_A_CURRENT] << 16
        )
        status = await self._read_one("input", CHARGING_STATUS_ADDRESS)
        available = await self._read_one("input", AVAILABLE_CURRENT)
        return Sample(
            status,
            (currents[0], currents[1], currents[2]),
            power,
            available * SCALE_THIS_PROJECT,
        )

    async def _touch(self, address: int) -> None:
        """Record that `address` is about to be written, and flush it first."""
        touched: list[int] = self.snapshot["touched"]
        if address in touched:
            return
        touched.append(address)
        if self._on_snapshot is not None:
            await self._on_snapshot(self.snapshot)

    async def _write(self, address: int, word: int) -> str | None:
        """Write one word. Returns a verdict on failure, None on success."""
        await self._touch(address)
        try:
            await self.port.write(address, word)
        except ModbusError as err:
            self.conditions.setdefault("refusals", {})[address] = (
                f"{type(err).__name__}: {err}"
            )
            return REFUSED
        except (TimeoutError, OSError) as err:
            self.conditions.setdefault("refusals", {})[address] = (
                f"{type(err).__name__}: {err}"
            )
            return DROPPED
        self.written.append((address, word))
        return None

    async def _wait(self, seconds: float) -> list[Sample]:
        """Wait, reading the live registers, so the session never goes quiet."""
        samples: list[Sample] = []
        end = self.clock.monotonic() + seconds
        while True:
            samples.append(await self._sample())
            if self.clock.monotonic() >= end:
                return samples
            await self.clock.sleep(SAMPLE_INTERVAL)

    # -- the run -----------------------------------------------------------

    async def async_run(self) -> Outcome:
        """Run the whole procedure and put everything back, whatever happens."""
        try:
            await self._preflight()
            if self.options.leave:
                if self.options.current:
                    await self._current_steps()
                if self.options.follow:
                    await self._follow()
                if self.options.below_minimum:
                    await self._below_minimum()
                if self.options.above_rating:
                    await self._above_rating()
                self._available_vs_setting()
                if self.options.start_stop:
                    await self._start_stop()
                if self.options.enable:
                    await self._enable()
                if self.options.phase:
                    await self._phase()
                if self.options.phase_charging:
                    await self._phase_charging()
                if self.options.mileage:
                    await self._mileage()
                if self.options.fallback:
                    await self._fallback()
            else:
                self.conditions["dry_run"] = DRY_RUN_MEANS
        except Guard as guard:
            self._worst(guard.code)
            self.conditions["guard"] = guard.reason
        except _LOST:
            _LOGGER.exception("wallbox capability test: lost the wallbox")
            self._worst(1 if not self.written else 3)
            self.conditions["guard"] = "the wallbox stopped answering"
        finally:
            await self._shielded(self._restore())
        return Outcome(
            self.code,
            tuple(self.steps),
            tuple(self.restores),
            self.conditions,
            tuple(self.unestablished),
        )

    async def _shielded(self, coro: Awaitable[None]) -> None:
        """Finish a restore even if this run is being cancelled."""
        task = asyncio.ensure_future(coro)
        for _attempt in range(3):
            try:
                await asyncio.shield(task)
                return
            except asyncio.CancelledError:
                if task.done():
                    raise
                _LOGGER.warning("wallbox capability test: cancelled, restore continues")
        await task

    # -- preflight ---------------------------------------------------------

    async def _preflight(self) -> None:
        self._step("identify the wallbox")
        try:
            words = await self.port.read(
                MODEL_NAME.space, MODEL_NAME.address, MODEL_NAME.length
            )
        except _LOST as err:
            raise Guard(1, f"could not read the model name: {err}") from err
        name = model_name(words)
        self.conditions["model"] = name
        if not name or not name.upper().startswith("AC"):
            raise Guard(2, f"{name!r} is not a Sungrow wallbox")

        self._step("snapshot")
        rated_word = await self._read_one("input", RATED_CURRENT)
        setting = await self._read_one("holding", OUTPUT_CURRENT)
        start_stop = await self._read_one("holding", START_STOP)
        sample = await self._sample()
        self.snapshot["raw"] = {OUTPUT_CURRENT: setting, START_STOP: start_stop}
        # The two settings a step may touch later. A failed read drops the
        # step rather than the run, because a lost read is not a refusal and
        # never write what cannot be put back.
        extra = [(ENABLED, "enabled"), (PHASE_SETPOINT, "phase")]
        if self.options.mileage:
            extra.append((MILEAGE, "mileage"))
        for address, name in extra:
            try:
                self.snapshot["raw"][address] = await self._read_one("holding", address)
            except _LOST as err:
                self.conditions.setdefault("unreadable", {})[name] = (
                    f"{type(err).__name__}: {err}"
                )
        self.conditions["enabled_word"] = self.snapshot["raw"].get(ENABLED)
        self.conditions["phase_word"] = self.snapshot["raw"].get(PHASE_SETPOINT)
        self.snapshot["taken_at"] = self.clock.monotonic()
        self.conditions.update(
            rated_a=rated_word * SCALE_THIS_PROJECT,
            setting_word=setting,
            start_stop_word=start_stop,
            status=CHARGING_STATUS.get(sample.status or 0, sample.status),
            draw_a=sample.draw_a,
            available_a=sample.available_a,
        )
        self._charging_at_start = sample.status == CHARGING

        # Something else writing the setting -- an inverter's energy management
        # ramps it every few seconds while a car charges -- shows as a second
        # read that differs from the first, with nothing written in between.
        again = await self._read_one("holding", OUTPUT_CURRENT)
        if again != setting:
            self.conditions["setting_moved"] = [setting, again]
        if self.options.leave and not self.options.standalone:
            raise Guard(2, MANAGED_REASON)
        if self.options.leave and again != setting:
            raise Guard(
                2,
                f"the output current setting moved from {setting} to {again} with "
                "nothing written: another controller drives it",
            )

        if self.options.leave:
            if self._on_snapshot is None:
                raise Guard(2, "writes need a snapshot callback to keep the snapshot")
            await self._on_snapshot(self.snapshot)
        if sample.status == 9:
            raise Guard(2, "the wallbox reports a fault")
        if self.options.max_amps <= 0:
            raise Guard(2, "max_amps must be positive")
        rating = round(rated_word * SCALE_THIS_PROJECT, 1)
        if rating > 0 and self.options.max_amps > rating:
            # The owner's cap is never above what the wallbox is rated for.
            self.options = replace(self.options, max_amps=rating)
            self.conditions["cap_limited_to_rating_a"] = rating

        # Measured idle at gerd's (2026-11-06): 0 with no car, where a charge
        # read 160. What a 0 means -- no limit set, or nothing offered -- is not
        # established, so it is not a value to restore after writing 6 A.
        if setting == 0 and self.options.leave:
            raise Guard(
                2,
                "the output current setting reads 0, whose meaning is not "
                "established: run with a car charging, when it holds a current",
            )
        rated_a = rated_word * SCALE_THIS_PROJECT
        first = setting * SCALE_THIS_PROJECT
        second = setting * SCALE_DISCUSSION_571
        if first > rated_a:
            # Above the rating under one reading. If the other reading puts it
            # inside the rating and above the pilot minimum, that is the finding
            # itself, reached without a single write.
            if MIN_CURRENT_A <= second <= rated_a:
                self.conditions["scale_before_writing"] = (
                    f"the setting word {setting} is {first:.1f} A at 0.1 A per count, "
                    f"above the {rated_a:.1f} A rating, and {second:.1f} A at 0.01"
                )
                raise Guard(4, "the setting reads as 0.01 A per count, not 0.1")
            raise Guard(
                2,
                f"the setting ({first} A under the first reading) is above the "
                f"rating ({rated_a} A) and fits neither reading: not understood",
            )
        # Before any write: a car already drawing more than the setting would
        # offer under the second reading cannot be reading it that way.
        if self._charging_at_start:
            if sample.draw_a > setting * SCALE_DISCUSSION_571 + TOLERANCE_A:
                self.conditions["scale_before_writing"] = (
                    "the car draws more than the setting would offer at 0.01 A "
                    "per count, so the setting is not read that way"
                )
            else:
                self._note("the car's draw does not separate the two readings")
        else:
            self._note(
                "no car is charging: only plumbing and the raw word can be checked, "
                "not what the wallbox does with the setting"
            )

    # -- the output current ------------------------------------------------

    def _plan(self) -> list[int]:
        """Return the words to write, lowest first, none above the cap."""
        return [
            round(amps / SCALE_THIS_PROJECT)
            for amps in PLAN_AMPS
            if amps <= self.options.max_amps
        ]

    async def _current_steps(self) -> None:
        results: list[str] = []
        for word in self._plan():
            self._step(f"offer {word * SCALE_THIS_PROJECT:.1f} A")
            step = await self._current_step(word)
            self.steps.append(step)
            results.append(step.verdict)
            if step.verdict in (REFUSED, DROPPED, MISMATCH, DECADE):
                break
        if not results:
            self._note("max_amps is below the lowest step: nothing was written")
            self._worst(3)
            return
        if DECADE in results:
            self._worst(4)
        elif any(v in (REFUSED, DROPPED, MISMATCH) for v in results):
            self._worst(3)
        elif CONFIRMED in results:
            return
        else:
            self._worst(3)
            if not self._charging_at_start:
                return
            self._note("what the car draws did not settle the scale")

    async def _current_step(self, word: int) -> Step:
        name = f"output current {word}"
        failure = await self._write(OUTPUT_CURRENT, word)
        if failure is not None:
            return Step(name, failure, self.conditions["refusals"][OUTPUT_CURRENT])

        if self.port.fresh:
            # Leg A: the same session, through the library's own decode.
            same = await self._read_one("holding", OUTPUT_CURRENT)
            # Leg B: the raw word on a fresh session.
            raw = (await self.port.read_fresh("holding", OUTPUT_CURRENT, 1))[0]
            if raw != word:
                return Step(
                    name,
                    MISMATCH,
                    f"wrote {word}; the same session read {same}, a fresh one {raw}",
                )
        else:
            # A read on the session that wrote answers another register's value
            # (a dongle always, a shared TLS session as measured), so neither
            # leg is evidence and only what the car does counts.
            self._note(
                "the port has no fresh session: the readback is not independent, "
                "only what the car does counts"
            )
            self._worst(3)

        if not self._charging_at_start:
            if not self.port.fresh:
                return Step(
                    name, INCONCLUSIVE, "no car charging: nothing to judge the write by"
                )
            return Step(name, MATCHED, "no car charging: behaviour not watched")

        # Leg C: what the car draws.
        samples = await self._wait(SETTLE_SECONDS)
        tail = samples[-SAMPLES:]
        draw = statistics.median(s.draw_a for s in tail)
        offered = word * SCALE_THIS_PROJECT
        charging = all(s.status == CHARGING for s in tail)
        self._pairs.append((offered, tail[-1].available_a, draw))
        if charging and abs(draw - offered) <= TOLERANCE_A:
            return Step(
                name, CONFIRMED, f"offered {offered:.1f} A, the car draws {draw:.1f} A"
            )
        if not charging and draw < MIN_CURRENT_A:
            return Step(
                name,
                DECADE,
                f"offered {offered:.1f} A at 0.1 A per count and the car stopped "
                f"({CHARGING_STATUS.get(tail[-1].status or 0, tail[-1].status)}), "
                "as if offered a tenth of that",
            )
        return Step(
            name,
            INCONCLUSIVE,
            f"offered {offered:.1f} A, the car draws {draw:.1f} A: it may limit itself",
        )

    # -- start and stop ----------------------------------------------------

    async def _start_stop(self) -> None:
        self._step("stop and start the charge")
        original = self.snapshot["raw"][START_STOP]
        if not self._charging_at_start:
            self.steps.append(Step("start/stop", SKIPPED, "no car is charging"))
            self._note("start and stop were not watched: no car was charging")
            self._worst(3)
            return
        if original != START_WORD:
            self.steps.append(
                Step(
                    "start/stop",
                    SKIPPED,
                    f"the register reads {original} while a car charges, so it is "
                    "not a state and its polarity is unknown",
                )
            )
            self._note("start/stop polarity could not be established safely")
            self._worst(3)
            return
        failure = await self._write(START_STOP, STOP_WORD)
        if failure is not None:
            self.steps.append(
                Step("stop", failure, self.conditions["refusals"][START_STOP])
            )
            self._worst(3)
            return
        stopped = await self._timed(lambda s: s.status != CHARGING, STATE_TIMEOUT)
        failure = await self._write(START_STOP, START_WORD)
        if failure is not None:
            self.steps.append(
                Step("start", failure, self.conditions["refusals"][START_STOP])
            )
            self._worst(3)
            return
        resumed = await self._timed(lambda s: s.status == CHARGING, STATE_TIMEOUT)
        self.conditions["start_stop_seconds"] = {"stop": stopped, "resume": resumed}
        if stopped is not None and resumed is not None:
            self.steps.append(
                Step(
                    "start/stop",
                    CONFIRMED,
                    f"stopped on 1 after {stopped:.0f} s, resumed on 0 after "
                    f"{resumed:.0f} s",
                )
            )
        else:
            self.steps.append(
                Step(
                    "start/stop",
                    INCONCLUSIVE,
                    f"stopped: {stopped is not None}, resumed: {resumed is not None}",
                )
            )
            self._worst(3)

    async def _until(self, condition: Callable[[Sample], bool], timeout: float) -> bool:
        """Poll the live registers until `condition` holds, or the time is up."""
        return await self._timed(condition, timeout) is not None

    async def _timed(
        self, condition: Callable[[Sample], bool], timeout: float
    ) -> float | None:
        """Seconds until `condition` held, or None if it did not in `timeout`.

        The resolution is the sample interval: a wallbox is looked at every
        five seconds so the session never goes quiet.
        """
        start = self.clock.monotonic()
        end = start + timeout
        while True:
            if condition(await self._sample()):
                return self.clock.monotonic() - start
            if self.clock.monotonic() >= end:
                return None
            await self.clock.sleep(SAMPLE_INTERVAL)

    async def _poll(self, check: Callable[[], Awaitable[bool]], timeout: float) -> bool:
        """Ask `check` every sample interval, so the session never goes quiet."""
        end = self.clock.monotonic() + timeout
        while self.clock.monotonic() < end:
            if await check():
                return True
            await self.clock.sleep(SAMPLE_INTERVAL)
        return False

    # -- enable and disable --------------------------------------------------

    def _skip(self, name: str, reason: str) -> None:
        self.steps.append(Step(name, SKIPPED, reason))
        self._note(f"{name}: {reason}")
        self._worst(3)

    async def _enable(self) -> None:
        """Never disable the charge point; say so, and write nothing."""
        self._step("disable and enable the charge point")
        self._skip("enable", ENABLE_NEVER)

    # -- the phase setting ----------------------------------------------------

    async def _phase(self) -> None:
        """Switch the phase setting and see the wallbox follow, only when idle."""
        self._step("switch the phase setting")
        original = self.snapshot["raw"].get(PHASE_SETPOINT)
        if original not in PHASE_WORDS:
            self._skip(
                "phase", f"the setting reads {original!r}, not one of {PHASE_WORDS}"
            )
            return
        sample = await self._sample()
        if sample.status not in IDLE_STATUSES:
            self._skip(
                "phase",
                f"status {CHARGING_STATUS.get(sample.status or 0, sample.status)}: a "
                "contactor is not opened with a car charging or the pilot active",
            )
            return
        before = await self._read_one("input", PHASE_ACTUAL)
        target = PHASE_WORDS[1 - PHASE_WORDS.index(original)]
        failure = await self._write(PHASE_SETPOINT, target)
        if failure is not None:
            self.steps.append(
                Step("phase", failure, self.conditions["refusals"][PHASE_SETPOINT])
            )
            self._worst(3)
            return

        async def followed() -> bool:
            return await self._read_one("input", PHASE_ACTUAL) == target

        moved = await self._poll(followed, STATE_TIMEOUT)
        if moved:
            self.steps.append(
                Step(
                    "phase",
                    CONFIRMED,
                    f"setting {original} to {target}; the wallbox followed",
                )
            )
        else:
            self.steps.append(
                Step(
                    "phase",
                    INCONCLUSIVE,
                    f"setting {original} to {target}; the actual mode stayed {before}: "
                    "a single-phase unit, or it needs longer",
                )
            )
            self._worst(3)

    # -- what a car does across the whole range -------------------------------

    def _needs_car(self, name: str) -> bool:
        """Skip `name` unless a car was charging at the start; say whether to go on."""
        if self._charging_at_start:
            return True
        self._skip(name, "no car is charging")
        return False

    def _needs_cap(self, name: str) -> bool:
        """Skip `name` unless the owner chose the cap; say whether to go on."""
        if self.options.cap_explicit:
            return True
        self._skip(name, "the owner's cap was not set explicitly")
        return False

    async def _follow(self) -> None:
        """Step the offer up to the cap and back, and time how the car follows."""
        self._step("follow the offer across the range")
        if not self._needs_car("current follow"):
            return
        ups: list[float] = []
        amps = MIN_CURRENT_A
        while amps <= self.options.max_amps + 1e-9:
            ups.append(amps)
            amps += FOLLOW_STEP_A
        if not ups:
            self._skip("current follow", "the cap is below 6 A: nothing to step")
            return
        path = [(a, "up") for a in ups] + [(a, "down") for a in reversed(ups[:-1])]
        rows: list[dict[str, Any]] = []
        self.conditions["follow"] = rows
        previous: float | None = None
        ceiling: float | None = None
        for amps, direction in path:
            self._step(f"offer {amps:.1f} A, {direction}")
            failure = await self._write(
                OUTPUT_CURRENT, round(amps / SCALE_THIS_PROJECT)
            )
            if failure is not None:
                self.steps.append(
                    Step(
                        "current follow",
                        failure,
                        self.conditions["refusals"][OUTPUT_CURRENT],
                    )
                )
                self._worst(3)
                return
            seconds = await self._timed(_follows(amps), FOLLOW_TIMEOUT)
            sample = await self._sample()
            # A car that stops following on the way up has met its own limit;
            # a step above that limit, either way, is not the wallbox's doing.
            beyond = sample.draw_a < amps - TOLERANCE_A
            limited = (
                seconds is None
                and sample.status == CHARGING
                and beyond
                and (
                    (
                        direction == "up"
                        and previous is not None
                        and sample.draw_a >= previous - 0.5
                    )
                    or (ceiling is not None and abs(sample.draw_a - ceiling) <= 0.5)
                )
            )
            if limited and ceiling is None:
                ceiling = sample.draw_a
            stopped = sample.status != CHARGING and sample.draw_a < MIN_CURRENT_A
            rows.append(
                {
                    "offered_a": amps,
                    "direction": direction,
                    "seconds": seconds,
                    "draw_a": sample.draw_a,
                    "available_a": sample.available_a,
                    "limited": limited,
                    "stopped": stopped,
                }
            )
            if seconds is not None or limited:
                self._pairs.append((amps, sample.available_a, sample.draw_a))
            if stopped:
                break
            previous = sample.draw_a
        if any(row["stopped"] for row in rows):
            self.steps.append(
                Step(
                    "current follow",
                    DECADE,
                    f"the car stopped when offered {rows[-1]['offered_a']:.1f} A at "
                    "0.1 A per count, as if offered a tenth of that",
                )
            )
            self._worst(4)
            return
        missed = [r for r in rows if r["seconds"] is None and not r["limited"]]
        followed = [r for r in rows if r["seconds"] is not None]
        if missed or not followed:
            detail = (
                "the draw did not follow at "
                + ", ".join(f"{r['offered_a']:.0f} A {r['direction']}" for r in missed)
                if missed
                else "no step was followed"
            )
            self.steps.append(Step("current follow", INCONCLUSIVE, detail))
            self._worst(3)
            return
        up = [r["seconds"] for r in followed if r["direction"] == "up"]
        down = [r["seconds"] for r in followed if r["direction"] == "down"]
        limit = [r["draw_a"] for r in rows if r["limited"]]
        detail = (
            f"the draw followed {len(followed)} steps from {path[0][0]:.0f} A to "
            f"{max(a for a, _d in path):.0f} A; up {_mean(up)}, down {_mean(down)}"
        )
        if limit:
            detail += f"; the car stopped following at {limit[0]:.1f} A"
        self.steps.append(Step("current follow", CONFIRMED, detail))

    async def _below_minimum(self) -> None:
        """Never offer under the pilot minimum; say so, and write nothing."""
        self._step("offer under the pilot minimum")
        self._skip("below minimum", BELOW_MINIMUM_NEVER)

    async def _above_rating(self) -> None:
        """Offer the rating plus 1 A: refused, or clamped, or neither."""
        self._step("offer above the rating")
        if not self._needs_car("above rating") or not self._needs_cap("above rating"):
            return
        rated = float(self.conditions.get("rated_a") or 0.0)
        if rated <= 0 or self.options.max_amps < rated:
            self._skip(
                "above rating",
                f"the owner's cap ({self.options.max_amps:.0f} A) is below the "
                f"rating ({rated:.0f} A)",
            )
            return
        amps = rated + ABOVE_RATING_A
        original = self.snapshot["raw"][OUTPUT_CURRENT]
        failure = await self._write(OUTPUT_CURRENT, round(amps / SCALE_THIS_PROJECT))
        if failure == REFUSED:
            refusal = self.conditions["refusals"][OUTPUT_CURRENT]
            self.steps.append(Step("above rating", REFUSED, f"{amps:.0f} A: {refusal}"))
            return
        if failure is not None:
            refusal = self.conditions["refusals"][OUTPUT_CURRENT]
            self.steps.append(Step("above rating", failure, refusal))
            self._worst(3)
            return
        samples = await self._wait(SETTLE_SECONDS)
        tail = samples[-SAMPLES:]
        draw = statistics.median(s.draw_a for s in tail)
        available = tail[-1].available_a
        # Put the house's own word back before anything else is offered.
        await self._write(OUTPUT_CURRENT, original)
        held = available is None or available <= rated + 0.05
        if held and draw <= rated + TOLERANCE_A:
            self.steps.append(
                Step(
                    "above rating",
                    CLAMPED,
                    f"{amps:.0f} A accepted; the available current reads "
                    f"{available} A and the car draws {draw:.1f} A",
                )
            )
        else:
            self.steps.append(
                Step(
                    "above rating",
                    NOT_CLAMPED,
                    f"{amps:.0f} A accepted; the available current reads "
                    f"{available} A: a control must cap itself at the rating",
                )
            )

    def _available_vs_setting(self) -> None:
        """Say what the available current (21322) is, beside the setting."""
        if not self.options.follow:
            return
        usable = [(o, a, d) for o, a, d in self._pairs if a is not None]
        if len(usable) < 2:
            return
        offsets = [round(a - o, 2) for o, a, _d in usable]
        verdict = CONFIRMED
        if all(abs(x) <= 0.05 for x in offsets):
            what = "equals the setting"
        elif all(abs(x - 1.0) <= 0.05 for x in offsets):
            what = "is the setting plus 1 A"
        elif all(abs(a - d) <= 0.15 for _o, a, d in usable):
            what = "follows what the car draws"
        else:
            what = "is neither the setting, the setting plus 1 A nor the draw"
            verdict = INCONCLUSIVE
            self._worst(3)
        self.conditions["available_offsets_a"] = offsets
        self.steps.append(
            Step("available current", verdict, f"{what} (offsets {offsets})")
        )

    async def _phase_charging(self) -> None:
        """Switch the phase with a car charging: stop, switch, start, and back."""
        self._step("switch the phase with a car charging")
        if not self._needs_car("phase while charging"):
            return
        original = self.snapshot["raw"].get(PHASE_SETPOINT)
        if original not in PHASE_WORDS:
            self._skip(
                "phase while charging",
                f"the setting reads {original!r}, not one of {PHASE_WORDS}",
            )
            return
        if self.snapshot["raw"].get(START_STOP) != START_WORD:
            self._skip(
                "phase while charging",
                "the start/stop register does not read as running: the order "
                "stop, switch, start cannot be kept",
            )
            return
        target = PHASE_WORDS[1 - PHASE_WORDS.index(original)]
        details: list[str] = []
        clean = True
        for goal in (target, original):
            problem, detail = await self._switch_phase(goal)
            details.append(detail)
            if problem is not None:
                clean = False
                break
        verdict = CONFIRMED if clean else INCONCLUSIVE
        if not clean:
            self._worst(3)
        self.steps.append(Step("phase while charging", verdict, "; ".join(details)))

    async def _switch_phase(self, target: int) -> tuple[str | None, str]:
        """Stop, see the stop, write the phase, start. Returns (problem, detail)."""
        name = f"to {'single' if target == 1 else 'three'} phase"
        failure = await self._write(START_STOP, STOP_WORD)
        if failure is not None:
            return failure, f"{name}: the stop was {failure}"
        stopped = await self._timed(
            lambda s: s.status != CHARGING and s.draw_a < STOPPED_DRAW_A,
            STATE_TIMEOUT,
        )
        if stopped is None:
            await self._write(START_STOP, START_WORD)
            return (
                "the stop was not seen",
                f"{name}: the stop was not seen within {STATE_TIMEOUT:.0f} s, so "
                "the switch was not written",
            )
        failure = await self._write(PHASE_SETPOINT, target)
        if failure is not None:
            await self._write(START_STOP, START_WORD)
            return failure, f"{name}: the switch was {failure}"

        async def followed() -> bool:
            return await self._read_one("input", PHASE_ACTUAL) == target

        moved = await self._poll(followed, STATE_TIMEOUT)
        failure = await self._write(START_STOP, START_WORD)
        if failure is not None:
            return failure, f"{name}: the start was {failure}"
        resumed = await self._timed(lambda s: s.status == CHARGING, STATE_TIMEOUT)
        if resumed is None:
            return "no resume", f"{name}: the car did not resume"
        a, b, c = (await self._wait(SETTLE_SECONDS))[-1].currents_a
        single = (
            a >= MIN_CURRENT_A - TOLERANCE_A
            and b < STOPPED_DRAW_A
            and c < STOPPED_DRAW_A
        )
        shape = "on phase A only" if single else f"on {a:.1f}/{b:.1f}/{c:.1f} A"
        if not moved:
            return "the actual mode did not follow", f"{name}: 21270 did not follow"
        if target == 1 and not single:
            return "not single phase", f"{name}: the car then draws {shape}"
        return (
            None,
            f"{name}: stopped, switched, resumed after {resumed:.0f} s, {shape}",
        )

    async def _mileage(self) -> None:
        """Write the mileage setting its own word: a no-op that proves the path."""
        self._step("write the mileage setting its own word")
        original = self.snapshot["raw"].get(MILEAGE)
        if original is None:
            self._skip(
                "mileage", "the register could not be read, so it is not written"
            )
            return
        failure = await self._write(MILEAGE, original)
        if failure is not None:
            refusal = self.conditions["refusals"][MILEAGE]
            self.steps.append(Step("mileage", failure, refusal))
            if failure != REFUSED:
                self._worst(3)
            return
        held = await self._held(MILEAGE)
        if held == original:
            self.steps.append(Step("mileage", CONFIRMED, "its own word, taken"))
        else:
            self.steps.append(
                Step("mileage", MISMATCH, f"wrote {original}, then read {held}")
            )
            self._worst(3)

    async def _fallback(self) -> None:
        """Stop every read, and see what the car is left with after the session drops.

        Only once 21203's own word is back and the cap is no higher than the
        house's setting, so whatever the wallbox falls back to, it is not
        something this run offered.
        """
        self._step("fall silent")
        if not self._needs_car("fallback") or not self._needs_cap("fallback"):
            return
        original = self.snapshot["raw"][OUTPUT_CURRENT]
        if self.options.max_amps > original * SCALE_THIS_PROJECT + 0.05:
            self._skip(
                "fallback",
                f"the cap ({self.options.max_amps:.0f} A) is above the setting the "
                f"house had ({original * SCALE_THIS_PROJECT:.0f} A)",
            )
            return
        if OUTPUT_CURRENT in self.snapshot["touched"]:
            row = await self._restore_one(OUTPUT_CURRENT, original)
            if not row.restored:
                self._skip("fallback", "the output current could not be put back first")
                return
        before = await self._sample()
        await self.clock.sleep(SILENCE_SECONDS)
        try:
            after = await self._sample()
        except _LOST:
            await self.clock.sleep(RESTORE_PAUSE)
            after = await self._sample()
        held = await self._held(OUTPUT_CURRENT)
        self.conditions["fallback"] = {
            "silence_s": SILENCE_SECONDS,
            "draw_before_a": before.draw_a,
            "draw_after_a": after.draw_a,
            "available_after_a": after.available_a,
            "status_after": CHARGING_STATUS.get(after.status or 0, after.status),
            "setting_after_word": held,
        }
        left = after.status == CHARGING and after.draw_a >= before.draw_a - TOLERANCE_A
        self.steps.append(
            Step(
                "fallback",
                CONFIRMED,
                f"after {SILENCE_SECONDS:.0f} s of silence the car draws "
                f"{after.draw_a:.1f} A (before {before.draw_a:.1f} A), available "
                f"{after.available_a} A, setting word {held}"
                + ("; it is left charging at what it had" if left else ""),
            )
        )

    async def async_restore(self) -> None:
        """Put back everything in the snapshot, shielded from cancellation.

        For a driver restoring a saved snapshot after a run died; a run does it
        itself, last, whatever happened.
        """
        await self._shielded(self._restore())

    # -- the restore: never budgeted, never deadlined, never skipped --------

    async def _restore(self) -> None:
        """Put back every register this run sent a write to, newest first.

        The phase is the exception to "newest first": a contactor does not open
        under load, so where the phase and the start word were both written,
        the charge is stopped before the phase goes back and the start word is
        restored last.
        """
        raw: dict[int, int] = self.snapshot["raw"]
        order = list(reversed(self.snapshot["touched"]))
        if PHASE_SETPOINT in order and START_STOP in order:
            order = [a for a in order if a not in (PHASE_SETPOINT, START_STOP)]
            order += [PHASE_SETPOINT, START_STOP]
            if await self._held(PHASE_SETPOINT) != raw[PHASE_SETPOINT]:
                await self._stop_for_phase()
        for address in order:
            self.restores.append(await self._restore_one(address, raw[address]))
        if self.restores and any(not row.restored for row in self.restores):
            self._worst(5)

    async def _stop_for_phase(self) -> None:
        """Stop the charge and wait to see it, before the phase is put back."""
        try:
            await self.port.write(START_STOP, STOP_WORD)
            await self._until(
                lambda s: s.status != CHARGING and s.draw_a < STOPPED_DRAW_A,
                STATE_TIMEOUT,
            )
        except _LOST:
            _LOGGER.exception("wallbox capability test: could not stop for the phase")

    async def _held(self, address: int) -> int | None:
        """Read what the register holds now, on a fresh session where possible.

        A port with no fresh session answers the first holding read after a
        write with another register's value, so it is read twice and the
        second answer is the one taken.
        """
        try:
            if self.port.fresh:
                return (await self.port.read_fresh("holding", address, 1))[0]
            await self.port.read("holding", address, 1)
            return (await self.port.read("holding", address, 1))[0]
        except _LOST:
            return None

    async def _restore_one(self, address: int, original: int) -> RestoreResult:
        """Write the snapshot's raw word back, and check it by a raw read.

        Every attempt writes. When the write itself is refused or lost, the
        register is still read: a refused write changed nothing, and a register
        that already holds the original is restored, whatever the write said.
        """
        detail = ""
        for attempt in range(1, RESTORE_ATTEMPTS + 1):
            try:
                await self.port.write(address, original)
            except _LOST as err:
                detail = f"{type(err).__name__}: {err}"
                _LOGGER.warning(
                    "wallbox capability test: restore of %s failed (%s), attempt %s",
                    address,
                    detail,
                    attempt,
                )
            held = await self._held(address)
            if held == original:
                return RestoreResult(address, original, True, attempt, detail)
            detail = detail or f"read {held}, wanted {original}"
            await self.clock.sleep(RESTORE_PAUSE)
        return RestoreResult(address, original, False, RESTORE_ATTEMPTS, detail)
