"""The forced startup check: register 13017, only from low-SoC standby.

The mock unit stores words and has no behaviour, so the inverter's answer to
0xAA and 0x55 -- waking and going back to standby, as watched at bar12 on
P023 -- is modelled here by the running-state read, from the word 13017 holds.
"""

from __future__ import annotations

from typing import Any

from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter
from sungrow_modbus.addresses import field_address
from sungrow_modbus.capability_test import CapabilityTest, Options
from sungrow_modbus.capability_test.procedure import (
    CONFIRMED,
    FORCED_STARTUP,
    FORCED_STARTUP_OFF,
    FORCED_STARTUP_ON,
    NO_EFFECT,
)

from .test_capability_test import FakeClock

STANDBY = 0x0008
RUNNING = 0x0040
STARTING = 0x0020


def _set(unit: MockModbusUnit, field: str, *words: int) -> None:
    where = field_address(field)
    table = unit.holding if where.space == "holding" else unit.input
    for offset, word in enumerate(words):
        table[where.address + offset] = word


@pytest.fixture
def asleep(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an inverter in low-SoC standby at night, battery at its 7 % minimum."""
    _set(sungrow_unit, "running_state_raw", STANDBY)
    _set(sungrow_unit, "battery_min_soc", 70)
    _set(sungrow_unit, "battery_level", 70)
    _set(sungrow_unit, "total_dc_power", 0, 0)
    _set(sungrow_unit, FORCED_STARTUP.field, 0)
    return sungrow_unit


async def _run(unit: MockModbusUnit, *, wakes: bool = True) -> tuple[Any, Any]:
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = CapabilityTest(
        inverter, options=Options(forced_startup=True), clock=FakeClock()
    )
    address = field_address(FORCED_STARTUP.field).address
    polls = {"awake": 0}

    async def running_word() -> int:
        if wakes and unit.holding.get(address) == FORCED_STARTUP_ON:
            polls["awake"] += 1
            return STARTING if polls["awake"] < 3 else RUNNING
        polls["awake"] = 0
        return STANDBY

    run._running_word = running_word  # type: ignore[method-assign]
    return run, await run.async_run()


async def test_a_sleeping_inverter_wakes_sleeps_again_and_is_put_back(
    asleep: MockModbusUnit,
) -> None:
    run, outcome = await _run(asleep)

    (effect,) = outcome.effects
    assert effect.check == "forced startup under low SoC"
    assert effect.verdict == CONFIRMED
    assert "running after" in str(effect.detail)
    assert "back in standby" in str(effect.detail)
    assert effect.before == STANDBY
    assert effect.during == RUNNING
    assert outcome.probes == ()
    assert outcome.restart is None
    (restored,) = outcome.restores
    assert restored.restored
    # The factory 0 is refused by the register, so its equivalent goes back.
    address = field_address(FORCED_STARTUP.field).address
    assert asleep.holding[address] == FORCED_STARTUP_OFF
    assert "0x0000" in str(restored.detail)
    assert outcome.code == 0, run.conditions


async def test_a_word_the_register_takes_is_put_back_as_found(
    asleep: MockModbusUnit,
) -> None:
    _set(asleep, FORCED_STARTUP.field, FORCED_STARTUP_OFF)
    _run_result = await _run(asleep)
    (restored,) = _run_result[1].restores
    assert restored.restored
    assert "refused by the register" not in str(restored.detail)


async def test_an_inverter_that_never_wakes_is_reported_as_no_effect(
    asleep: MockModbusUnit,
) -> None:
    _run_unused, outcome = await _run(asleep, wakes=False)

    (effect,) = outcome.effects
    assert effect.verdict == NO_EFFECT
    address = field_address(FORCED_STARTUP.field).address
    assert asleep.holding[address] == FORCED_STARTUP_OFF


@pytest.mark.parametrize(
    ("field", "words", "said"),
    [
        ("running_state_raw", (RUNNING,), "rather than standby"),
        ("battery_level", (500,), "above its"),
        ("total_dc_power", (3000, 0), "W of PV"),
    ],
)
async def test_anything_but_low_soc_standby_is_refused_before_a_write(
    asleep: MockModbusUnit, field: str, words: tuple[int, ...], said: str
) -> None:
    _set(asleep, field, *words)
    before = dict(asleep.holding)

    run, outcome = await _run(asleep)

    assert outcome.code == 2
    assert said in run.conditions["refused"]
    assert outcome.effects == ()
    assert asleep.holding == before
