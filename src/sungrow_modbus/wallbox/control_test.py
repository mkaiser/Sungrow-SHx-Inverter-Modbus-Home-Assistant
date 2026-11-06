"""The wallbox's control test: write a setting, read it back, watch the car.

The inverter's control test (`sungrow_modbus.control_test`) asks whether a
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
from dataclasses import dataclass
import logging
import statistics
from typing import Any, NamedTuple, Protocol

from modbus_connection import ModbusError

from ..control_test.procedure import Clock, RealClock
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

# -- what a run can say --------------------------------------------------------

MATCHED = "matched"
MISMATCH = "the word read back is not the word written"
CONFIRMED = "the wallbox did as it was told"
DECADE = "the car stopped: the setting is read a decade too low"
INCONCLUSIVE = "could not tell"
SKIPPED = "skipped"
REFUSED = "refused"
DROPPED = "the link dropped"

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


def _address(component: type[Any], name: str) -> int:
    """Return a field's protocol address from the library's own map."""
    address: int = component.declared_fields[name].address
    return address


OUTPUT_CURRENT = _address(WallboxSettings, "output_current_setting")
START_STOP = _address(WallboxSettings, "start_stop_raw")
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
    sent. The survey's rule: a run with nobody at a terminal is a no."""

    max_amps: float = DEFAULT_MAX_AMPS
    """The highest current to offer, under the first reading of the scale."""

    start_stop: bool = False
    """Also stop and start the charge once. Off by default, because it is
    the one step that interrupts a car."""


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


class WallboxControlTest:
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
                await self._current_steps()
                if self.options.start_stop:
                    await self._start_stop()
            else:
                self.conditions["dry_run"] = DRY_RUN_MEANS
        except Guard as guard:
            self._worst(guard.code)
            self.conditions["guard"] = guard.reason
        except _LOST:
            _LOGGER.exception("wallbox control test: lost the wallbox")
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
                _LOGGER.warning("wallbox control test: cancelled, restore continues")
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

        if self.options.leave:
            if self._on_snapshot is None:
                raise Guard(2, "writes need a snapshot callback to keep the snapshot")
            await self._on_snapshot(self.snapshot)
        if sample.status == 9:
            raise Guard(2, "the wallbox reports a fault")
        if self.options.max_amps <= 0:
            raise Guard(2, "max_amps must be positive")

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

        # Leg A: the same session, through the library's own decode.
        same = await self._read_one("holding", OUTPUT_CURRENT)
        # Leg B: the raw word on a fresh session.
        if self.port.fresh:
            raw = (await self.port.read_fresh("holding", OUTPUT_CURRENT, 1))[0]
        else:
            raw = same
            self._note(
                "the port has no fresh session: the raw readback is not independent"
            )
            self._worst(3)
        if raw != word:
            return Step(
                name,
                MISMATCH,
                f"wrote {word}; the same session read {same}, a fresh one {raw}",
            )

        if not self._charging_at_start:
            return Step(name, MATCHED, "no car charging: behaviour not watched")

        # Leg C: what the car draws.
        samples = await self._wait(SETTLE_SECONDS)
        tail = samples[-SAMPLES:]
        draw = statistics.median(s.draw_a for s in tail)
        offered = word * SCALE_THIS_PROJECT
        charging = all(s.status == CHARGING for s in tail)
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
        stopped = await self._until(lambda s: s.status != CHARGING, STATE_TIMEOUT)
        failure = await self._write(START_STOP, START_WORD)
        if failure is not None:
            self.steps.append(
                Step("start", failure, self.conditions["refusals"][START_STOP])
            )
            self._worst(3)
            return
        resumed = await self._until(lambda s: s.status == CHARGING, STATE_TIMEOUT)
        if stopped and resumed:
            self.steps.append(
                Step("start/stop", CONFIRMED, "stopped on 1, resumed on 0")
            )
        else:
            self.steps.append(
                Step(
                    "start/stop",
                    INCONCLUSIVE,
                    f"stopped: {stopped}, resumed: {resumed}",
                )
            )
            self._worst(3)

    async def _until(self, condition: Callable[[Sample], bool], timeout: float) -> bool:
        end = self.clock.monotonic() + timeout
        while self.clock.monotonic() < end:
            if condition(await self._sample()):
                return True
            await self.clock.sleep(SAMPLE_INTERVAL)
        return False

    # -- the restore: never budgeted, never deadlined, never skipped --------

    async def _restore(self) -> None:
        """Put back every register this run sent a write to, newest first."""
        raw: dict[int, int] = self.snapshot["raw"]
        for address in reversed(self.snapshot["touched"]):
            original = raw[address]
            self.restores.append(await self._restore_one(address, original))
        if self.restores and any(not row.restored for row in self.restores):
            self._worst(5)

    async def _held(self, address: int) -> int | None:
        """Read what the register holds now, on a fresh session where possible."""
        reader = self.port.read_fresh if self.port.fresh else self.port.read
        try:
            return (await reader("holding", address, 1))[0]
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
                    "wallbox control test: restore of %s failed (%s), attempt %s",
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
