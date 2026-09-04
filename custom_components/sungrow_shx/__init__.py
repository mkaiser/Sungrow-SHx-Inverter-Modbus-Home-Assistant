"""The Sungrow SHx Inverter integration.

Built on the modernized Home Assistant Modbus architecture: this integration
collects its own connection details in its config flow and asks the modbus
integration for a unit, so several integrations pointed at the same inverter
share one serialized connection instead of competing for its few sessions.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from modbus_connection import ModbusError, ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from sungrow_shx_modbus import SungrowInverter

from .const import CONF_UNIT_ID, READINGS_SCAN_INTERVAL
from .coordinator import (
    SungrowConfigEntry,
    SungrowDataUpdateCoordinator,
    SungrowRuntimeData,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up a Sungrow SHx inverter from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    inverter = SungrowInverter(unit)

    # Identity is read once and never polled: it cannot change while the
    # entry is loaded, and entities need the serial number to exist first.
    try:
        await inverter.async_update_identity()
    except ModbusError as err:
        raise ConfigEntryNotReady(
            f"Could not read the identity of {entry.title}: {err}"
        ) from err

    readings = SungrowDataUpdateCoordinator(
        hass,
        entry,
        inverter,
        inverter.async_update_readings,
        timedelta(seconds=READINGS_SCAN_INTERVAL),
    )
    await readings.async_config_entry_first_refresh()

    entry.runtime_data = SungrowRuntimeData(readings)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Unload a config entry.

    The shared connection closes itself once the last entry holding a unit on
    it unloads, so there is nothing to tear down here.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
