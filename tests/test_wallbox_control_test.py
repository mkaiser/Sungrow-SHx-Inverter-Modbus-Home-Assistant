"""The wallbox control test, against a wallbox that can be wrong where it matters.

`FakeWallbox` is a wallbox with a car on it. It models the three things the
procedure turns on, none of which a passing mock would show:

* **The scale in dispute.** `scale` is what the output current setting really
  means per count: 0.1 A here, 0.01 A in discussion #571. A car offered less
  than 6 A stops, as it does on a real pilot signal.
* **The stale readback.** A holding read straight after a write, on the same
  session, answers another register's value (measured on 2026-10-29 over
  TLS). `read_fresh` never does.
* **Refusal and loss.** A write can come back as the real exception type
  (`ModbusExceptionError`), and a link can drop (`TimeoutError`). A bare
  `ModbusError` would not be the thing a device sends.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
from typing import Any

from modbus_connection import ModbusExceptionError
import pytest

from sungrow_modbus.wallbox import control_test as wct
from sungrow_modbus.wallbox.discovery import MODEL_NAME

from .conftest import encode_string

STALE_JUNK = 4242


class FakeClock:
    """Time that only passes when somebody sleeps, so a run takes no time."""

    def __init__(self) -> None:
        """Start at zero."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the pretend time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Pass time without waiting."""
        self.now += seconds


