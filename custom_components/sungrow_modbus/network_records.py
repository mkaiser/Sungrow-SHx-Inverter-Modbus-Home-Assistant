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
from sungrow_modbus.network_names import async_mac_prefix

_LOGGER = logging.getLogger(__name__)

#: Shorter than the terminal's: Home Assistant's instance has been listening
#: since it started, so a record on this network is usually in its cache.
BROWSE_SECONDS = 2.0


async def _async_adverts(hass: HomeAssistant) -> list[network_names.Advert]:
    """Browse for Sungrow records through Home Assistant's zeroconf instance."""
    instance = await ha_zeroconf.async_get_async_instance(hass)
    return await network_names.async_browse(BROWSE_SECONDS, zeroconf=instance.zeroconf)


async def async_network_names(
    hass: HomeAssistant, host: str, serials: Iterable[str | None] = ()
) -> dict[str, object]:
    """Return `network_names` for the device at `host`."""
    adverts: list[network_names.Advert] | None = None
    why: str | None = None
    try:
        adverts = await _async_adverts(hass)
    except (RuntimeError, OSError) as err:
        # Recorded in the document as why nothing was browsed; the traceback
        # goes to the log for whoever has to explain it.
        _LOGGER.exception("mDNS browse for the diagnosis failed")
        why = f"{type(err).__name__}: {err}"
    return network_names.network_section(
        host=host,
        device_serials=[serial for serial in serials if serial],
        adverts=adverts,
        browse_error=why,
        browse_seconds=BROWSE_SECONDS,
        hostname=await async_hostname(host),
        mac_prefix=await async_mac_prefix(host),
    )
