"""The forced-charging schedule, registers 33208-33219 in V1.1.16 (#785).

An enable flag, weekdays or every day, and two windows of a start and an end
time with a target state of charge each. Each time is two registers, an hour
and a minute, shown as one `time` entity, so the test that matters most is
that setting one writes both and nothing else.
"""

from __future__ import annotations

from datetime import time
from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_CONTROL_TEST_EXPORT,
    CONF_CONTROL_TEST_PV_CUT,
    CONF_CONTROL_TEST_RESTART,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.inverter.capabilities import ABSENT_IN, Capability, Family

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses, one below the registers: 33208 is at 33207.
ENABLE = 33207
DAYS = 33208
START_1_HOUR, START_1_MINUTE, END_1_HOUR, END_1_MINUTE, TARGET_1 = range(33209, 33214)
START_2_HOUR = 33214

#: Off, every day, one window 02:00-05:00 to 80 %, the second unused.
SCHEDULE: dict[int, int] = {
    ENABLE: 0x55,
    DAYS: 1,
    START_1_HOUR: 2,
    START_1_MINUTE: 0,
    END_1_HOUR: 5,
    END_1_MINUTE: 0,
    TARGET_1: 80,
    **dict.fromkeys(range(33214, 33219), 0),
}


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    options: dict[str, Any] = {
        CONF_CONTROL_TEST_RESTART: False,
        CONF_CONTROL_TEST_EXPORT: False,
        CONF_CONTROL_TEST_PV_CUT: False,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity(hass: HomeAssistant, domain: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}")


async def test_the_schedule_reads_as_times_a_switch_a_select_and_targets(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding.update(SCHEDULE)
    await _setup(hass, sungrow_unit)

    switch = _entity(hass, "switch", "forced_charging_schedule")
    assert switch is not None
    assert hass.states.get(switch).state == "off"
    days = _entity(hass, "select", "forced_charging_days")
    assert days is not None
    assert hass.states.get(days).state == "every_day"
    start = _entity(hass, "time", "forced_charging_start_1")
    end = _entity(hass, "time", "forced_charging_end_1")
    assert start is not None and end is not None
    assert hass.states.get(start).state == "02:00:00"
    assert hass.states.get(end).state == "05:00:00"
    target = _entity(hass, "number", "forced_charging_target_soc_1")
    assert target is not None
    assert float(hass.states.get(target).state) == 80


async def test_setting_a_time_writes_its_hour_and_its_minute(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding.update(SCHEDULE)
    await _setup(hass, sungrow_unit)
    start = _entity(hass, "time", "forced_charging_start_1")
    assert start is not None

    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": start, "time": time(23, 45)},
        blocking=True,
    )

    assert sungrow_unit.holding[START_1_HOUR] == 23
    assert sungrow_unit.holding[START_1_MINUTE] == 45
    # The window's other end, and the other window, are untouched.
    assert sungrow_unit.holding[END_1_HOUR] == 5
    assert sungrow_unit.holding[START_2_HOUR] == 0
    assert hass.states.get(start).state == "23:45:00"


async def test_turning_the_schedule_on_writes_the_enable_code(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding.update(SCHEDULE)
    await _setup(hass, sungrow_unit)
    switch = _entity(hass, "switch", "forced_charging_schedule")
    assert switch is not None

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch}, blocking=True
    )

    assert sungrow_unit.holding[ENABLE] == 0xAA


async def test_an_hour_that_is_not_one_is_not_shown_as_a_time(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The specification gives 0-23; anything else is unknown, not a guess."""
    sungrow_unit.holding.update({**SCHEDULE, END_1_HOUR: 24})
    await _setup(hass, sungrow_unit)
    end = _entity(hass, "time", "forced_charging_end_1")
    assert end is not None
    assert hass.states.get(end).state == "unknown"


async def test_an_inverter_without_it_gets_none_of_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Unseeded, the enable reads 0, which no Sungrow mode register holds."""
    await _setup(hass, sungrow_unit)

    assert _entity(hass, "switch", "forced_charging_schedule") is None
    assert _entity(hass, "time", "forced_charging_start_1") is None
    assert _entity(hass, "number", "forced_charging_target_soc_1") is None


def test_the_specifications_exclusions_are_recorded() -> None:
    """V1.1.16: "MG5-12RL and SH3-10RL are not supported. SH50~125CX are not"."""
    assert ABSENT_IN[Capability.FORCED_CHARGING] == {Family.MG, Family.RL, Family.CX}
