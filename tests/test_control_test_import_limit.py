"""The control test's import limit check: register 32998 under a forced charge.

The mock house here obeys a cap the way the maintainer's SH10RT did on
2026-11-07 (P020): under a forced charge it cuts the charge until grid import
sits at the cap, and never touches the load. What is tested is the procedure:
when it runs, how it sizes the cap, how it judges it, which words it probes,
and that the restore puts every word back.
"""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusConnectionError, ServerDeviceFailureError
from modbus_connection.mock import MockModbusUnit

from sungrow_modbus import SungrowInverter
from sungrow_modbus.control_test import CONFIRMED, NO_EFFECT, ControlTest, Options
from sungrow_modbus.control_test.procedure import IMPORT_LIMIT

#: Protocol addresses, one below the registers.
BATTERY_POWER = 5213  # input 5214-5215, int32 low word first
SOC = 13022  # input 13023, 0.1 %
EXPORT = 13009  # input 13010-13011, int32 low word first, positive exporting
EMS_MODE = 13049  # holding 13050
FORCED_CMD = 13050  # holding 13051
FORCED_W = 13051  # holding 13052
LIMIT = 32997  # holding 32998, 0.01 kW

LOAD_W = 600
SNAPSHOT_WORD = 2000


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


def _int32(unit: MockModbusUnit, address: int, value: int) -> None:
    word = value & 0xFFFFFFFF
    unit.input[address] = word & 0xFFFF
    unit.input[address + 1] = word >> 16


def _house(unit: MockModbusUnit, *, pv: int = 0, obeys: bool = True) -> MockModbusUnit:
    """Make the unit a house at night (or with `pv`) that obeys 32998 or not.

    Out of range words are refused with 0x04, as the SH10RS and the SH10RT
    refused 0 and 5001.
    """
    unit.input[SOC] = 500
    # The limits the inverter states about itself, so the forced charge power
    # resolves: BDC rated power 5 kW, 100 W per count.
    unit.input[5621] = 0
    unit.input[5622] = 1000
    unit.input[5627] = 50
    unit.holding.update(
        {EMS_MODE: 0, FORCED_CMD: 0xCC, FORCED_W: 0, LIMIT: SNAPSHOT_WORD}
    )
    plain = unit.write_register

    def settle() -> None:
        forced = unit.holding[EMS_MODE] == 2 and unit.holding[FORCED_CMD] == 0xAA
        charge = unit.holding[FORCED_W] if forced else max(0, pv - LOAD_W)
        need = LOAD_W - pv
        if obeys:
            cap = unit.holding[LIMIT] * 10
            charge = min(charge, max(0, cap - need))
        _int32(unit, BATTERY_POWER, -charge)
        _int32(unit, EXPORT, -(need + charge))

    async def write_register(address: int, value: int) -> None:
        if address == LIMIT and not 1 <= value <= 5000:
            raise ServerDeviceFailureError
        await plain(address, value)
        settle()

    unit.write_register = write_register  # type: ignore[method-assign]
    settle()
    return unit


async def _run(unit: MockModbusUnit, **options: Any) -> ControlTest:
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = ControlTest(inverter, options=Options(**options), clock=FakeClock())
    run._plan_budget()
    await run._preflight()
    return run


def _limit_writes(unit: MockModbusUnit) -> list[int]:
    words: list[int] = []
    unit.on_write(
        lambda event: words.extend(event.values) if event.address == LIMIT else None
    )
    return words


async def test_without_leave_the_limit_is_neither_read_nor_written(
    sungrow_unit: MockModbusUnit,
) -> None:
    house = _house(sungrow_unit)
    words = _limit_writes(house)
    run = await _run(house)

    assert IMPORT_LIMIT.field not in run.snapshot.raw
    assert await run._import_limit_effect() == []
    assert words == []


async def test_a_cap_under_a_forced_charge_is_met_and_everything_goes_back(
    sungrow_unit: MockModbusUnit,
) -> None:
    house = _house(sungrow_unit)
    words = _limit_writes(house)
    run = await _run(house, import_limit=True)
    assert run.snapshot.raw[IMPORT_LIMIT.field] == SNAPSHOT_WORD

    [result] = await run._import_limit_effect()
    restored = await run.async_restore()

    # 600 W of load and the 1250 W charge: 1850 W of import, the cap halfway
    # down to the load's 600 W.
    assert run.conditions["import_limit_sizing_w"] == 1850
    assert result.commanded == 1220
    assert result.verdict == CONFIRMED
    assert words[0] == 122
    assert run.conditions["import_limit_words"]["5000"] == "taken"
    for word in ("0", "5001"):
        answer = run.conditions["import_limit_words"][word]
        assert answer.startswith("refused: ServerDeviceFailureError")
    assert all(row.restored for row in restored)
    assert house.holding[LIMIT] == SNAPSHOT_WORD
    assert (house.holding[EMS_MODE], house.holding[FORCED_CMD]) == (0, 0xCC)


async def test_a_device_that_ignores_the_cap_is_no_effect_and_still_put_back(
    sungrow_unit: MockModbusUnit,
) -> None:
    """As one SH10RT-V112 was reported to in discussion #546."""
    house = _house(sungrow_unit, obeys=False)
    run = await _run(house, import_limit=True)

    [result] = await run._import_limit_effect()
    await run.async_restore()

    assert result.verdict == NO_EFFECT
    assert house.holding[LIMIT] == SNAPSHOT_WORD


async def test_pv_covering_the_charge_leaves_the_limit_unwritten(
    sungrow_unit: MockModbusUnit,
) -> None:
    house = _house(sungrow_unit, pv=1500)
    words = _limit_writes(house)
    run = await _run(house, import_limit=True)

    assert await run._import_limit_effect() == []
    await run.async_restore()

    assert words == []
    assert any("PV was covering it" in note for note in run.unestablished)
    assert (house.holding[EMS_MODE], house.holding[FORCED_CMD]) == (0, 0xCC)


async def test_a_lost_link_on_a_probe_word_is_not_a_refusal(
    sungrow_unit: MockModbusUnit,
) -> None:
    house = _house(sungrow_unit)
    run = await _run(house, import_limit=True)
    obeying = house.write_register

    async def drop_5001(address: int, value: int) -> None:
        if address == LIMIT and value == 5001:
            raise ModbusConnectionError("connection lost")
        await obeying(address, value)

    house.write_register = drop_5001  # type: ignore[method-assign]

    await run._import_limit_effect()

    assert run.conditions["import_limit_words"]["5001"].startswith(
        "not answered: ModbusConnectionError"
    )
    assert house.holding[LIMIT] == SNAPSHOT_WORD


async def test_a_value_written_to_the_raw_register_goes_through_its_scale(
    sungrow_unit: MockModbusUnit,
) -> None:
    """The restore's fallback writes the snapshot's value: 20.00 kW is 2000."""
    house = _house(sungrow_unit)
    run = await _run(house, import_limit=True)
    house.holding[LIMIT] = 7

    assert await run._write(IMPORT_LIMIT, 20.0) is None
    assert house.holding[LIMIT] == SNAPSHOT_WORD


async def test_a_zero_from_a_dongle_is_not_a_limit(
    sungrow_unit: MockModbusUnit,
) -> None:
    house = _house(sungrow_unit)
    house.holding[LIMIT] = 0
    words = _limit_writes(house)
    run = await _run(house, import_limit=True)

    assert await run._import_limit_effect() == []
    assert words == []
