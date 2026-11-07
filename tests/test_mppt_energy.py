"""Energy per MPP tracker: voltage times current, integrated over the polls.

No register counts it, so the arithmetic is `sungrow_modbus.energy_integral`
and the entity keeps its total across a restart. The library half takes the
clock as an argument; the entity half is driven by patching the event loop's
clock around each poll.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.energy_integral import EnergyIntegral

from .conftest import SERIAL

#: Far enough past the real clock that every patched poll comes after it.
_START = 10_000_000.0

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses of MPPT1's voltage and current (registers 5011, 5012).
MPPT1_VOLTAGE = 5010
MPPT1_CURRENT = 5011


# -- the arithmetic ---------------------------------------------------------


def test_a_steady_kilowatt_for_an_hour_is_one_kilowatt_hour() -> None:
    integral = EnergyIntegral(max_gap=60)
    for second in range(0, 3601, 10):
        integral.update(second, 1000.0)
    assert integral.total_kwh == pytest.approx(1.0)


def test_a_ramp_is_integrated_as_trapezoids() -> None:
    integral = EnergyIntegral(max_gap=60)
    integral.update(0, 0.0)
    integral.update(36, 2000.0)
    # 1000 W on average for 36 s.
    assert integral.total_kwh == pytest.approx(0.01)


def test_nothing_is_added_across_a_gap() -> None:
    integral = EnergyIntegral(max_gap=60)
    integral.update(0, 1000.0)
    integral.update(3600, 1000.0)
    assert integral.total_kwh == 0.0
    integral.update(3636, 1000.0)
    assert integral.total_kwh == pytest.approx(0.01)


def test_a_missing_reading_ends_the_run() -> None:
    integral = EnergyIntegral(max_gap=600)
    integral.update(0, 1000.0)
    integral.update(10, None)
    integral.update(20, 1000.0)
    assert integral.total_kwh == 0.0


def test_the_total_never_falls() -> None:
    integral = EnergyIntegral(5.0, max_gap=60)
    integral.update(0, -50.0)
    integral.update(10, -50.0)
    assert integral.total_kwh == 5.0


def test_the_same_moment_twice_adds_nothing() -> None:
    integral = EnergyIntegral(max_gap=60)
    integral.update(0, 1000.0)
    integral.update(0, 3000.0)
    integral.update(36, 3000.0)
    assert integral.total_kwh == pytest.approx(0.03)


def test_the_count_starts_from_a_restored_total() -> None:
    integral = EnergyIntegral(12.5, max_gap=60)
    integral.update(0, 1000.0)
    integral.update(36, 1000.0)
    assert integral.total_kwh == pytest.approx(12.51)


# -- the entity -------------------------------------------------------------


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _poll_at(hass: HomeAssistant, entry: MockConfigEntry, now: float) -> None:
    """Poll the trackers' tier `now` seconds after the real clock's reading.

    Offset rather than absolute: the entity took its first sample on the real
    clock when it was added, and a clock running backwards adds nothing.
    """
    coordinator: Any = entry.runtime_data.coordinator_for("fast_input")
    with patch.object(hass.loop, "time", return_value=_START + now):
        await coordinator.async_refresh()
        await hass.async_block_till_done()


def _energy_id(hass: HomeAssistant, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_{key}")


async def test_each_tracker_the_inverter_has_gets_an_energy_sensor(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)

    assert _energy_id(hass, "mppt1_energy") is not None
    assert _energy_id(hass, "mppt2_energy") is not None
    # The double answers 0xFFFF for both, as a two-tracker SH10RT does.
    assert _energy_id(hass, "mppt3_energy") is None
    assert _energy_id(hass, "mppt4_energy") is None


async def test_the_sensor_integrates_voltage_times_current(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[MPPT1_VOLTAGE] = 4000  # 400.0 V
    sungrow_unit.input[MPPT1_CURRENT] = 50  # 5.0 A: 2000 W
    entry = await _setup(hass, sungrow_unit)
    entity_id = _energy_id(hass, "mppt1_energy")
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["device_class"] == "energy"

    await _poll_at(hass, entry, 1000.0)
    await _poll_at(hass, entry, 1018.0)
    # 2000 W for 18 s.
    assert float(hass.states.get(entity_id).state) == pytest.approx(0.01)


async def test_the_total_survives_a_reload(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[MPPT1_VOLTAGE] = 4000
    sungrow_unit.input[MPPT1_CURRENT] = 50
    entry = await _setup(hass, sungrow_unit)
    entity_id = _energy_id(hass, "mppt1_energy")
    assert entity_id is not None
    await _poll_at(hass, entry, 1000.0)
    await _poll_at(hass, entry, 1036.0)
    assert float(hass.states.get(entity_id).state) == pytest.approx(0.02)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert float(hass.states.get(entity_id).state) == pytest.approx(0.02)
    await _poll_at(hass, entry, 5000.0)
    await _poll_at(hass, entry, 5018.0)
    assert float(hass.states.get(entity_id).state) == pytest.approx(0.03)