class FakeWallbox:
    """An AC22E-01 with a car, as a `WallboxPort`."""

    def __init__(
        self,
        *,
        scale: float = 0.1,
        charging: bool = True,
        car_max_a: float = 13.0,
        setting: int = 160,
        rated: int = 320,
        name: str = "AC22E-01",
        start_stop: int = 0,
        fresh: bool = True,
        stale: bool = True,
        refuse: set[int] | None = None,
        drop_writes_after: int | None = None,
        restore_fails: bool = False,
        until_first_write_reads_as: float | None = None,
        enabled: int = 1,
        phase: int = 0,
        phase_follows: bool = True,
        ignores_start_stop: bool = False,
        ignores_enable: bool = False,
    ) -> None:
        """Set the wallbox up; every argument is a way for it to be different."""
        self.scale = scale
        self.charging = charging
        self.car_max_a = car_max_a
        self.name = name
        self.fresh = fresh
        self.stale = stale
        self.refuse = refuse or set()
        self.drop_writes_after = drop_writes_after
        self.restore_fails = restore_fails
        self.rated = rated
        self.until_first_write_reads_as = until_first_write_reads_as
        self.holding = {
            wct.OUTPUT_CURRENT: setting,
            wct.START_STOP: start_stop,
            wct.ENABLED: enabled,
            wct.PHASE_SETPOINT: phase,
        }
        self.phase_follows = phase_follows
        self.ignores_start_stop = ignores_start_stop
        self.ignores_enable = ignores_enable
        self.fixed_phase = phase
        self.original = dict(self.holding)
        self.writes: list[tuple[int, int]] = []
        self._just_wrote = False

    # -- the car -----------------------------------------------------------

    def _live(self) -> tuple[int, float]:
        """Return (status, amps the car draws) from what is set."""
        if self.holding[wct.ENABLED] == wct.DISABLED_WORD and not self.ignores_enable:
            return wct.DISABLED_STATUS, 0.0
        if not self.charging:
            return 1, 0.0
        if (
            self.holding[wct.START_STOP] == wct.STOP_WORD
            and not self.ignores_start_stop
        ):
            return 5, 0.0
        scale = self.scale
        if self.until_first_write_reads_as is not None and not self.writes:
            scale = self.until_first_write_reads_as
        offered = self.holding[wct.OUTPUT_CURRENT] * scale
        if offered < wct.MIN_CURRENT_A:
            return 5, 0.0
        return 3, min(offered, self.car_max_a)

    # -- the port ----------------------------------------------------------

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read on the open session, stale straight after a write."""
        words = self._words(space, address, count)
        if space == "holding" and self.stale and self._just_wrote:
            self._just_wrote = False
            return [STALE_JUNK] * count
        return words

    async def read_fresh(self, space: str, address: int, count: int) -> list[int]:
        """Read on a new session, which is never stale."""
        return self._words(space, address, count)

    def _words(self, space: str, address: int, count: int) -> list[int]:
        if space == "holding":
            return [self.holding.get(address + i, 0) for i in range(count)]
        if address == MODEL_NAME.address:
            return encode_string(self.name, MODEL_NAME.length)
        status, amps = self._live()
        counts = round(amps / wct.SCALE_THIS_PROJECT)
        table: dict[int, int] = {
            wct.RATED_CURRENT: self.rated,
            wct.PHASE_ACTUAL: (
                self.holding[wct.PHASE_SETPOINT]
                if self.phase_follows
                else self.fixed_phase
            ),
            wct.PHASE_A_CURRENT: counts,
            wct.PHASE_B_CURRENT: counts,
            wct.PHASE_C_CURRENT: counts,
            wct.CHARGING_POWER: round(amps * 230 * 3) & 0xFFFF,
            wct.CHARGING_POWER + 1: round(amps * 230 * 3) >> 16,
            wct.CHARGING_STATUS_ADDRESS: status,
            wct.AVAILABLE_CURRENT: self.holding[wct.OUTPUT_CURRENT],
        }
        return [table.get(address + i, 0) for i in range(count)]

    async def write(self, address: int, word: int) -> None:
        """Write a word, or refuse, or lose the link."""
        if address in self.refuse:
            raise ModbusExceptionError(4, "illegal data value")
        if self.drop_writes_after is not None and len(self.writes) >= (
            self.drop_writes_after
        ):
            raise TimeoutError("the link dropped")
        if self.restore_fails and word == self.original[address]:
            raise TimeoutError("the link dropped")
        self.writes.append((address, word))
        self.holding[address] = word
        self._just_wrote = True


async def _run(
    box: FakeWallbox,
    *,
    leave: bool = True,
    snapshot: bool = True,
    **options: Any,
) -> tuple[wct.Outcome, list[str]]:
    """Run the procedure; return the outcome and the order things happened in."""
    events: list[str] = []

    async def on_snapshot(data: dict[str, Any]) -> None:
        events.append(
            f"snapshot touched={list(data['touched'])} writes={len(box.writes)}"
        )

    run = wct.WallboxControlTest(
        box,
        wct.Options(leave=leave, **options),
        clock=FakeClock(),
        on_snapshot=on_snapshot if snapshot else None,
    )
    return await run.async_run(), events


# -- the straight run -----------------------------------------------------------


async def test_the_scale_is_confirmed_and_everything_is_put_back() -> None:
    box = FakeWallbox()
    outcome, _events = await _run(box)

    assert outcome.code == 0
    assert [s.verdict for s in outcome.steps] == [wct.CONFIRMED] * 3
    assert box.holding == box.original
    assert all(row.restored for row in outcome.restores)


async def test_every_word_written_is_safe_at_either_scale() -> None:
    """The wrong reading may only offer less than meant, never ten times more."""
    box = FakeWallbox()
    await _run(box)

    out = [word for address, word in box.writes if address == wct.OUTPUT_CURRENT]
    steps = out[:-1]  # the last write is the restore
    assert steps == [60, 80, 100]
    assert max(steps) * wct.SCALE_THIS_PROJECT <= wct.DEFAULT_MAX_AMPS
    assert all(
        word * scale <= wct.DEFAULT_MAX_AMPS
        for word in steps
        for scale in (wct.SCALE_THIS_PROJECT, wct.SCALE_DISCUSSION_571)
    )


async def test_the_snapshot_is_flushed_before_the_first_write() -> None:
    box = FakeWallbox()
    _outcome, events = await _run(box)

    assert events[0] == "snapshot touched=[] writes=0"
    assert "touched=[21202] writes=0" in events[1]


async def test_the_cap_is_obeyed() -> None:
    box = FakeWallbox()
    await _run(box, max_amps=8.0)

    words = [w for a, w in box.writes if a == wct.OUTPUT_CURRENT][:-1]
    assert words == [60, 80]


# -- the scale error the test exists to find -------------------------------------


async def test_a_decade_error_is_found_before_a_single_write() -> None:
    """A setting of 1000 is 100 A at 0.1 A per count and 10 A at 0.01."""
    box = FakeWallbox(scale=0.01, setting=1000)
    outcome, _ = await _run(box)

    assert outcome.code == 4
    assert box.writes == []
    assert "0.01" in outcome.conditions["scale_before_writing"]


async def test_a_car_that_stops_when_offered_6_a_is_a_decade_error_too() -> None:
    """The step-level evidence: charging before, stopped by the first write."""
    box = FakeWallbox(scale=0.01, setting=160, until_first_write_reads_as=0.1)
    outcome, _ = await _run(box)

    assert outcome.code == 4
    assert outcome.steps[0].verdict == wct.DECADE
    # It stopped at the first step: no point offering more.
    assert len(outcome.steps) == 1
    # The last write is the restore; the steps never went past 100.
    assert max(w for _a, w in box.writes[:-1]) <= 100
    assert box.holding == box.original


# -- what it declines to do -------------------------------------------------------


async def test_no_leave_is_a_dry_run_that_writes_nothing() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, leave=False)

    assert box.writes == []
    assert outcome.code == 0
    assert outcome.conditions["dry_run"] == wct.DRY_RUN_MEANS
    assert outcome.steps == ()


async def test_no_snapshot_means_no_writes() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, snapshot=False)

    assert box.writes == []
    assert outcome.code == 2
    assert "snapshot" in outcome.conditions["guard"]


async def test_a_device_that_is_not_a_wallbox_is_left_alone() -> None:
    box = FakeWallbox(name="SH10RT")
    outcome, _ = await _run(box)

    assert box.writes == []
    assert outcome.code == 2


async def test_a_setting_above_the_rating_is_not_understood_and_not_touched() -> None:
    box = FakeWallbox(setting=5000, rated=320)
    outcome, _ = await _run(box)

    assert box.writes == []
    assert outcome.code == 2


async def test_without_a_car_only_the_plumbing_is_checked() -> None:
    box = FakeWallbox(charging=False)
    outcome, _ = await _run(box)

    assert outcome.code == 3
    assert [s.verdict for s in outcome.steps] == [wct.MATCHED] * 3
    assert any("no car" in sentence for sentence in outcome.unestablished)
    assert box.holding == box.original


# -- readback ------------------------------------------------------------------------


async def test_the_stale_same_session_read_does_not_fool_the_raw_leg() -> None:
    """The same session answered 4242; the fresh one told the truth."""
    box = FakeWallbox(stale=True)
    outcome, _ = await _run(box)

    assert outcome.code == 0


async def test_a_port_without_a_fresh_session_cannot_call_the_raw_leg_independent() -> (
    None
):
    box = FakeWallbox(fresh=False, stale=False)
    outcome, _ = await _run(box)

    assert outcome.code == 3
    assert any("not independent" in s for s in outcome.unestablished)


async def test_a_word_that_does_not_stay_is_a_mismatch_and_ends_the_steps() -> None:
    box = FakeWallbox()
    original_write = box.write

    async def lossy(address: int, word: int) -> None:
        # The register keeps a different word than was sent.
        await original_write(address, word)
        if word != box.original[address]:
            box.holding[address] = word + 1

    box.write = lossy  # type: ignore[method-assign]
    outcome, _ = await _run(box)

    assert outcome.steps[0].verdict == wct.MISMATCH
    assert len(outcome.steps) == 1
    assert outcome.code == 3
    assert box.holding == box.original


# -- refusal, loss and the restore -------------------------------------------------


async def test_a_refused_write_is_recorded_with_its_exception_and_nothing_is_left() -> (
    None
):
    box = FakeWallbox(refuse={wct.OUTPUT_CURRENT})
    outcome, _ = await _run(box)

    assert outcome.steps[0].verdict == wct.REFUSED
    assert "ModbusExceptionError" in outcome.conditions["refusals"][wct.OUTPUT_CURRENT]
    assert outcome.code == 3
    assert box.holding == box.original


async def test_a_link_lost_mid_run_still_restores() -> None:
    box = FakeWallbox(drop_writes_after=1)
    outcome, _ = await _run(box)

    assert outcome.steps[-1].verdict == wct.DROPPED
    assert box.holding == box.original or outcome.code == 5


async def test_a_restore_that_cannot_land_is_code_5_and_is_tried_again() -> None:
    box = FakeWallbox(restore_fails=True)
    outcome, _ = await _run(box)

    assert outcome.code == 5
    assert outcome.not_restored
    assert outcome.not_restored[0].attempts == wct.RESTORE_ATTEMPTS


async def test_a_cancelled_run_still_finishes_its_restore() -> None:
    box = FakeWallbox()
    run = wct.WallboxControlTest(
        box, wct.Options(leave=True), clock=FakeClock(), on_snapshot=_noop_snapshot
    )
    task = asyncio.ensure_future(run.async_run())
    # Let it get into the steps, then cancel.
    for _ in range(40):
        await asyncio.sleep(0)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    assert box.holding == box.original


async def _noop_snapshot(_data: dict[str, Any]) -> None:
    return None


# -- start and stop --------------------------------------------------------------


async def test_start_stop_runs_only_when_asked_and_resumes_the_charge() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, start_stop=True)

    names = [s.name for s in outcome.steps]
    assert "start/stop" in names
    assert outcome.steps[-1].verdict == wct.CONFIRMED
    assert box.holding == box.original


async def test_start_stop_is_not_run_by_default() -> None:
    box = FakeWallbox()
    await _run(box)

    assert all(a != wct.START_STOP for a, _w in box.writes)


async def test_start_stop_is_skipped_when_the_register_is_not_a_state() -> None:
    """Reading 1 ("stop") while a car charges means it is not a state.

    Measured at gerd's: start/stop read 1 on a wallbox whose charge had
    finished. A register that reads "stop" while the car charges cannot be
    the start/stop state, so its polarity is unknown and it is not written.
    """
    box = FakeWallbox(start_stop=1, ignores_start_stop=True)
    outcome, _ = await _run(box, start_stop=True)

    assert all(a != wct.START_STOP for a, _w in box.writes)
    step = next(s for s in outcome.steps if s.name == "start/stop")
    assert step.verdict == wct.SKIPPED
    assert "polarity" in step.detail
    assert outcome.code == 3


def test_the_candidate_scales_are_typed_here_and_not_read_from_the_library() -> None:
    from sungrow_modbus.wallbox.registers import WallboxSettings

    field = WallboxSettings.declared_fields["output_current_setting"]
    # They meet: the library's scale is one of the two hypotheses, and the
    # hypotheses are not derived from it.
    assert field.scale in (wct.SCALE_THIS_PROJECT, wct.SCALE_DISCUSSION_571)
    assert math.isclose(wct.SCALE_THIS_PROJECT, 0.1)
    assert math.isclose(wct.SCALE_DISCUSSION_571, 0.01)


# -- enable and phase -------------------------------------------------------------


async def test_enable_is_not_run_by_default() -> None:
    box = FakeWallbox()
    await _run(box)

    assert all(a not in (wct.ENABLED, wct.PHASE_SETPOINT) for a, _w in box.writes)


@pytest.mark.parametrize("charging", [True, False])
async def test_disable_and_enable_are_seen_with_or_without_a_car(
    charging: bool,
) -> None:
    box = FakeWallbox(charging=charging)
    outcome, _ = await _run(box, enable=True)

    step = next(s for s in outcome.steps if s.name == "enable")
    assert step.verdict == wct.CONFIRMED
    words = [w for a, w in box.writes if a == wct.ENABLED]
    assert words[:2] == [wct.DISABLED_WORD, wct.ENABLED_WORD]
    assert box.holding == box.original


async def test_enable_is_skipped_when_the_register_already_reads_disabled() -> None:
    box = FakeWallbox(enabled=0)
    outcome, _ = await _run(box, enable=True)

    assert all(a != wct.ENABLED for a, _w in box.writes)
    assert any(s.name == "enable" and s.verdict == wct.SKIPPED for s in outcome.steps)


async def test_the_phase_is_never_switched_with_a_car_charging() -> None:
    box = FakeWallbox(charging=True)
    outcome, _ = await _run(box, phase=True)

    assert all(a != wct.PHASE_SETPOINT for a, _w in box.writes)
    step = next(s for s in outcome.steps if s.name == "phase")
    assert step.verdict == wct.SKIPPED
    assert outcome.code == 3


async def test_the_phase_follows_when_nothing_is_flowing_and_is_put_back() -> None:
    box = FakeWallbox(charging=False, phase=0)
    outcome, _ = await _run(box, phase=True)

    step = next(s for s in outcome.steps if s.name == "phase")
    assert step.verdict == wct.CONFIRMED
    written = [w for a, w in box.writes if a == wct.PHASE_SETPOINT]
    assert written[0] == 1  # the other of the two words, and only those two
    assert set(written) <= {0, 1}
    assert box.holding == box.original


async def test_a_phase_that_does_not_follow_is_inconclusive_and_still_restored() -> (
    None
):
    """A single-phase unit takes the write and stays single phase."""
    box = FakeWallbox(charging=False, phase=1, phase_follows=False)
    outcome, _ = await _run(box, phase=True)

    step = next(s for s in outcome.steps if s.name == "phase")
    assert step.verdict == wct.INCONCLUSIVE
    assert outcome.code == 3
    assert box.holding == box.original


async def test_a_setting_that_cannot_be_read_is_not_written() -> None:
    """A lost read is not a refusal, and nothing is written that cannot be put back."""
    box = FakeWallbox(charging=False)
    real = box.read

    async def read(space: str, address: int, count: int) -> list[int]:
        if space == "holding" and address == wct.PHASE_SETPOINT:
            raise TimeoutError("no answer")
        return await real(space, address, count)

    box.read = read  # type: ignore[method-assign]
    outcome, _ = await _run(box, phase=True)

    assert all(a != wct.PHASE_SETPOINT for a, _w in box.writes)
    assert "phase" in outcome.conditions["unreadable"]
    assert any(s.name == "phase" and s.verdict == wct.SKIPPED for s in outcome.steps)


async def test_a_setting_of_0_is_not_written_over() -> None:
    """Idle at gerd's the setting read 0; its meaning is not established."""
    box = FakeWallbox(charging=False, setting=0)
    outcome, _ = await _run(box)

    assert box.writes == []
    assert outcome.code == 2
    assert "reads 0" in outcome.conditions["guard"]


