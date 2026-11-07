"""The capability test's timed windows: forced charging and the discharge schedules.

Both write a schedule and judge it by what the battery then does, and both must
leave every word of the schedule exactly where they found it. The mock inverter
here reacts the way the checks assume a real one does -- a forced-charging
window around now starts a charge, discharge windows away from now stop a
discharge -- so what is tested is the procedure: when it runs, what it writes,
in what order, and that the restore puts each word back.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter
from sungrow_modbus.capability_test import CONFIRMED, CapabilityTest, Options
from sungrow_modbus.capability_test.procedure import (
    CHARGE_WINDOW,
    DISCHARGE_WINDOW,
    Sample,
    inverter_clock,
    window_around,
    window_away,
)

#: Protocol addresses, one below the registers.
CLOCK = 4999  # holding 5000-5005
BATTERY_POWER = 5213  # input 5214-5215, int32 low word first
SOC = 13022  # input 13023, 0.1 %
MAX_SOC = 13057  # holding 13058, 0.1 %
CHARGE_ENABLE = 33207  # holding 33208
CHARGE_BLOCK = range(33207, 33219)  # holding 33208-33219
WEEKDAY = range(33150, 33158)  # holding 33151-33158
WEEKEND_ENABLE = 33178  # holding 33179
WEEKEND = range(33179, 33187)  # holding 33180-33187


class FakeClock:
    """A clock that agrees to anything, so a budget costs no time."""

    def __init__(self) -> None:
        """Start at an arbitrary origin."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Advance instead of waiting."""
        self.now += seconds


def _battery(unit: MockModbusUnit, watts: int) -> None:
    """Set battery power; negative is charging, as the inverter reports it."""
    word = watts & 0xFFFFFFFF
    unit.input[BATTERY_POWER] = word & 0xFFFF
    unit.input[BATTERY_POWER + 1] = word >> 16


@pytest.fixture
def house(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an SH10RT at 50 %, 14:00 on a Saturday, scheduled as peter-sm's."""
    unit = sungrow_unit
    unit.holding.update(
        dict(zip(range(CLOCK, CLOCK + 6), (2026, 10, 31, 14, 0, 0), strict=True))
    )
    unit.input[SOC] = 500
    unit.holding[MAX_SOC] = 1000
    _battery(unit, 0)
    # Forced charging off, every day, both windows unused, targets 0.
    unit.holding.update({**dict.fromkeys(CHARGE_BLOCK, 0), CHARGE_ENABLE: 0x55})
    unit.holding[CHARGE_ENABLE + 1] = 1
    # Discharge allowed all day on both days, the second windows unused.
    for block in (WEEKDAY, WEEKEND):
        unit.holding.update(dict(zip(block, (0, 0, 24, 0, 0, 0, 0, 0), strict=True)))
    unit.holding[WEEKEND_ENABLE] = 0xAA
    return unit


async def _run(unit: MockModbusUnit, **options: Any) -> CapabilityTest:
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = CapabilityTest(inverter, options=Options(**options), clock=FakeClock())
    run._plan_budget()
    await run._preflight()
    return run


# -- the arithmetic ----------------------------------------------------------


def test_the_inverter_clock_decodes_and_refuses_a_non_date() -> None:
    assert inverter_clock([2026, 10, 31, 14, 5, 9]) == datetime(2026, 10, 31, 14, 5, 9)  # noqa: DTZ001
    assert inverter_clock([2026, 13, 31, 14, 5, 9]) is None
    assert inverter_clock([2026, 10]) is None


def test_a_window_around_now_never_crosses_midnight() -> None:
    assert window_around(datetime(2026, 10, 31, 14, 0), 5, 20) == (13, 55, 14, 20)  # noqa: DTZ001
    assert window_around(datetime(2026, 10, 31, 0, 2), 5, 20) is None  # noqa: DTZ001
    assert window_around(datetime(2026, 10, 31, 23, 50), 5, 20) is None  # noqa: DTZ001


@pytest.mark.parametrize("hour", range(24))
def test_a_window_away_never_holds_now(hour: int) -> None:
    start_hour, start_minute, end_hour, end_minute = window_away(
        datetime(2026, 10, 31, hour, 30)  # noqa: DTZ001
    )
    now = hour * 60 + 30
    assert not start_hour * 60 + start_minute <= now < end_hour * 60 + end_minute


# -- leave ---------------------------------------------------------------------


async def test_without_leave_neither_schedule_is_read_or_written(
    house: MockModbusUnit,
) -> None:
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house)

    snapshotted = set(run.snapshot.raw)
    assert not snapshotted & {p.field for p in (*CHARGE_WINDOW, *DISCHARGE_WINDOW)}
    assert await run._charge_window_effect() == []
    assert await run._discharge_window_effect() == []
    assert not set(writes) & {*CHARGE_BLOCK, *WEEKDAY, *WEEKEND}


# -- the forced-charging window --------------------------------------------------


@pytest.fixture
def charges(house: MockModbusUnit) -> MockModbusUnit:
    """Charge at 2 kW while the forced-charging enable holds 0xAA."""

    def obey(event: Any) -> None:
        if event.address == CHARGE_ENABLE:
            _battery(house, -2000 if event.values[0] == 0xAA else 0)

    house.on_write(obey)
    return house


