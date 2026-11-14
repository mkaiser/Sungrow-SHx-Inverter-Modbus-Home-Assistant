"""The capability test of a wallbox an inverter manages: written at the inverter.

A wallbox on a hybrid inverter's bus is driven by the inverter, which
overwrites a write to the wallbox's own registers within seconds
(`capability_test.MANAGED_REASON`). Its charge is controlled at the inverter's
EV charger block (`sungrow_modbus.hybrid_inverter.ev_charger`), and this asks
of that block what `capability_test` asks of a standalone wallbox's own
registers: does a write land, and does the car do what it was told?

**Only the inverter is written**; the wallbox is only read, for what the car
does. Every verdict is the car's: the phase currents and the charging status.
A readback of the inverter's block is recorded, never a verdict on its own,
because through a WiNet-S a readback can be stale.

The checks, as measured at gerd's on 2026-11-14:

* *user current*: in user-defined mode the car follows the user current,
  6, 8 and 10 A by default, never above `max_amps` or the wallbox's rating;
* *floor*: 5 A is refused by the inverter (exception 0x04). If it is taken,
  6 A is written straight back;
* *start/stop*: charging off stops the car within seconds, charging on starts
  it again. A car left stopped too long falls asleep and needs a replug, so
  the pause is short.

**The restore puts the house back, not only the registers**, never budgeted,
never deadlined and never skipped: the user current while still in user-
defined mode (it is writable only there), then the mode, then charging on if
it was on and a mode change ended the session. Each by a raw read of the
block, then the car: if a car was charging, it must be charging again. A
house left changed is code 5, with what to do on site.

Nothing here talks to Home Assistant, opens a file or prints.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging
from typing import Any, NamedTuple, Protocol

from modbus_connection import ModbusError, ModbusExceptionError

from ..capability_test.procedure import Clock, RealClock
from ..hybrid_inverter import ev_charger as ev
from . import capability_test as wct
from .discovery import MODEL_NAME, model_name
from .registers import CHARGING_STATUS

_LOGGER = logging.getLogger(__name__)

_LOST = (TimeoutError, OSError)

#: The block, read whole: on/off, mode, three words nobody has named, the
#: user current, two times, and the grid flag. Eleven words from on/off.
BLOCK_COUNT = 11

PLAN_AMPS = (6.0, 8.0, 10.0)
DEFAULT_MAX_AMPS = 10.0

#: Below the floor, for the refusal check. 5.0 A was refused at gerd's.
BELOW_FLOOR_A = 5.0

#: A car within this of the offer follows it. It drew about 0.5 A under.
TOLERANCE_A = 1.5

#: A lower current applied within six seconds, a higher one ramped in about
#: twenty, a start took up to fifteen and the ramp to 16 A forty more.
FOLLOW_TIMEOUT = 60.0
START_TIMEOUT = 60.0
STOP_TIMEOUT = 20.0
SAMPLE_INTERVAL = 3.0

#: How long the car is left stopped. A 2.5-minute stop resumed without a
#: replug, a 7-minute one did not.
PAUSE_SECONDS = 15.0

#: The restore keeps trying; between attempts it waits this long.
RESTORE_PAUSE = 5.0
RESTORE_ROUNDS = 6

CHARGING = 3

CONFIRMED = "the car did as it was told"
CAR_LIMIT = "the car draws less than offered: its own limit"
INCONCLUSIVE = wct.INCONCLUSIVE
REFUSED = wct.REFUSED
SKIPPED = wct.SKIPPED
TAKEN = "taken where a refusal was expected"

CODES = {
    0: "every planned check ran and the car did as it was told",
    1: "nothing ran -- could not read the inverter or the wallbox",
    2: "this cannot run here -- no managed wallbox, no car charging, or no snapshot",
    3: "ran, but checks were skipped or inconclusive",
    5: "the house was not put back",
}
SEVERITY = (0, 3, 1, 2, 5)
DRY_RUN_MEANS = wct.DRY_RUN_MEANS

#: What to do on site when the restore could not bring the charge back.
ON_SITE = (
    "set the charging mode and current in iSolarCloud as they were, press Start, "
    "and replug the car if it does not resume"
)


class InverterPort(Protocol):
    """The inverter at unit 1: holding reads and single writes."""

    async def read(self, address: int, count: int) -> list[int]:
        """Read holding words. Raises, never guesses."""

    async def write(self, address: int, word: int) -> None:
        """Write one holding word. Raises `ModbusError` when refused."""


class WallboxReader(Protocol):
    """The wallbox, read only: at its own address or through a dongle."""

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read words. Raises, never guesses."""


