"""The managed wallbox's capability test, against an inverter that acts as gerd's did.

`FakeHouse` is an SH8.0RT managing an AC22E-01 with a car on it, as measured on
2026-11-14 (wiki: `gerd-wallbox-inverter-control-2026-11-14-summary.md`):

* the user current is refused (exception 0x04) outside user-defined mode,
  and under 6 A;
* switching to user-defined mode switches charging on; leaving it for fast
  charge, or fast charge for PV surplus, ends the session;
* charging on starts a session again, unless the car has fallen asleep;
* the car draws about 0.5 A under what it is offered, up to its own limit.
"""

from __future__ import annotations

import asyncio
from typing import Any

from modbus_connection import ModbusExceptionError
import pytest

from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.wallbox import capability_test as wct, managed_test as mt
from sungrow_modbus.wallbox.discovery import MODEL_NAME

from .conftest import encode_string
from .test_wallbox_capability_test import FakeClock


class FakeHouse:
    """The inverter's block at unit 1 and the wallbox's live registers."""

    def __init__(
        self,
        *,
        mode: int = ev.FAST,
        user_current: int = 160,
        charging: bool = True,
        car_max_a: float = 16.0,
        rated: int = 320,
        floor_refused: bool = True,
        sleeps_after_stop: bool = False,
        restore_refused: bool = False,
        lose_inverter_after: int | None = None,
    ) -> None:
        """Set the house up; every argument is a way for it to be different."""
        self.block = {
            ev.CHARGING: ev.ON if charging else ev.OFF,
            ev.MODE: mode,
            ev.USER_CURRENT: user_current,
            ev.GRID_SURPLUS: ev.OFF,
        }
        self.original = dict(self.block)
        self.session = charging
        self.car_max_a = car_max_a
        self.rated = rated
        self.floor_refused = floor_refused
        self.sleeps_after_stop = sleeps_after_stop
        self.asleep = False
        self.restore_refused = restore_refused
        self.lose_inverter_after = lose_inverter_after
        self.writes: list[tuple[int, int]] = []

    # -- the car -------------------------------------------------------------

    def _offer_a(self) -> float:
        if self.block[ev.MODE] == ev.USER_DEFINED:
            return self.block[ev.USER_CURRENT] * ev.AMPS_PER_COUNT
        return self.rated * 0.1

    def _live(self) -> tuple[int, float]:
        if not self.session:
            return (5 if self.asleep else 6), 0.0
        return 3, max(0.0, min(self._offer_a(), self.car_max_a) - 0.5)

    # -- the inverter, unit 1 -------------------------------------------------

    async def read(self, address: int, count: int) -> list[int]:
        """Read the inverter's holding block."""
        return [self.block.get(address + i, 0) for i in range(count)]

    async def write(self, address: int, word: int) -> None:
        """Write as gerd's inverter answered."""
        if self.lose_inverter_after is not None and len(self.writes) >= (
            self.lose_inverter_after
        ):
            raise TimeoutError("the link dropped")
        if self.restore_refused and word == self.original.get(address) and self.writes:
            raise ModbusExceptionError(4, "server device failure")
        if address == ev.USER_CURRENT:
            if self.block[ev.MODE] != ev.USER_DEFINED:
                raise ModbusExceptionError(4, "server device failure")
            if word < 60 and self.floor_refused:
                raise ModbusExceptionError(4, "server device failure")
        self.writes.append((address, word))
        old = self.block.get(address)
        self.block[address] = word
        if address == ev.MODE:
            if word == ev.USER_DEFINED:
                self._on()
            elif (old, word) in ((ev.USER_DEFINED, ev.FAST), (ev.FAST, ev.PV_SURPLUS)):
                self.block[ev.CHARGING] = ev.OFF
                self.session = False
        elif address == ev.CHARGING:
            if word == ev.ON:
                self._on()
            else:
                self.session = False
                self.asleep = self.sleeps_after_stop

    def _on(self) -> None:
        self.block[ev.CHARGING] = ev.ON
        if not self.asleep:
            self.session = True