async def test_a_setting_of_0_still_allows_a_dry_run() -> None:
    box = FakeWallbox(charging=False, setting=0)
    outcome, _ = await _run(box, leave=False)

    assert box.writes == []
    assert outcome.code == 0


# -- the paths that decide whether a charger is left changed -----------------------


def _refuse_the_nth_write_to(box: FakeWallbox, address: int, n: int) -> None:
    """Refuse the n-th write to one address (1-based), as the device would."""
    real = box.write
    seen = {"count": 0}

    async def write(at: int, word: int) -> None:
        if at == address:
            seen["count"] += 1
            if seen["count"] == n:
                raise ModbusExceptionError(4, "illegal data value")
        await real(at, word)

    box.write = write  # type: ignore[method-assign]


async def test_a_model_name_that_cannot_be_read_is_code_1_and_nothing_is_written() -> (
    None
):
    box = FakeWallbox()
    real = box.read

    async def read(space: str, address: int, count: int) -> list[int]:
        if address == MODEL_NAME.address:
            raise TimeoutError("no answer")
        return await real(space, address, count)

    box.read = read  # type: ignore[method-assign]
    outcome, _ = await _run(box)

    assert outcome.code == 1
    assert box.writes == []


async def test_a_wallbox_reporting_a_fault_is_left_alone() -> None:
    box = FakeWallbox()
    real = box._words

    def words(space: str, address: int, count: int) -> list[int]:
        if space == "input" and address == wct.CHARGING_STATUS_ADDRESS:
            return [9]
        return real(space, address, count)

    box._words = words  # type: ignore[method-assign]
    outcome, _ = await _run(box)

    assert outcome.code == 2
    assert box.writes == []


