"""The write-path checks: no-op writes, window 2, upper bounds, EMS options.

Each writes only what cannot change how the house runs, and puts the word
back. The mock inverter takes every write by default; a refusal is the real
exception type (`IllegalDataValueError`, 0x03), never a bare `ModbusError`,
because a refusal and a lost link are different answers.
"""

from __future__ import annotations

from typing import Any

from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter
from sungrow_modbus.capability_test import CapabilityTest, Options, ledger
from sungrow_modbus.capability_test.coverage import (
    CHECK_REVISIONS,
    EFFECT_FIELDS,
    WRITE_PATH_CHECKS,
)
from sungrow_modbus.capability_test.procedure import (
    CLAMPED,
    CONFIRMED,
    NO_EFFECT,
    REFUSED,
    bound_check,
    bounded_probes,
)
from sungrow_modbus.capability_test.writepath import EMS_CHECK, WINDOW_2_CHECK

#: Protocol addresses, one below the registers.
SOC = 13022  # input 13023, 0.1 %
MIN_SOC = 13058  # holding 13059, 0.1 %
MAX_SOC = 13057  # holding 13058, 0.1 %
EMS = 13049  # holding 13050
LOAD_MODE = 13001  # holding 13002
LOAD_ENABLE = 13010  # holding 13011
BACKUP = 13074  # holding 13075
CHARGE_ENABLE = 33207  # holding 33208
CHARGE_BLOCK = range(33207, 33219)  # holding 33208-33219
WINDOW_2 = range(33208, 33219)  # days, window 1, window 2, targets
WEEKEND_ENABLE = 33178  # holding 33179


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


