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

from homeassistant.components import zeroconf as ha_zeroconf
from homeassistant.core import HomeAssistant
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


async def async_network_names(
    hass: HomeAssistant, host: str, serials: Iterable[str | None] = ()
) -> dict[str, object]:
    """Return `network_names` for the device at `host`."""
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
    )