@pytest.mark.parametrize("max_amps", [0.0, -1.0])
async def test_a_cap_that_is_not_positive_is_refused(max_amps: float) -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, max_amps=max_amps)

    assert outcome.code == 2
    assert box.writes == []


async def test_a_cap_below_the_lowest_step_writes_nothing() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, max_amps=5.0)

    assert outcome.code == 3
    assert box.writes == []
    assert any("below the lowest step" in s for s in outcome.unestablished)


async def test_a_link_lost_mid_run_is_reported_and_the_restore_still_runs() -> None:
    box = FakeWallbox()
    real = box.read
    reads = {"n": 0}

    async def read(space: str, address: int, count: int) -> list[int]:
        reads["n"] += 1
        if reads["n"] == 12:  # after the first write
            raise TimeoutError("the link dropped")
        return await real(space, address, count)

    box.read = read  # type: ignore[method-assign]
    outcome, _ = await _run(box)

    assert outcome.conditions["guard"] == "the wallbox stopped answering"
    assert outcome.code in (3, 5)
    assert box.holding == box.original


async def test_a_car_that_limits_itself_leaves_the_scale_unsettled() -> None:
    """Offered 6 A and up, a car that takes 3 A says nothing about the scale."""
    box = FakeWallbox(car_max_a=3.0)
    outcome, _ = await _run(box)

    assert [s.verdict for s in outcome.steps] == [wct.INCONCLUSIVE] * 3
    assert outcome.code == 3
    assert any("did not settle the scale" in s for s in outcome.unestablished)
    assert box.holding == box.original


