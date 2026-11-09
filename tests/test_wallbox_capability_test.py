"""The wallbox capability test, against a wallbox that can be wrong where it matters.

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

from sungrow_modbus.wallbox import capability_test as wct
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
        refuse_below_a: float | None = None,
        clamp_to_rating: bool = True,
        available_offset_a: float = 0.0,
        mileage: int = 70,
        stays_on_after_stop: bool = False,
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
        self.refuse_below_a = refuse_below_a
        self.clamp_to_rating = clamp_to_rating
        self.available_offset_a = available_offset_a
        self.stays_on_after_stop = stays_on_after_stop
        self.holding[wct.MILEAGE] = mileage
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
        single = self.holding[wct.PHASE_SETPOINT] == 1 and self.phase_follows
        other = 0 if single else counts
        word = self.holding[wct.OUTPUT_CURRENT]
        if self.clamp_to_rating:
            word = min(word, self.rated)
        available = word + round(self.available_offset_a / wct.SCALE_THIS_PROJECT)
        table: dict[int, int] = {
            wct.RATED_CURRENT: self.rated,
            wct.PHASE_ACTUAL: (
                self.holding[wct.PHASE_SETPOINT]
                if self.phase_follows
                else self.fixed_phase
            ),
            wct.PHASE_A_CURRENT: counts,
            wct.PHASE_B_CURRENT: other,
            wct.PHASE_C_CURRENT: other,
            wct.CHARGING_POWER: round(amps * 230 * 3) & 0xFFFF,
            wct.CHARGING_POWER + 1: round(amps * 230 * 3) >> 16,
            wct.CHARGING_STATUS_ADDRESS: status,
            wct.AVAILABLE_CURRENT: available,
        }
        return [table.get(address + i, 0) for i in range(count)]

    async def write(self, address: int, word: int) -> None:
        """Write a word, or refuse, or lose the link."""
        if address in self.refuse:
            raise ModbusExceptionError(4, "illegal data value")
        if (
            address == wct.OUTPUT_CURRENT
            and self.refuse_below_a is not None
            and word * wct.SCALE_THIS_PROJECT < self.refuse_below_a
        ):
            raise ModbusExceptionError(3, "illegal data value")
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

    run = wct.WallboxCapabilityTest(
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
    run = wct.WallboxCapabilityTest(
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


# -- the checks a charging session can answer -----------------------------------


def _verdicts(outcome: wct.Outcome) -> dict[str, str]:
    return {step.name: step.verdict for step in outcome.steps}


async def test_the_offer_is_followed_across_the_range_and_back() -> None:
    box = FakeWallbox(setting=160)
    outcome, _ = await _run(box, follow=True, max_amps=12.0, cap_explicit=True)

    assert _verdicts(outcome)["current follow"] == wct.CONFIRMED
    rows = outcome.conditions["follow"]
    assert [r["offered_a"] for r in rows] == [6.0, 8.0, 10.0, 12.0, 10.0, 8.0, 6.0]
    assert [r["direction"] for r in rows] == ["up"] * 4 + ["down"] * 3
    assert all(r["seconds"] is not None for r in rows)
    assert box.holding == box.original
    assert outcome.code == 0


async def test_a_car_that_stops_following_is_the_cars_limit_not_a_failure() -> None:
    box = FakeWallbox(setting=160, car_max_a=9.0)
    outcome, _ = await _run(box, follow=True, max_amps=14.0, cap_explicit=True)

    assert _verdicts(outcome)["current follow"] == wct.CONFIRMED
    assert any(r["limited"] for r in outcome.conditions["follow"])
    assert "stopped following" in next(
        s.detail for s in outcome.steps if s.name == "current follow"
    )


async def test_follow_needs_a_car() -> None:
    box = FakeWallbox(charging=False)
    outcome, _ = await _run(box, follow=True)

    assert _verdicts(outcome)["current follow"] == wct.SKIPPED
    assert outcome.code == 3


async def test_available_current_is_compared_with_the_setting() -> None:
    box = FakeWallbox(setting=160, available_offset_a=1.0)
    outcome, _ = await _run(box, follow=True, max_amps=10.0, cap_explicit=True)

    step = next(s for s in outcome.steps if s.name == "available current")
    assert step.verdict == wct.CONFIRMED
    assert "plus 1 A" in step.detail


async def test_an_available_current_that_is_nothing_known_is_inconclusive() -> None:
    box = FakeWallbox(setting=160, available_offset_a=3.5)
    outcome, _ = await _run(box, follow=True, max_amps=10.0, cap_explicit=True)

    step = next(s for s in outcome.steps if s.name == "available current")
    assert step.verdict == wct.INCONCLUSIVE


async def test_an_offer_below_the_minimum_pauses_the_car_and_it_resumes() -> None:
    box = FakeWallbox(setting=160)
    outcome, _ = await _run(box, below_minimum=True, max_amps=10.0, cap_explicit=True)

    assert _verdicts(outcome)["below minimum"] == wct.CONFIRMED
    results = outcome.conditions["below_minimum"]
    assert set(results) == {"5.0 A", "0"}
    assert all("paused" in what and "resumed" in what for what in results.values())
    assert box.holding == box.original


async def test_an_offer_below_the_minimum_may_be_refused() -> None:
    box = FakeWallbox(setting=160, refuse_below_a=6.0)
    outcome, _ = await _run(box, below_minimum=True, max_amps=10.0, cap_explicit=True)

    assert _verdicts(outcome)["below minimum"] == wct.CONFIRMED
    assert all(
        what.startswith("refused")
        for what in outcome.conditions["below_minimum"].values()
    )
    assert all(row.restored for row in outcome.restores)


async def test_below_minimum_is_not_run_on_a_default_cap() -> None:
    box = FakeWallbox(setting=160)
    outcome, _ = await _run(box, below_minimum=True)

    assert _verdicts(outcome)["below minimum"] == wct.SKIPPED
    assert not any(w < 60 for a, w in box.writes if a == wct.OUTPUT_CURRENT)


async def test_above_the_rating_is_clamped_or_not_and_the_setting_goes_back() -> None:
    clamped, _ = await _run(
        FakeWallbox(setting=160, clamp_to_rating=True),
        above_rating=True,
        max_amps=32.0,
        cap_explicit=True,
    )
    free_box = FakeWallbox(setting=160, clamp_to_rating=False)
    free, _ = await _run(free_box, above_rating=True, max_amps=32.0, cap_explicit=True)

    assert _verdicts(clamped)["above rating"] == wct.CLAMPED
    assert _verdicts(free)["above rating"] == wct.NOT_CLAMPED
    offered = [w for a, w in free_box.writes if a == wct.OUTPUT_CURRENT]
    assert 330 in offered
    # The house's own word is written straight after, before the final restore.
    assert offered[offered.index(330) + 1] == 160


async def test_above_the_rating_never_exceeds_the_owners_cap() -> None:
    box = FakeWallbox(setting=160)
    outcome, _ = await _run(box, above_rating=True, max_amps=10.0, cap_explicit=True)

    assert _verdicts(outcome)["above rating"] == wct.SKIPPED
    stepped = [w for a, w in box.writes if a == wct.OUTPUT_CURRENT][:-1]
    assert max(stepped, default=0) <= 100


async def test_above_the_rating_refused() -> None:
    box = FakeWallbox(setting=160)

    class Refusing(FakeWallbox):
        async def write(self, address: int, word: int) -> None:
            if address == wct.OUTPUT_CURRENT and word > self.rated:
                raise ModbusExceptionError(3, "illegal data value")
            await super().write(address, word)

    refusing = Refusing(setting=160)
    outcome, _ = await _run(
        refusing, above_rating=True, max_amps=32.0, cap_explicit=True
    )

    assert _verdicts(outcome)["above rating"] == wct.REFUSED
    assert box.writes == []
    assert refusing.holding == refusing.original


async def test_start_stop_and_enable_are_timed() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, start_stop=True, enable=True)

    assert set(outcome.conditions["start_stop_seconds"]) == {"stop", "resume"}
    assert outcome.conditions["start_stop_seconds"]["stop"] is not None
    assert outcome.conditions["enable_seconds"]["disable"] is not None


async def test_the_phase_is_switched_with_a_car_charging_in_evcc_order() -> None:
    box = FakeWallbox(setting=160)
    outcome, _ = await _run(box, phase_charging=True)

    assert _verdicts(outcome)["phase while charging"] == wct.CONFIRMED
    writes = [
        (a, w) for a, w in box.writes if a in (wct.START_STOP, wct.PHASE_SETPOINT)
    ]
    # stop, switch to single, start, stop, switch back, start, then the restore.
    assert writes[:6] == [
        (wct.START_STOP, wct.STOP_WORD),
        (wct.PHASE_SETPOINT, 1),
        (wct.START_STOP, wct.START_WORD),
        (wct.START_STOP, wct.STOP_WORD),
        (wct.PHASE_SETPOINT, 0),
        (wct.START_STOP, wct.START_WORD),
    ]
    assert box.holding == box.original


async def test_the_phase_is_never_written_before_the_stop_is_seen() -> None:
    box = FakeWallbox(setting=160, ignores_start_stop=True)
    outcome, _ = await _run(box, phase_charging=True)

    assert _verdicts(outcome)["phase while charging"] == wct.INCONCLUSIVE
    assert not [w for a, w in box.writes if a == wct.PHASE_SETPOINT]
    assert box.holding == box.original
    assert outcome.code == 3


async def test_a_restore_after_a_dead_run_stops_before_it_moves_the_phase() -> None:
    """A run that died mid-switch: the phase goes back only with the charge stopped."""
    box = FakeWallbox(setting=160)
    box.holding[wct.PHASE_SETPOINT] = 1
    box.holding[wct.START_STOP] = wct.START_WORD
    run = wct.WallboxCapabilityTest(box, wct.Options(), clock=FakeClock())
    run.snapshot = {
        "raw": {wct.PHASE_SETPOINT: 0, wct.START_STOP: wct.START_WORD},
        "touched": [wct.START_STOP, wct.PHASE_SETPOINT],
    }
    await run.async_restore()

    order = [(a, w) for a, w in box.writes]
    assert order[0] == (wct.START_STOP, wct.STOP_WORD)
    assert order.index((wct.PHASE_SETPOINT, 0)) > 0
    assert order[-1] == (wct.START_STOP, wct.START_WORD)
    assert all(row.restored for row in run.restores)


async def test_the_mileage_write_is_a_no_op_that_is_taken() -> None:
    box = FakeWallbox()
    outcome, _ = await _run(box, mileage=True)

    assert _verdicts(outcome)["mileage"] == wct.CONFIRMED
    assert (wct.MILEAGE, 70) in box.writes
    assert all(w == 70 for a, w in box.writes if a == wct.MILEAGE)


async def test_a_refused_mileage_write_is_a_finding_not_a_failure() -> None:
    box = FakeWallbox(refuse={wct.MILEAGE})
    outcome, _ = await _run(box, mileage=True)

    assert _verdicts(outcome)["mileage"] == wct.REFUSED
    assert outcome.code == 0


async def test_the_fallback_waits_in_silence_and_reports_what_the_car_is_given() -> (
    None
):
    box = FakeWallbox(setting=160)
    clock_times: list[float] = []

    class Timing(FakeWallbox):
        async def read(self, space: str, address: int, count: int) -> list[int]:
            clock_times.append(0.0)
            return await super().read(space, address, count)

    outcome, _ = await _run(box, fallback=True, max_amps=10.0, cap_explicit=True)

    step = next(s for s in outcome.steps if s.name == "fallback")
    assert step.verdict == wct.CONFIRMED
    assert outcome.conditions["fallback"]["silence_s"] == wct.SILENCE_SECONDS
    assert outcome.conditions["fallback"]["setting_after_word"] == 160
    assert box.holding == box.original


async def test_the_fallback_runs_only_with_the_setting_already_back() -> None:
    box = FakeWallbox(setting=160, restore_fails=True)
    outcome, _ = await _run(box, fallback=True, max_amps=10.0, cap_explicit=True)

    assert _verdicts(outcome)["fallback"] == wct.SKIPPED
    assert outcome.code in (3, 5)


async def test_the_fallback_is_not_run_with_a_cap_above_the_houses_setting() -> None:
    box = FakeWallbox(setting=80)
    outcome, _ = await _run(box, fallback=True, max_amps=10.0, cap_explicit=True)

    assert _verdicts(outcome)["fallback"] == wct.SKIPPED
    assert "above the setting" in next(
        s.detail for s in outcome.steps if s.name == "fallback"
    )


async def test_a_port_with_no_fresh_session_is_judged_by_the_car_alone() -> None:
    """Through a dongle or a shared session the readback is stale, not a mismatch."""
    box = FakeWallbox(fresh=False, stale=True)
    outcome, _ = await _run(box)

    assert [s.verdict for s in outcome.steps] == [wct.CONFIRMED] * 3
    assert any("not independent" in n for n in outcome.unestablished)
    assert outcome.code == 3
    assert box.holding == box.original
    assert all(row.restored for row in outcome.restores)


# -- the ledger and the plausibility checks --------------------------------------

from datetime import UTC, datetime, timedelta  # noqa: E402

from sungrow_modbus.wallbox import ledger, plausibility  # noqa: E402


async def _block(box: FakeWallbox, **options: Any) -> dict[str, Any]:
    outcome, _ = await _run(box, **options)
    return ledger.block(
        outcome,
        wct.Options(leave=True, **options),
        transport="tls",
        fresh=box.fresh,
    )


async def test_a_run_without_a_car_leaves_the_scale_missing_until_one_charges() -> None:
    idle = await _block(FakeWallbox(charging=False))
    folded = ledger.fold([idle])
    assert not folded["checks"]["output current"]["established"]
    assert folded["checks"]["output current"]["attempts"] == 0
    assert ledger.due(folded, ledger.Live(1, 0.0), {}) == []
    assert ledger.due(folded, ledger.Live(3, 9.0), {}) == ["output current"]

    charging = await _block(FakeWallbox())
    both = ledger.fold([idle, charging])
    assert both["checks"]["output current"]["established"]
    assert ledger.awaited(both, {}) == []


async def test_a_finding_outranks_a_later_pass() -> None:
    found = await _block(
        FakeWallbox(scale=0.01, setting=160, until_first_write_reads_as=0.1)
    )
    passed = await _block(FakeWallbox())
    folded = ledger.fold([found, passed])

    row = folded["checks"]["output current"]
    assert row["verdict"] == wct.DECADE
    assert row["contradicted_by"] == [wct.CONFIRMED]
    assert folded["code"] == 4


async def test_a_check_that_will_not_settle_is_given_up_after_three_tries() -> None:
    runs = [
        await _block(FakeWallbox(car_max_a=3.0, setting=160))
        for _ in range(ledger.MAX_ATTEMPTS)
    ]
    folded = ledger.fold(runs)

    assert not folded["checks"]["output current"]["established"]
    assert ledger.awaited(folded, {}) == []
    missing = ledger.still_missing(folded, {})
    assert "not settled after 3 tries" in missing[0]["why"]


async def test_options_decide_which_checks_are_awaited() -> None:
    folded = ledger.fold([await _block(FakeWallbox())])

    names = {
        name for name, _need in ledger.awaited(folded, {"follow": True, "phase": True})
    }
    assert names == {"current follow", "available current", "phase"}
    assert ledger.due(folded, ledger.Live(3, 9.0), {"follow": True, "phase": True}) == [
        "available current",
        "current follow",
    ]


def _reading(**changes: float) -> dict[str, float | None]:
    reading: dict[str, float | None] = {
        "phase_a_voltage": 230.0,
        "phase_b_voltage": 230.0,
        "phase_c_voltage": 230.0,
        "phase_a_current": 10.0,
        "phase_b_current": 10.0,
        "phase_c_current": 10.0,
        "charging_power": 6900.0,
        "session_energy": 1000.0,
        "lifetime_energy": 50000.0,
        "control_pilot_voltage": 6.0,
        "charging_status_raw": 3,
        "unnamed_register_21313": 527,
        "output_current_setting": 10.0,
    }
    reading.update(changes)
    return reading


def test_a_power_that_is_voltage_times_current_matches_and_a_decade_off_is_found() -> (
    None
):
    start = datetime(2026, 11, 9, 12, tzinfo=UTC)
    good, bad = plausibility.WallboxPlausibility(), plausibility.WallboxPlausibility()
    for i in range(25):
        at = start + timedelta(seconds=10 * i)
        good.observe(plausibility.values(_reading()), at)
        bad.observe(plausibility.values(_reading(charging_power=690.0 * 10)), at)
        bad.observe(plausibility.values(_reading(charging_power=69000.0)), at)

    name = "wallbox power times voltage and current"
    assert good.summary()[name]["verdict"] == "matched"
    assert bad.summary()[name]["verdict"] != "matched"


def test_a_counter_that_falls_during_a_session_is_reported_and_21313_is_logged() -> (
    None
):
    start = datetime(2026, 11, 9, 12, tzinfo=UTC)
    state = plausibility.WallboxPlausibility()
    state.observe(plausibility.values(_reading(session_energy=2000.0)), start)
    state.observe(
        plausibility.values(_reading(session_energy=1500.0, unnamed_register_21313=0)),
        start + timedelta(seconds=10),
    )

    row = state.summary()["wallbox energy counters never fall"]
    assert "fell from 2000 to 1500" in row["detail"]
    assert [entry["value"] for entry in state.log] == [527, 0]
    assert state.log[1]["status"] == 3


def test_the_plausibility_state_survives_a_restart() -> None:
    start = datetime(2026, 11, 9, 12, tzinfo=UTC)
    state = plausibility.WallboxPlausibility()
    for i in range(25):
        state.observe(
            plausibility.values(_reading()), start + timedelta(seconds=10 * i)
        )

    again = plausibility.WallboxPlausibility.from_dict(state.as_dict())
    assert again.summary() == state.summary()
    assert again.log == state.log
    assert again.document()["register_21313"] == state.document()["register_21313"]


def test_the_load_must_move_with_the_wallbox() -> None:
    start = datetime(2026, 11, 9, 12, tzinfo=UTC)
    state = plausibility.WallboxPlausibility()
    for i in range(8):
        power = 1500.0 if i % 2 == 0 else 6900.0
        state.observe(
            plausibility.values(_reading(charging_power=power), load_w=power + 400),
            start + timedelta(seconds=10 * i),
        )
    row = state.summary()["inverter load includes the wallbox"]
    assert row["verdict"] == "matched"