@dataclass(frozen=True)
class Options:
    """What a run has been given leave to do."""

    leave: bool = False
    """Write at all. False is a dry run."""

    max_amps: float = DEFAULT_MAX_AMPS
    """The highest user current offered, never above the wallbox's rating."""

    current: bool = True
    """Step the user current and watch the car follow."""

    floor: bool = True
    """Offer 5 A and expect the inverter to refuse it."""

    start_stop: bool = False
    """Stop the charge and start it again. Off by default: an interruption."""


class Step(NamedTuple):
    """One thing the run did or declined to do, and what it found."""

    name: str
    verdict: str
    detail: str


class Outcome(NamedTuple):
    """Everything one run established."""

    code: int
    steps: tuple[Step, ...]
    restored: bool
    conditions: dict[str, Any]


class Guard(Exception):
    """The run cannot proceed; carries the code it ends with."""

    def __init__(self, code: int, reason: str) -> None:
        """Say which code and why."""
        super().__init__(reason)
        self.code = code
        self.reason = reason


class Block(NamedTuple):
    """The inverter's block at one moment."""

    charging: int
    mode: int
    user_current: int
    grid: int


def _follows(amps: float) -> Callable[[wct.Sample], bool]:
    """Return the test for a car charging at `amps`, within tolerance."""

    def test(sample: wct.Sample) -> bool:
        return sample.status == CHARGING and abs(sample.draw_a - amps) <= TOLERANCE_A

    return test


def _status(code: int | None) -> str | int | None:
    """Return a charging status's name, or the code nobody has named."""
    return CHARGING_STATUS.get(code or 0, code)


