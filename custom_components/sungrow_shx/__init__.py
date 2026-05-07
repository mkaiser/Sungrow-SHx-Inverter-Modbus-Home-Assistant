"""The Sungrow SHx Inverter integration."""

from __future__ import annotations

import logging
from typing import Any, Final

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BATTERY_MAX_POWER,
    CONF_HOST,
    CONF_PORT,
    CONF_SBR_SLAVE,
    CONF_SLAVE,
    CONF_WAIT_MS,
    DEFAULT_BATTERY_MAX_POWER,
    DEFAULT_PORT,
    DEFAULT_SBR_SLAVE,
    DEFAULT_SLAVE,
    DEFAULT_WAIT_MS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SungrowModbusCoordinator
from .modbus_client import SungrowModbusClient, SungrowModbusError
from .repairs import async_check_legacy_yaml

_LOGGER: Final = logging.getLogger(__name__)

type SungrowRuntimeData = SungrowModbusCoordinator
type SungrowConfigEntry = ConfigEntry[SungrowRuntimeData]


# ---------------------------------------------------------------------------
# YAML import schema (migration helper).
#
# The historical integration was delivered as a *YAML package* wired into the
# built-in ``modbus:`` platform — so there is no legacy ``sungrow_shx:`` top
# level key to import from. This block exists purely so power users who want
# a scripted, reproducible migration path can temporarily add:
#
#     sungrow_shx:
#       - host: 192.168.1.10
#         port: 502
#         slave: 1
#         sbr_slave: 200
#
# and on the next restart the integration will create a proper config entry
# and surface a "imported_from_yaml" repair telling them to remove the block.
# Extras are allowed so users migrating from partial hand-written snippets
# aren't punished for passing extra keys.
# ---------------------------------------------------------------------------
_IMPORT_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SLAVE, default=DEFAULT_SLAVE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Optional(CONF_SBR_SLAVE, default=DEFAULT_SBR_SLAVE): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=247)
        ),
        vol.Optional(
            CONF_BATTERY_MAX_POWER, default=DEFAULT_BATTERY_MAX_POWER
        ): vol.All(vol.Coerce(int), vol.Range(min=0, max=50000)),
        vol.Optional(CONF_WAIT_MS, default=DEFAULT_WAIT_MS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=1000)
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.All(cv.ensure_list, [_IMPORT_ITEM_SCHEMA]),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Sungrow SHx integration from YAML (legacy import).

    No-op when the ``sungrow_shx:`` YAML block is absent. When present,
    each entry is handed to the config-flow import step so a real
    ConfigEntry is created. The import step will then raise a repairs
    issue instructing the user to delete the YAML block.
    """
    imports: list[dict[str, Any]] | None = config.get(DOMAIN)
    if not imports:
        return True

    _LOGGER.info(
        "Triggering YAML import for %d sungrow_shx entry(ies)", len(imports)
    )
    for item in imports:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=dict(item),
            )
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up Sungrow SHx from a config entry."""
    _LOGGER.debug("Setting up Sungrow SHx entry %s", entry.entry_id)

    merged = {**entry.data, **entry.options}
    host = merged[CONF_HOST]
    port = merged.get(CONF_PORT, DEFAULT_PORT)
    slave = merged.get(CONF_SLAVE, DEFAULT_SLAVE)
    wait_ms = merged.get(CONF_WAIT_MS, DEFAULT_WAIT_MS)

    client = SungrowModbusClient(host=host, port=port, slave=slave, wait_ms=wait_ms)
    try:
        await client.connect()
    except SungrowModbusError as err:
        raise ConfigEntryNotReady(f"Cannot connect to Sungrow inverter: {err}") from err

    coordinator = SungrowModbusCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.close()
        raise

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Detect a still-loaded legacy YAML package and raise a repairs issue.
    # Runs after the coordinator is ready so HA's main setup has had a
    # chance to register any `modbus:` hubs referenced by the old package.
    await async_check_legacy_yaml(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Unload a Sungrow SHx config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SungrowModbusCoordinator | None = entry.runtime_data
        if coordinator is not None:
            await coordinator.client.close()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Reload a Sungrow SHx config entry (e.g. after options change)."""
    await hass.config_entries.async_reload(entry.entry_id)