@pytest.fixture
def house(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an SH10RT at 70 %, in self-consumption, the schedule off."""
    unit = sungrow_unit
    unit.input[SOC] = 700
    unit.holding[MIN_SOC] = 100
    unit.holding[MAX_SOC] = 1000
    unit.holding[EMS] = 0
    unit.holding[LOAD_MODE] = 3
    unit.holding[LOAD_ENABLE] = 0x55
    unit.holding[BACKUP] = 0x55
    unit.holding.update({**dict.fromkeys(CHARGE_BLOCK, 0), CHARGE_ENABLE: 0x55})
    unit.holding[WEEKEND_ENABLE] = 0xAA
    return unit


async def _run(unit: MockModbusUnit, **options: Any) -> CapabilityTest:
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = CapabilityTest(inverter, options=Options(**options), clock=FakeClock())
    run._plan_budget()
    await run._preflight()
    return run


def _refuse(unit: MockModbusUnit, address: int, when: Any = lambda _w: True) -> None:
    """Make one register answer 0x04 to the words `when` picks, keeping its word.

    The mock stores a word before its hooks run, so a refusal puts the word
    it held back first.
    """
    held = {"word": unit.holding[address]}

    def check(event: Any) -> None:
        if event.address != address:
            return
        if when(event.values[0]):
            unit.holding[address] = held["word"]
            raise IllegalDataValueError("refused")
        held["word"] = event.values[0]

    unit.on_write(check)


def _by_check(rows: list[Any]) -> dict[str, Any]:
    return {row.check: row for row in rows}


# -- the tables ----------------------------------------------------------------


def test_every_write_path_check_is_counted_and_awaited() -> None:
    """Named in the coverage, revised, and waited for by auto repeat."""
    assert set(WRITE_PATH_CHECKS) <= set(EFFECT_FIELDS)
    assert set(WRITE_PATH_CHECKS) <= set(CHECK_REVISIONS)
    assert set(WRITE_PATH_CHECKS) <= set(ledger.NEEDS)
    for name in WRITE_PATH_CHECKS:
        assert ledger.note_check(f"{name}: not run, for a reason") == name


def test_the_backup_reserve_and_the_export_limit_are_not_bounded() -> None:
    """A reserve above 100 % needs a battery above it; 13074 has its own probe."""
    fields = {probe.field for probe in bounded_probes()}
    assert "battery_reserved_soc_for_backup" not in fields
    assert "export_power_limit" not in fields
    assert "battery_max_soc" in fields


# -- no-op writes ------------------------------------------------------------------


async def test_a_no_op_write_hands_every_register_its_own_word(
    house: MockModbusUnit,
) -> None:
    writes: list[tuple[int, int]] = []
    house.on_write(lambda event: writes.append((event.address, event.values[0])))
    run = await _run(house, discharge_window=True)
    rows = _by_check(await run._write_paths())
    for check in (
        "backup mode write path",
        "load control write path",
        "weekend discharge enable write path",
    ):
        assert rows[check].verdict == CONFIRMED, rows[check]
    assert (BACKUP, 0x55) in writes
    assert (LOAD_ENABLE, 0x55) in writes
    assert (LOAD_MODE, 3) in writes
    assert (WEEKEND_ENABLE, 0xAA) in writes
    assert house.holding[BACKUP] == 0x55


async def test_a_refused_no_op_is_recorded_with_its_exception(
    house: MockModbusUnit,
) -> None:
    _refuse(house, BACKUP)
    run = await _run(house)
    row = _by_check(await run._write_paths())["backup mode write path"]
    assert row.verdict == REFUSED
    assert "IllegalDataValueError" in row.detail


async def test_without_leave_the_weekend_enable_is_not_read_or_written(
    house: MockModbusUnit,
) -> None:
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house)
    rows = _by_check(await run._write_paths())
    assert "weekend discharge enable write path" not in rows
    assert WEEKEND_ENABLE not in writes
    assert any(
        note.startswith("weekend discharge enable write path: not given leave")
        for note in run.unestablished
    )


# -- the second window -------------------------------------------------------------


async def test_window_2_reads_back_the_words_written_and_goes_back(
    house: MockModbusUnit,
) -> None:
    before = {address: house.holding[address] for address in CHARGE_BLOCK}
    run = await _run(house, charge_window=True)
    row = _by_check(await run._write_paths())[WINDOW_2_CHECK]
    assert row.verdict == CONFIRMED, row
    assert {address: house.holding[address] for address in CHARGE_BLOCK} == before


async def test_window_2_is_never_written_with_the_schedule_on(
    house: MockModbusUnit,
) -> None:
    house.holding[CHARGE_ENABLE] = 0xAA
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house, charge_window=True)
    assert WINDOW_2_CHECK not in _by_check(await run._write_paths())
    assert not set(writes) & set(WINDOW_2)
    note = next(n for n in run.unestablished if n.startswith(WINDOW_2_CHECK))
    assert ledger.needs_leave({"why": note})


async def test_window_2_needs_the_charge_windows_leave(house: MockModbusUnit) -> None:
    run = await _run(house)
    assert WINDOW_2_CHECK not in _by_check(await run._write_paths())
    assert not set(run.snapshot.raw) & {"forced_charging_start_2_hour"}


async def test_window_2_through_a_dongle_is_not_read_back(
    house: MockModbusUnit,
) -> None:
    run = await _run(house, charge_window=True)
    run.direct = False
    assert WINDOW_2_CHECK not in _by_check(await run._write_paths())


# -- upper bounds ------------------------------------------------------------------


async def test_a_bound_enforced_is_a_pass(house: MockModbusUnit) -> None:
    _refuse(house, MAX_SOC, when=lambda word: word > 1000)
    run = await _run(house)
    row = _by_check(await run._write_paths())[bound_check("battery_max_soc")]
    assert row.verdict == CONFIRMED
    assert "refused 101" in row.detail
    assert house.holding[MAX_SOC] == 1000


async def test_a_bound_not_enforced_is_named_and_put_back(
    house: MockModbusUnit,
) -> None:
    run = await _run(house)
    row = _by_check(await run._write_paths())[bound_check("battery_max_soc")]
    assert row.verdict == NO_EFFECT
    assert "not enforced" in row.detail
    assert house.holding[MAX_SOC] == 1000


async def test_a_bound_clamped_is_recorded(house: MockModbusUnit) -> None:
    def clamp(event: Any) -> None:
        if event.address == MAX_SOC and event.values[0] > 1000:
            house.holding[MAX_SOC] = 1000

    house.on_write(clamp)
    run = await _run(house)
    row = _by_check(await run._write_paths())[bound_check("battery_max_soc")]
    assert row.verdict == CLAMPED


async def test_a_floor_is_raised_past_its_maximum_only_under_a_full_battery(
    house: MockModbusUnit,
) -> None:
    house.input[SOC] = 520
    writes: list[tuple[int, int]] = []
    house.on_write(lambda event: writes.append((event.address, event.values[0])))
    run = await _run(house)
    rows = _by_check(await run._write_paths())
    assert bound_check("battery_min_soc") not in rows
    assert (MIN_SOC, 510) not in writes


# -- the EMS mode ------------------------------------------------------------------


async def test_each_ems_option_is_written_once_and_put_back(
    house: MockModbusUnit,
) -> None:
    writes: list[int] = []
    house.on_write(
        lambda event: writes.append(event.values[0]) if event.address == EMS else None
    )
    run = await _run(house)
    row = _by_check(await run._write_paths())[EMS_CHECK]
    assert row.verdict == CONFIRMED
    assert writes == [2, 0, 3, 0, 4, 0]
    assert house.holding[EMS] == 0


async def test_an_ems_option_refused_is_named(house: MockModbusUnit) -> None:
    _refuse(house, EMS, when=lambda word: word == 4)
    run = await _run(house)
    row = _by_check(await run._write_paths())[EMS_CHECK]
    assert row.verdict == REFUSED
    assert run.conditions["ems_mode_options"]["4"].startswith(REFUSED)
    assert house.holding[EMS] == 0


# -- what a run does not do --------------------------------------------------------


async def test_a_dry_run_and_a_simulated_run_write_nothing_here(
    house: MockModbusUnit,
) -> None:
    for options in ({"dry_run": True}, {"simulated": True}):
        writes: list[int] = []
        house.on_write(lambda event, sink=writes: sink.append(event.address))
        run = await _run(house, **options)
        assert await run._write_paths() == []
        assert writes == []


async def test_an_established_check_is_left_out(house: MockModbusUnit) -> None:
    run = await _run(house, skip=frozenset({EMS_CHECK}))
    assert EMS_CHECK not in _by_check(await run._write_paths())


async def test_the_whole_run_restores_every_word(house: MockModbusUnit) -> None:
    before = dict(house.holding)
    inverter = SungrowInverter(house)
    await inverter.async_update()
    run = CapabilityTest(
        inverter,
        options=Options(allow_dark=True, charge_window=True, discharge_window=True),
        clock=FakeClock(),
    )
    outcome = await run.async_run()
    assert outcome.restores
    assert all(row.restored for row in outcome.restores)
    for address in (BACKUP, LOAD_ENABLE, LOAD_MODE, EMS, WEEKEND_ENABLE, MAX_SOC):
        assert house.holding[address] == before[address], address
