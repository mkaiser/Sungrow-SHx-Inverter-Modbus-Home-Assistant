"""The Sungrow Modbus integration.

Built on the modernized Home Assistant Modbus architecture: this integration
collects its own connection details in its config flow and asks the modbus
integration for a unit, so several integrations pointed at the same inverter
share one serialized connection instead of competing for its few sessions.
"""

from __future__ import annotations

from datetime import timedelta
from functools import partial
import logging

from modbus_connection import ModbusConnectionError, ModbusError, ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from sungrow_modbus import TIERS, SungrowInverter

from .const import CONF_ENTITY_IDS, CONF_UNIT_ID, ENTITY_IDS_MIGRATE
from .coordinator import (
    SungrowConfigEntry,
    SungrowDataUpdateCoordinator,
    SungrowRuntimeData,
)
from .migration import async_claim_legacy_ids

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


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
    except ModbusConnectionError as err:
        raise ConfigEntryNotReady(
            f"Could not reach {entry.title}: {err}. A Sungrow inverter accepts "
            "very few Modbus connections at once, so check whether something "
            "else is polling it -- the modbus_sungrow.yaml package, another "
            "Home Assistant, or another tool."
        ) from err
    except ModbusError as err:
        raise ConfigEntryNotReady(
            f"Could not read the identity of {entry.title}: {err}"
        ) from err

    # One coordinator per poll interval, mirroring the tiers the YAML package
    # used, so users see the same freshness they are used to.
    coordinators: dict[str, SungrowDataUpdateCoordinator] = {}
    for interval, components in TIERS.items():
        coordinator = SungrowDataUpdateCoordinator(
            hass,
            entry,
            inverter,
            partial(inverter.async_update_tier, interval),
            timedelta(seconds=interval),
        )
        await coordinator.async_config_entry_first_refresh()
        for component in components:
            coordinators[component] = coordinator

    # Probed after the first poll, not before: every optional block looks
    # absent until something has actually been read.
    capabilities = inverter.capabilities()
    _LOGGER.debug(
        "%s reports capabilities: %s",
        entry.title,
        ", ".join(sorted(c.value for c in capabilities)) or "none",
    )
    entry.runtime_data = SungrowRuntimeData(coordinators, capabilities)

    # Before the platforms, not after: an entity registered on the YAML
    # package's id continues its history, whereas renaming into that id
    # afterwards is refused outright. The user chose this at setup.
    if entry.data.get(CONF_ENTITY_IDS) == ENTITY_IDS_MIGRATE:
        serial = inverter.serial_number
        assert serial is not None
        claimed = async_claim_legacy_ids(hass, entry, serial, capabilities)
        _LOGGER.info(
            "%s took over %d entity ids from the YAML package",
            entry.title,
            len(claimed),
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Unload a config entry.

    The shared connection closes itself once the last entry holding a unit on
    it unloads, so there is nothing to tear down here.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
