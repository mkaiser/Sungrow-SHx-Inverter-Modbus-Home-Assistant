"""When a day's balance began again, and what statistics make of it."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)
from pytest_homeassistant.components.recorder.common import (
    async_recorder_block_till_done,
    async_wait_recording_done,
    do_adhoc_statistics,
    get_start_time,
    statistics_during_period,
)
from pytest_homeassistant.typing import RecorderInstanceContextManager

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from sungrow_modbus.hybrid_inverter.daily_cycle import HOLD, DailyCycle

from .conftest import SERIAL

_START = 10_000_000.0
#: Protocol addresses of the five counters, in `depends_on`'s order, in 0.1 kWh.
COUNTERS = (13001, 13044, 13035, 13039, 13025)
FIELDS = (
    "daily_pv_generation",
    "daily_exported_energy",
    "daily_imported_energy",
    "daily_battery_charge",
    "daily_battery_discharge",
)
EVENING = (300, 50, 60, 100, 80)  # 30 - 5 + 6 - 10 + 8 = 29.0 kWh
MORNING = (0, 0, 2, 0, 3)  # 0.5 kWh


# -- the arithmetic ---------------------------------------------------------


def test_the_counters_fall_together() -> None:
    cycle = DailyCycle()
    assert not cycle.update(0, (30, 5, 6))
    assert not cycle.update(10, (30.1, 5, 6))
    assert cycle.update(20, (0, 0, 0.1))
    assert not cycle.holding
    assert not cycle.update(30, (0, 0, 0.2))


def test_staggered_counters_are_one_reset() -> None:
    cycle = DailyCycle((30, 5, 6))
    cycle.update(0, (30, 5, 6))
    assert not cycle.update(10, (0, 5, 6))
    assert cycle.holding
    assert cycle.counters == (30, 5, 6)
    assert cycle.update(20, (0, 0, 0.1))
    assert not cycle.holding


def test_a_counter_that_never_falls_is_waited_for_so_long() -> None:
    cycle = DailyCycle()
    cycle.update(0, (30, 5))
    now = 10.0
    while now < 10 + HOLD:
        assert not cycle.update(now, (0, 5))
        now += 10
    assert cycle.update(now, (0, 5))


def test_a_misread_is_no_reset() -> None:
    cycle = DailyCycle()
    cycle.update(0, (30, 5))
    assert not cycle.update(10, (0, 5))
    assert not cycle.update(20, (30, 5))
    assert not cycle.holding


def test_a_small_counter_is_not_waited_for() -> None:
    cycle = DailyCycle()
    cycle.update(0, (30, 0.1))
    assert cycle.update(10, (0, 0.1))


def test_a_fall_after_a_gap_is_a_reset_at_once() -> None:
    cycle = DailyCycle()
    cycle.update(0, (30, 5))
    assert cycle.update(HOLD + 1, (12, 9))


def test_a_restored_cycle_sees_the_reset_it_missed() -> None:
    assert DailyCycle((30, 5)).update(0, (12, 9))
    assert not DailyCycle((30, 5)).update(0, (31, 5))


# -- the entities -----------------------------------------------------------


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


def _count(unit: MockModbusUnit, values: tuple[int, ...]) -> None:
    unit.input.update(zip(COUNTERS, values, strict=True))


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _poll_at(hass: HomeAssistant, entry: MockConfigEntry, now: float) -> None:
    with patch.object(hass.loop, "time", return_value=_START + now):
        runtime_data = entry.runtime_data
        for component in {runtime_data.component_of(field) for field in FIELDS}:
            coordinator: Any = runtime_data.coordinator_for(component)
            await coordinator.async_refresh()
        await hass.async_block_till_done()


def _state(hass: HomeAssistant, key: str = "daily_consumed_energy") -> State:
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_{key}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_both_begin_again_with_the_counters(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    _count(sungrow_unit, EVENING)
    entry = await _setup(hass, sungrow_unit)
    await _poll_at(hass, entry, 0)
    assert float(_state(hass).state) == pytest.approx(29.0)
    assert _state(hass).attributes.get("last_reset") is None
    assert _state(hass).attributes["state_class"] == "total"

    _count(sungrow_unit, MORNING)
    await _poll_at(hass, entry, 10)
    for key in ("daily_consumed_energy", "daily_consumed_energy_filtered"):
        state = _state(hass, key)
        assert float(state.state) == pytest.approx(0.5)
        assert state.attributes["last_reset"] is not None
    assert _state(hass, "total_consumed_energy").attributes.get("last_reset") is None


async def test_the_old_day_is_held_until_all_have_fallen(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    _count(sungrow_unit, EVENING)
    entry = await _setup(hass, sungrow_unit)
    await _poll_at(hass, entry, 0)

    _count(sungrow_unit, (0, *EVENING[1:]))
    await _poll_at(hass, entry, 10)
    assert float(_state(hass).state) == pytest.approx(29.0)
    assert _state(hass).attributes.get("last_reset") is None

    _count(sungrow_unit, MORNING)
    await _poll_at(hass, entry, 20)
    assert float(_state(hass).state) == pytest.approx(0.5)
    assert _state(hass).attributes["last_reset"] is not None


@pytest.mark.parametrize(
    ("values", "kept"), [(MORNING, False), ((301, 50, 60, 100, 80), True)]
)
async def test_a_restart_keeps_the_reset_and_sees_one_it_missed(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    values: tuple[int, ...],
    kept: bool,
) -> None:
    before = "2026-11-23T23:04:00+00:00"
    registry = er.async_get(hass)
    entity_id = registry.async_get_or_create(
        "sensor", DOMAIN, f"{SERIAL}_daily_consumed_energy"
    ).entity_id
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(entity_id, "29.0"),
                {"last_reset": before, "counters": [one / 10 for one in EVENING]},
            )
        ],
    )
    _count(sungrow_unit, values)
    await _setup(hass, sungrow_unit)
    last_reset = _state(hass).attributes["last_reset"]
    assert (last_reset == before) is kept


async def test_statistics_book_the_day_and_not_its_negative(
    recorder_mock: Recorder,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    sungrow_unit: MockModbusUnit,
) -> None:
    """The first reset after an update: nothing doubled, nothing subtracted."""
    await async_setup_component(hass, "sensor", {})
    await async_recorder_block_till_done(hass)
    start: datetime = get_start_time(dt_util.utcnow())
    freezer.move_to(start)
    _count(sungrow_unit, EVENING)
    entry = await _setup(hass, sungrow_unit)
    for minute, values in enumerate(
        (EVENING, (300, 50, 70, 100, 80), MORNING, (0, 0, 2, 0, 8)), start=1
    ):
        freezer.move_to(start + timedelta(minutes=minute))
        _count(sungrow_unit, values)
        await _poll_at(hass, entry, minute * 60)
    await async_wait_recording_done(hass)
    entity_id = _state(hass).entity_id
    with freeze_time(start + timedelta(minutes=5)):
        do_adhoc_statistics(hass, start=start)
        await async_wait_recording_done(hass)
    rows = statistics_during_period(hass, start, period="5minute")[entity_id]
    # 29.0 to 30.0 in the old day, then 0 to 1.0 in the new one.
    assert rows[-1]["sum"] == pytest.approx(2.0)