async def test_a_charge_window_around_now_starts_a_charge_and_goes_back(
    charges: MockModbusUnit,
) -> None:
    before = {address: charges.holding[address] for address in CHARGE_BLOCK}
    order: list[int] = []
    charges.on_write(lambda event: order.append(event.address))
    run = await _run(charges, charge_window=True)

    [result] = await run._charge_window_effect()
    restored = await run.async_restore()

    assert result.verdict == CONFIRMED
    assert run.conditions["inverter_clock"] == "2026-10-31T14:00:00"
    # The enable last on the way in, so nothing charges on a half-written window.
    written = [address for address in order if address in CHARGE_BLOCK]
    assert written.index(CHARGE_ENABLE) == len(set(written)) - 1
    assert all(row.restored for row in restored)
    assert {address: charges.holding[address] for address in CHARGE_BLOCK} == before


async def test_the_window_brackets_now_on_the_inverters_clock(
    charges: MockModbusUnit,
) -> None:
    seen: dict[int, int] = {}
    charges.on_write(lambda event: seen.update({event.address: event.values[0]}))
    run = await _run(charges, charge_window=True)

    await run._charge_window_effect()

    # 13:55-14:20, every day, to 60 % from 50 %.
    assert [seen[address] for address in range(33208, 33214)] == [1, 13, 55, 14, 20, 60]


async def test_the_owners_own_schedule_is_never_overwritten(
    charges: MockModbusUnit,
) -> None:
    charges.holding[CHARGE_ENABLE] = 0xAA
    writes: list[int] = []
    charges.on_write(lambda event: writes.append(event.address))
    run = await _run(charges, charge_window=True)

    assert await run._charge_window_effect() == []
    assert not set(writes) & set(CHARGE_BLOCK)
    assert any("owner's forced-charging schedule is on" in n for n in run.unestablished)


async def test_a_window_that_starts_nothing_is_no_effect(house: MockModbusUnit) -> None:
    run = await _run(house, charge_window=True)

    [result] = await run._charge_window_effect()

    assert result.verdict != CONFIRMED
    assert "did not start" in (result.detail or "")


# -- the discharge windows -------------------------------------------------------


@pytest.fixture
def discharges(house: MockModbusUnit) -> MockModbusUnit:
    """Discharge 1.5 kW while any window holds 14:00, nothing otherwise."""

    def obey(_event: Any) -> None:
        open_now = any(
            house.holding[block[start]] * 60 + house.holding[block[start] + 1]
            <= 14 * 60
            < house.holding[block[start] + 2] * 60 + house.holding[block[start] + 3]
            for block in (WEEKDAY, WEEKEND)
            for start in (0, 4)
        )
        _battery(house, 1500 if open_now else 0)

    _battery(house, 1500)
    house.on_write(obey)
    return house


async def test_moving_the_discharge_windows_stops_a_discharge_and_goes_back(
    discharges: MockModbusUnit,
) -> None:
    before = {a: discharges.holding[a] for a in (*WEEKDAY, WEEKEND_ENABLE, *WEEKEND)}
    run = await _run(discharges, discharge_window=True)

    [result] = await run._discharge_window_effect()
    restored = await run.async_restore()

    assert result.verdict == CONFIRMED
    assert all(row.restored for row in restored)
    after = {a: discharges.holding[a] for a in (*WEEKDAY, WEEKEND_ENABLE, *WEEKEND)}
    assert after == before


async def test_the_weekend_enable_is_never_written(discharges: MockModbusUnit) -> None:
    writes: list[int] = []
    discharges.on_write(lambda event: writes.append(event.address))
    run = await _run(discharges, discharge_window=True)

    await run._discharge_window_effect()
    await run.async_restore()

    assert WEEKEND_ENABLE not in writes
    assert set(writes) & set(WEEKDAY) and set(writes) & set(WEEKEND)


async def test_a_battery_not_discharging_is_not_written(house: MockModbusUnit) -> None:
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house, discharge_window=True)

    assert await run._discharge_window_effect() == []
    assert not set(writes) & {*WEEKDAY, *WEEKEND}
    assert any("discharging 0 W" in note for note in run.unestablished)


# -- the start bracket -----------------------------------------------------------


def _charge_script(run: CapabilityTest, *windows: list[float]) -> None:
    """Script battery charge power, window by window; positive is charging."""
    values = iter([value for window in windows for value in window])
    last = windows[-1][-1]

    async def sample() -> Sample:
        return Sample(
            at=run.clock.monotonic(),
            pv=1000.0,
            battery=-next(values, last),
            export=0.0,
            load=1000.0,
            soc=50.0,
        )

    run._sample = sample  # type: ignore[method-assign]


@pytest.mark.parametrize(
    ("before", "during", "after"),
    [(772.0, 4499.0, -245.5), (2218.0, 4399.5, 1875.0), (1216.0, 4100.0, -1912.0)],
    ids=["mkaiser-p020", "gerd-p022", "bar12-p023-dongle"],
)
async def test_a_window_above_both_neighbours_is_judged_by_its_bracket(
    house: MockModbusUnit, before: float, during: float, after: float
) -> None:
    """Three runs of 2026-11-01: the house moved after the window, not in it."""
    run = await _run(house, charge_window=True)
    _charge_script(run, [before] * 11, [during] * 10, [after] * 10)

    [result] = await run._charge_window_effect()

    assert result.verdict == CONFIRMED
    assert not any("forced-charging window" in note for note in run.unestablished)


async def test_a_window_under_its_after_neighbour_still_answers_to_drift(
    house: MockModbusUnit,
) -> None:
    """A rise the house could have made on its own proves nothing."""
    run = await _run(house, charge_window=True)
    _charge_script(run, [500.0] * 11, [2500.0] * 10, [2400.0] * 10)

    [result] = await run._charge_window_effect()

    assert result.verdict != CONFIRMED
    assert any("W different afterwards" in note for note in run.unestablished)
