"""Test that the integration sets up under Home Assistant."""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
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
        "custom_components.sungrow_modbus.async_get_unit",
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


async def test_a_dropped_connection_names_its_usual_cause(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The message has to point somewhere useful.

    A Sungrow accepts very few Modbus sessions at once, so a dropped
    connection is nearly always a second client rather than a network fault.
    The bare library message -- "Connection lost before response was
    received" -- sends people to look at their cabling, which is what happened
    to the maintainer against his own inverter: the reads were fine, another
    client had the slots.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
        ),
        patch.object(
            type(sungrow_unit),
            "read_input_registers",
            side_effect=ModbusConnectionError("Connection lost"),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert "accepts very few Modbus connections" in str(entry.reason)