class ManagedWallboxTest:
    """One run against one inverter-managed wallbox. Construct it, call `async_run`."""

    def __init__(
        self,
        inverter: InverterPort,
        wallbox: WallboxReader,
        options: Options | None = None,
        *,
        clock: Clock | None = None,
        on_snapshot: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        on_step: Callable[[str], None] | None = None,
    ) -> None:
        """Remember the two devices; nothing is read yet."""
        self.inverter = inverter
        self.wallbox = wallbox
        self.options = options or Options()
        self.clock = clock or RealClock()
        self._on_snapshot = on_snapshot
        self._on_step = on_step
        self.code = 0
        self.steps: list[Step] = []
        self.conditions: dict[str, Any] = {}
        self.snapshot: dict[str, Any] = {}
        self.written: list[tuple[int, int]] = []
        self.restored = True
        self._charging_at_start = False

    # -- reading -------------------------------------------------------------

    async def _block(self) -> Block:
        words = await self.inverter.read(ev.CHARGING, BLOCK_COUNT)
        return Block(words[0], words[1], words[5], words[10])

    async def _sample(self) -> wct.Sample:
        status = (await self.wallbox.read("input", wct.CHARGING_STATUS_ADDRESS, 1))[0]
        currents = []
        for address in (wct.PHASE_A_CURRENT, wct.PHASE_B_CURRENT, wct.PHASE_C_CURRENT):
            word = (await self.wallbox.read("input", address, 1))[0]
            currents.append(word * wct.SCALE_THIS_PROJECT)
        return wct.Sample(status, (currents[0], currents[1], currents[2]), None, None)

    async def _until(
        self, test: Callable[[wct.Sample], bool], timeout: float
    ) -> tuple[float | None, wct.Sample]:
        """Sample until `test` holds; return the seconds it took (None) and the last."""
        start = self.clock.monotonic()
        while True:
            sample = await self._sample()
            if test(sample):
                return self.clock.monotonic() - start, sample
            if self.clock.monotonic() - start >= timeout:
                return None, sample
            await self.clock.sleep(SAMPLE_INTERVAL)

    # -- bookkeeping ---------------------------------------------------------

    def _step(self, label: str) -> None:
        if self._on_step is not None:
            self._on_step(label)

    def _worst(self, code: int) -> None:
        if SEVERITY.index(code) > SEVERITY.index(self.code):
            self.code = code

    def _record(self, name: str, verdict: str, detail: str) -> None:
        self.steps.append(Step(name, verdict, detail))
        if verdict not in (CONFIRMED,):
            self._worst(3)

    async def _write(self, address: int, word: int) -> None:
        """Write one word, after the snapshot is on disk. Raises as the port does."""
        touched: list[int] = self.snapshot["touched"]
        if address not in touched:
            touched.append(address)
            if self._on_snapshot is not None:
                await self._on_snapshot(self.snapshot)
        await self.inverter.write(address, word)
        self.written.append((address, word))

    # -- the run -------------------------------------------------------------

    async def async_run(self) -> Outcome:
        """Run every planned check and put the house back, whatever happens."""
        try:
            await self._preflight()
            if self.options.leave:
                if self.options.current:
                    await self._current()
                if self.options.floor:
                    await self._floor()
                if self.options.start_stop:
                    await self._start_stop()
            else:
                self.conditions["dry_run"] = DRY_RUN_MEANS
        except Guard as guard:
            self._worst(guard.code)
            self.conditions["guard"] = guard.reason
        except (ModbusError, *_LOST) as err:
            _LOGGER.exception("managed wallbox test: lost a device")
            self._worst(1 if not self.written else 3)
            self.conditions["guard"] = f"a device stopped answering: {err}"
        finally:
            if self.written:
                await self._shielded(self.async_restore())
        return Outcome(self.code, tuple(self.steps), self.restored, self.conditions)

    async def _shielded(self, coro: Awaitable[None]) -> None:
        """Finish a restore even if this run is being cancelled."""
        task = asyncio.ensure_future(coro)
        while True:
            try:
                await asyncio.shield(task)
                return
            except asyncio.CancelledError:
                if task.done():
                    raise
                _LOGGER.warning("managed wallbox test: cancelled, restore continues")

    async def _preflight(self) -> None:
        self._step("identify the wallbox and the inverter's block")
        try:
            name = model_name(
                await self.wallbox.read(
                    MODEL_NAME.space, MODEL_NAME.address, MODEL_NAME.length
                )
            )
            block = await self._block()
            rated = (await self.wallbox.read("input", wct.RATED_CURRENT, 1))[0]
            sample = await self._sample()
        except (ModbusError, *_LOST) as err:
            raise Guard(1, f"could not read: {type(err).__name__}: {err}") from err
        if not name or not name.upper().startswith("AC"):
            raise Guard(2, f"{name!r} is not a Sungrow wallbox")
        rating = round(rated * wct.SCALE_THIS_PROJECT, 1)
        self.conditions.update(
            model=name,
            rated_a=rating,
            charging_word=block.charging,
            mode=ev.MODES.get(block.mode, block.mode),
            user_current_a=round(block.user_current * ev.AMPS_PER_COUNT, 1),
            grid_word=block.grid,
            status=_status(sample.status),
            draw_a=round(sample.draw_a, 1),
        )
        if ev.manages_a_wallbox(block.mode) is not True:
            raise Guard(
                2,
                f"the inverter's charging mode reads {block.mode}, no mode anybody "
                "has named: no wallbox under its management, as far as can be told",
            )
        self._charging_at_start = sample.status == CHARGING
        self.snapshot = {
            "raw": {
                ev.CHARGING: block.charging,
                ev.MODE: block.mode,
                ev.USER_CURRENT: block.user_current,
            },
            "charging_at_start": self._charging_at_start,
            "touched": [],
        }
        cap = min(self.options.max_amps, rating) if rating > 0 else 0.0
        self.conditions["cap_a"] = cap
        if not self.options.leave:
            return
        if not self._charging_at_start:
            raise Guard(2, "no car is charging: nothing the car does could be judged")
        if self._on_snapshot is None:
            raise Guard(2, "writes need a snapshot callback to keep the snapshot")
        await self._on_snapshot(self.snapshot)

    # -- the checks ------------------------------------------------------------

    async def _user_defined(self) -> bool:
        """Switch to user-defined mode if needed; say whether it is now."""
        if self.snapshot["raw"][ev.MODE] == ev.USER_DEFINED:
            return True
        self._step("switch to user-defined mode")
        try:
            await self._write(ev.MODE, ev.USER_DEFINED)
        except ModbusExceptionError as err:
            self._record("user-defined mode", REFUSED, f"{type(err).__name__}: {err}")
            return False
        return True

    async def _current(self) -> None:
        cap = self.conditions["cap_a"]
        plan = [a for a in PLAN_AMPS if a <= cap]
        if not plan:
            self._record("user current", SKIPPED, f"the cap ({cap} A) is under 6 A")
            return
        if not await self._user_defined():
            return
        rows: list[dict[str, Any]] = []
        self.conditions["user_current"] = rows
        for amps in plan:
            self._step(f"user current {amps:.0f} A")
            try:
                await self._write(ev.USER_CURRENT, ev.user_current_word(amps, cap))
            except ModbusExceptionError as err:
                self._record(f"user current {amps:.0f} A", REFUSED, str(err))
                return
            seconds, sample = await self._until(_follows(amps), FOLLOW_TIMEOUT)
            rows.append(
                {
                    "offered_a": amps,
                    "seconds": seconds,
                    "draw_a": round(sample.draw_a, 1),
                }
            )
            if seconds is not None:
                verdict = CONFIRMED
            elif sample.status == CHARGING and sample.draw_a < amps - TOLERANCE_A:
                verdict = CAR_LIMIT
            else:
                verdict = INCONCLUSIVE
            self._record(
                f"user current {amps:.0f} A",
                verdict,
                f"the car draws {sample.draw_a:.1f} A"
                + (f" after {seconds:.0f} s" if seconds is not None else ""),
            )

    async def _floor(self) -> None:
        if not await self._user_defined():
            return
        self._step("offer under the floor")
        try:
            await self._write(ev.USER_CURRENT, round(BELOW_FLOOR_A / ev.AMPS_PER_COUNT))
        except ModbusExceptionError as err:
            self.steps.append(Step("floor", CONFIRMED, f"5 A refused: {err}"))
            return
        # Taken: the inverter's floor is not where it was measured. Put 6 A
        # back at once, before the car is offered what it may not take.
        await self._write(ev.USER_CURRENT, round(ev.MIN_AMPS / ev.AMPS_PER_COUNT))
        self._record("floor", TAKEN, "5 A was taken; 6 A written straight back")

    async def _start_stop(self) -> None:
        self._step("stop the charge")
        await self._write(ev.CHARGING, ev.OFF)
        stopped, _ = await self._until(
            lambda s: s.status != CHARGING and s.draw_a < wct.STOPPED_DRAW_A,
            STOP_TIMEOUT,
        )
        await self.clock.sleep(PAUSE_SECONDS)
        self._step("start the charge")
        await self._write(ev.CHARGING, ev.ON)
        started, sample = await self._until(
            lambda s: s.status == CHARGING and s.draw_a >= ev.MIN_AMPS - TOLERANCE_A,
            START_TIMEOUT,
        )
        self.conditions["start_stop_seconds"] = {"stop": stopped, "start": started}
        if stopped is not None and started is not None:
            self.steps.append(
                Step(
                    "start/stop",
                    CONFIRMED,
                    f"stopped after {stopped:.0f} s, "
                    f"charging again after {started:.0f} s",
                )
            )
        else:
            self._record(
                "start/stop",
                INCONCLUSIVE,
                f"stopped: {stopped is not None}, started: {started is not None}, "
                f"status {_status(sample.status)}",
            )

    # -- the restore -----------------------------------------------------------

    async def async_restore(self) -> None:
        """Put the block back, in the order it can be written, then the charge."""
        raw: dict[int, int] = {int(k): v for k, v in self.snapshot["raw"].items()}
        for round_ in range(RESTORE_ROUNDS):
            try:
                if await self._restore_once(raw):
                    self.restored = await self._charge_is_back()
                    if self.restored:
                        return
            except (ModbusError, *_LOST):
                _LOGGER.exception("managed wallbox test: restore, round %s", round_ + 1)
            await self.clock.sleep(RESTORE_PAUSE)
        self.restored = False
        self._worst(5)
        self.conditions["on_site"] = ON_SITE

    async def _restore_once(self, raw: dict[int, int]) -> bool:
        block = await self._block()
        # The user current is writable only in user-defined mode: first.
        if block.user_current != raw[ev.USER_CURRENT]:
            if block.mode != ev.USER_DEFINED:
                await self.inverter.write(ev.MODE, ev.USER_DEFINED)
            await self.inverter.write(ev.USER_CURRENT, raw[ev.USER_CURRENT])
            block = await self._block()
        if block.mode != raw[ev.MODE]:
            await self.inverter.write(ev.MODE, raw[ev.MODE])
            block = await self._block()
        if block.charging != raw[ev.CHARGING]:
            await self.inverter.write(ev.CHARGING, raw[ev.CHARGING])
            block = await self._block()
        now = {
            ev.CHARGING: block.charging,
            ev.MODE: block.mode,
            ev.USER_CURRENT: block.user_current,
        }
        self.conditions["restored_block"] = {str(k): v for k, v in now.items()}
        return now == raw

    async def _charge_is_back(self) -> bool:
        """Return whether a car that was charging charges again; write on once."""
        if not self.snapshot.get("charging_at_start"):
            return True
        seconds, _ = await self._until(lambda s: s.status == CHARGING, START_TIMEOUT)
        if seconds is not None:
            return True
        await self.inverter.write(ev.CHARGING, ev.ON)
        seconds, _ = await self._until(lambda s: s.status == CHARGING, START_TIMEOUT)
        return seconds is not None
