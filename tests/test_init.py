"""Test that the integration sets up under Home Assistant."""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_shx.const import CONF_UNIT_ID, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    """Set up a config entry backed by the mock unit."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_shx.async_get_unit",
        return_value=unit,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_entry_loads(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> None:
    """The entry reaches LOADED and registers the inverter as a device."""
    entry = await _setup(hass, sungrow_unit)

    assert entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Sungrow"
    assert device.model == "SH10RT"
    assert device.serial_number == SERIAL


async def test_total_dc_power_sensor(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The one milestone sensor exists and carries the decoded value."""
    await _setup(hass, sungrow_unit)

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_total_dc_power"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "7000"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"


async def test_entry_unloads(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> None:
    """Unloading tears the entry down cleanly."""
    entry = await _setup(hass, sungrow_unit)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
