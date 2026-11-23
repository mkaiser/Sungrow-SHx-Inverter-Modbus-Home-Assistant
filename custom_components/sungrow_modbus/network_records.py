"""The diagnosis's `network_names` section, read through Home Assistant.

The same section the terminal diagnosis writes
(`sungrow_modbus.network_names.network_section`), with one difference: the
mDNS browse goes through Home Assistant's **shared** zeroconf instance, never
sockets of its own, so it costs nothing Home Assistant is not already doing
and the records it has cached answer at once.
"""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any

from homeassistant.components import zeroconf as ha_zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from sungrow_modbus import network_names
from sungrow_modbus.discovery import async_hostname
from sungrow_modbus.network_names import async_mac_prefix, on_device_segment

_LOGGER = logging.getLogger(__name__)

#: Shorter than the terminal's: Home Assistant's instance has been listening
#: since it started, so a record on this network is usually in its cache.
BROWSE_SECONDS = 2.0


async def _async_adverts(hass: HomeAssistant) -> network_names.BrowseResult:
    """Browse for Sungrow records through Home Assistant's zeroconf instance."""
    instance = await ha_zeroconf.async_get_async_instance(hass)
    return await network_names.async_browse_result(
        BROWSE_SECONDS, zeroconf=instance.zeroconf
    )


@callback
def _home_assistant(hass: HomeAssistant, entry: ConfigEntry[Any]) -> dict[str, object]:
    """Return what Home Assistant's own discovery knows of this entry's address.

    No MAC, host name or address goes out, only whether. `dhcp_knows_address`
    is None where Home Assistant's DHCP discovery does not run; a true one does
    not say whether a DHCP request, a router or a network scan told it.
    """
    known: bool | None = None
    if "dhcp" in hass.config.components:
        # Here: its own requirements are only sure to be installed where it runs.
        from homeassistant.components.dhcp import async_discovered_service_info

        host = entry.data.get(CONF_HOST)
        known = any(info.ip == host for info in async_discovered_service_info(hass))
    return {"set_up_by": sorted(entry.discovery_keys), "dhcp_knows_address": known}


async def async_network_names(
    hass: HomeAssistant,
    entry: ConfigEntry[Any],
    serials: Iterable[str | None] = (),
) -> dict[str, object]:
    """Return `network_names` for the device this entry talks to."""
    host: str = entry.data.get(CONF_HOST, "")
    browsed: network_names.BrowseResult | None = None
    why: str | None = None
    try:
        browsed = await _async_adverts(hass)
    except (RuntimeError, OSError) as err:
        # Recorded in the document as why nothing was browsed; the traceback
        # goes to the log for whoever has to explain it.
        _LOGGER.exception("mDNS browse for the diagnosis failed")
        why = f"{type(err).__name__}: {err}"
    return network_names.network_section(
        host=host,
        device_serials=[serial for serial in serials if serial],
        adverts=list(browsed.adverts) if browsed is not None else None,
        browse_error=why,
        browse_seconds=BROWSE_SECONDS,
        hostname=await async_hostname(host),
        mac_prefix=await async_mac_prefix(host),
        services_heard=browsed.heard if browsed is not None else None,
        on_segment=on_device_segment(host),
        home_assistant=_home_assistant(hass, entry),
    )