class WallboxSide:
    """The wallbox, read only."""

    def __init__(self, house: FakeHouse) -> None:
        """Read what the house's car is doing."""
        self.house = house

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Answer the model name, the rating, the status and the phase currents."""
        if address == MODEL_NAME.address:
            return encode_string("AC22E-01", MODEL_NAME.length)
        status, amps = self.house._live()
        table = {
            wct.RATED_CURRENT: self.house.rated,
            wct.CHARGING_STATUS_ADDRESS: status,
            wct.PHASE_A_CURRENT: round(amps * 10),
            wct.PHASE_B_CURRENT: round(amps * 10),
            wct.PHASE_C_CURRENT: round(amps * 10),
        }
        return [table.get(address + i, 0) for i in range(count)]


async def _run(
    house: FakeHouse, *, snapshot: bool = True, **options: Any
) -> tuple[mt.Outcome, list[str]]:
    events: list[str] = []

    async def on_snapshot(data: dict[str, Any]) -> None:
        events.append(f"snapshot writes={len(house.writes)}")

    options.setdefault("leave", True)
    run = mt.ManagedWallboxTest(
        house,
        WallboxSide(house),
        mt.Options(**options),
        clock=FakeClock(),
        on_snapshot=on_snapshot if snapshot else None,
    )
    return await run.async_run(), events


def _verdicts(outcome: mt.Outcome) -> dict[str, str]:
    return {step.name: step.verdict for step in outcome.steps}


# -- the straight run -------------------------------------------------------------


async def test_a_dry_run_reads_the_block_and_writes_nothing() -> None:
    house = FakeHouse()
    outcome, events = await _run(house, leave=False)

    assert outcome.code == 0
    assert house.writes == []
    assert events == []
    assert outcome.conditions["mode"] == "fast"
    assert outcome.conditions["user_current_a"] == 16.0
    assert outcome.conditions["dry_run"] == mt.DRY_RUN_MEANS


async def test_the_car_follows_each_user_current_and_the_house_is_put_back() -> None:
    house = FakeHouse()
    outcome, _ = await _run(house, start_stop=True)

    assert outcome.code == 0, outcome
    verdicts = _verdicts(outcome)
    for amps in (6, 8, 10):
        assert verdicts[f"user current {amps} A"] == mt.CONFIRMED
    assert verdicts["floor"] == mt.CONFIRMED
    assert verdicts["start/stop"] == mt.CONFIRMED
    assert outcome.restored
    assert house.block == house.original
    assert house.session


async def test_only_the_inverter_is_written_and_never_under_six_amperes_kept() -> None:
    house = FakeHouse()
    await _run(house)

    assert {address for address, _ in house.writes} <= {
        ev.CHARGING,
        ev.MODE,
        ev.USER_CURRENT,
    }


async def test_the_mode_is_switched_before_the_first_user_current() -> None:
    """In fast charge the inverter refuses the user current."""
    house = FakeHouse()
    await _run(house)

    assert house.writes[0] == (ev.MODE, ev.USER_DEFINED)


async def test_the_snapshot_is_kept_before_the_first_write() -> None:
    house = FakeHouse()
    _, events = await _run(house)

    assert events[0] == "snapshot writes=0"


async def test_the_restore_writes_the_current_before_leaving_user_defined_mode() -> (
    None
):
    """Then the mode, which ends the session, then charging on."""
    house = FakeHouse()
    run = mt.ManagedWallboxTest(
        house,
        WallboxSide(house),
        mt.Options(leave=True, floor=False),
        clock=FakeClock(),
    )

    async def keep(_data: dict[str, Any]) -> None:
        return None

    run._on_snapshot = keep
    await run.async_run()

    tail = house.writes[-3:]
    assert tail == [
        (ev.USER_CURRENT, 160),
        (ev.MODE, ev.FAST),
        (ev.CHARGING, ev.ON),
    ]
    assert house.session


async def test_a_house_already_in_user_defined_mode_keeps_it() -> None:
    house = FakeHouse(mode=ev.USER_DEFINED, user_current=100)
    outcome, _ = await _run(house)

    assert outcome.code == 0
    assert (ev.MODE, ev.USER_DEFINED) not in house.writes
    assert house.block == house.original


# -- what the car and the inverter can say -----------------------------------------


async def test_a_car_that_takes_less_is_its_own_limit() -> None:
    house = FakeHouse(car_max_a=7.0)
    outcome, _ = await _run(house)

    verdicts = _verdicts(outcome)
    assert verdicts["user current 6 A"] == mt.CONFIRMED
    assert verdicts["user current 10 A"] == mt.CAR_LIMIT
    assert outcome.code == 3
    assert house.block == house.original


async def test_an_inverter_that_takes_five_amperes_gets_six_back_at_once() -> None:
    house = FakeHouse(floor_refused=False)
    outcome, _ = await _run(house, current=False)

    assert _verdicts(outcome)["floor"] == mt.TAKEN
    assert house.writes[house.writes.index((ev.USER_CURRENT, 50)) + 1] == (
        ev.USER_CURRENT,
        60,
    )
    assert house.block == house.original


async def test_the_cap_never_goes_above_the_rating() -> None:
    house = FakeHouse(rated=80)
    outcome, _ = await _run(house, max_amps=32.0, floor=False)

    assert outcome.conditions["cap_a"] == 8.0
    offered = [row["offered_a"] for row in outcome.conditions["user_current"]]
    assert offered == [6.0, 8.0]


# -- when it cannot run -------------------------------------------------------------


async def test_without_a_car_charging_nothing_is_written() -> None:
    house = FakeHouse(charging=False)
    outcome, _ = await _run(house)

    assert outcome.code == 2
    assert house.writes == []


async def test_an_inverter_that_names_no_mode_manages_no_wallbox() -> None:
    house = FakeHouse(mode=0)
    outcome, _ = await _run(house)

    assert outcome.code == 2
    assert house.writes == []


async def test_without_a_snapshot_callback_nothing_is_written() -> None:
    house = FakeHouse()
    outcome, _ = await _run(house, snapshot=False)

    assert outcome.code == 2
    assert house.writes == []


# -- the restore ---------------------------------------------------------------------


async def test_a_car_asleep_after_the_stop_leaves_the_house_changed() -> None:
    """A 7-minute stop needed a replug at gerd's: code 5, and what to do on site."""
    house = FakeHouse(sleeps_after_stop=True)
    outcome, _ = await _run(house, current=False, floor=False, start_stop=True)

    assert _verdicts(outcome)["start/stop"] == mt.INCONCLUSIVE
    assert outcome.code == 5
    assert not outcome.restored
    assert outcome.conditions["on_site"] == mt.ON_SITE
    # The registers are back; the car is what is not.
    assert house.block == house.original