async def test_a_draw_that_cannot_separate_the_readings_is_said_so() -> None:
    """A car drawing 1 A against a setting of 160 fits 16 A and 1.6 A alike."""
    box = FakeWallbox(car_max_a=1.0)
    outcome, _ = await _run(box, leave=False)

    assert any("does not separate" in s for s in outcome.unestablished)
    assert box.writes == []


async def test_a_refused_stop_ends_the_step_and_nothing_is_left() -> None:
    box = FakeWallbox()
    _refuse_the_nth_write_to(box, wct.START_STOP, 1)
    outcome, _ = await _run(box, start_stop=True)

    step = next(s for s in outcome.steps if s.name == "stop")
    assert step.verdict == wct.REFUSED
    assert outcome.code == 3
    assert box.holding == box.original


async def test_a_refused_start_is_still_put_back_by_the_restore() -> None:
    """Stopped, and the start refused: the restore writes the original 0 again."""
    box = FakeWallbox()
    _refuse_the_nth_write_to(box, wct.START_STOP, 2)
    outcome, _ = await _run(box, start_stop=True)

    step = next(s for s in outcome.steps if s.name == "start")
    assert step.verdict == wct.REFUSED
    assert box.holding[wct.START_STOP] == wct.START_WORD
    assert all(row.restored for row in outcome.restores)