async def test_a_lost_link_mid_run_is_still_put_back() -> None:
    house = FakeHouse(lose_inverter_after=2)
    calls = {"n": 0}
    real = house.write

    async def write(address: int, word: int) -> None:
        calls["n"] += 1
        if calls["n"] == 3:
            raise TimeoutError("the link dropped")
        house.lose_inverter_after = None
        await real(address, word)

    house.write = write  # type: ignore[method-assign]
    outcome, _ = await _run(house)

    assert outcome.restored
    assert house.block == house.original
    assert outcome.code == 3


async def test_a_restore_the_inverter_refuses_is_code_five() -> None:
    house = FakeHouse(restore_refused=True)
    outcome, _ = await _run(house, floor=False)

    assert outcome.code == 5
    assert not outcome.restored


async def test_a_cancelled_run_still_puts_the_house_back() -> None:
    house = FakeHouse()

    class SlowClock(FakeClock):
        async def sleep(self, seconds: float) -> None:
            await super().sleep(seconds)
            await asyncio.sleep(0.01)

    async def keep(_data: dict[str, Any]) -> None:
        return None

    run = mt.ManagedWallboxTest(
        house,
        WallboxSide(house),
        mt.Options(leave=True, start_stop=True),
        clock=SlowClock(),
        on_snapshot=keep,
    )
    written = asyncio.Event()
    real_write = house.write

    async def write(address: int, word: int) -> None:
        await real_write(address, word)
        written.set()

    house.write = write  # type: ignore[method-assign]
    task = asyncio.ensure_future(run.async_run())
    await written.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert house.block == house.original