async def test_a_wallbox_that_ignores_stop_is_inconclusive() -> None:
    box = FakeWallbox(ignores_start_stop=True)
    outcome, _ = await _run(box, start_stop=True)

    step = next(s for s in outcome.steps if s.name == "start/stop")
    assert step.verdict == wct.INCONCLUSIVE
    assert outcome.code == 3


async def test_start_stop_without_a_car_is_skipped() -> None:
    box = FakeWallbox(charging=False)
    outcome, _ = await _run(box, start_stop=True)

    assert all(a != wct.START_STOP for a, _w in box.writes)
    assert any(
        s.name == "start/stop" and s.verdict == wct.SKIPPED for s in outcome.steps
    )


async def test_an_enable_register_that_cannot_be_read_is_not_written() -> None:
    box = FakeWallbox(charging=False)
    real = box.read

    async def read(space: str, address: int, count: int) -> list[int]:
        if space == "holding" and address == wct.ENABLED:
            raise TimeoutError("no answer")
        return await real(space, address, count)

    box.read = read  # type: ignore[method-assign]
    outcome, _ = await _run(box, enable=True)

    assert all(a != wct.ENABLED for a, _w in box.writes)
    assert any(s.name == "enable" and s.verdict == wct.SKIPPED for s in outcome.steps)


async def test_a_refused_disable_ends_the_step() -> None:
    box = FakeWallbox(charging=False)
    _refuse_the_nth_write_to(box, wct.ENABLED, 1)
    outcome, _ = await _run(box, enable=True)

    step = next(s for s in outcome.steps if s.name == "disable")
    assert step.verdict == wct.REFUSED
    assert box.holding == box.original


async def test_a_refused_re_enable_is_put_back_by_the_restore() -> None:
    """The one that matters: a charge point left disabled would stop every charge."""
    box = FakeWallbox(charging=False)
    _refuse_the_nth_write_to(box, wct.ENABLED, 2)
    outcome, _ = await _run(box, enable=True)

    step = next(s for s in outcome.steps if s.name == "enable")
    assert step.verdict == wct.REFUSED
    assert box.holding[wct.ENABLED] == wct.ENABLED_WORD
    assert all(row.restored for row in outcome.restores)


async def test_a_wallbox_that_ignores_disable_is_inconclusive() -> None:
    box = FakeWallbox(charging=False, ignores_enable=True)
    outcome, _ = await _run(box, enable=True)

    step = next(s for s in outcome.steps if s.name == "enable")
    assert step.verdict == wct.INCONCLUSIVE
    assert box.holding == box.original


async def test_a_refused_phase_write_ends_the_step() -> None:
    box = FakeWallbox(charging=False)
    _refuse_the_nth_write_to(box, wct.PHASE_SETPOINT, 1)
    outcome, _ = await _run(box, phase=True)

    step = next(s for s in outcome.steps if s.name == "phase")
    assert step.verdict == wct.REFUSED
    assert box.holding == box.original


async def test_a_restore_whose_check_read_fails_is_tried_again_and_reported() -> None:
    """A restore is a statement about where the register is: no read, no claim."""
    box = FakeWallbox()
    real = box.read_fresh
    state = {"restoring": False}
    real_write = box.write

    async def write(address: int, word: int) -> None:
        if word == box.original.get(address) and box.writes:
            state["restoring"] = True
        await real_write(address, word)

    async def read_fresh(space: str, address: int, count: int) -> list[int]:
        if state["restoring"]:
            raise TimeoutError("no answer")
        return await real(space, address, count)

    box.write = write  # type: ignore[method-assign]
    box.read_fresh = read_fresh  # type: ignore[method-assign]
    outcome, _ = await _run(box)

    assert outcome.code == 5
    assert outcome.not_restored
    assert outcome.not_restored[0].attempts == wct.RESTORE_ATTEMPTS
