"""What a DHCP sighting can tell this integration, and the WiFi module it can link.

Two kinds of device ask a router for an address and are worth a look:

- **A Sungrow network port**, by its MAC address: `AC:19:9F` is the one
  vendor prefix the IEEE registry lists for SUNGROW POWER SUPPLY CO.,LTD.,
  and an inverter's own LAN port carries it (wiki: peter_sm's twentieth
  reading). Such a port announces nothing over mDNS, so DHCP is the only way
  Home Assistant notices it by itself. The sighting decides only whether to
  **offer**; what answers over Modbus decides what it is.
- **A RAK WiFi module** (hostname `rakmodule-` and six hex digits, a
  RAKwireless MAC), the older WiFi stick some inverters carry. It is no Modbus
  device: on 502 it accepts a connection and echoes what it is sent (wiki: the
  RAK WiFi module). What it has is a web page, on port 80 behind a login. The
  inverter does not report it over Modbus (the maintainer's P020 names no
  communication module), so which inverter it belongs to only the owner
  knows: the flow asks, and the answer is stored on that inverter's entry.

Nothing here reads the network. The entry keeps the module's address, MAC and
hostname; the device page links the page, and the diagnostics download names
the module with its address redacted.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import CONF_KIND, CONF_WIFI_MODULE, DOMAIN, KIND_STRING_INVERTER

#: Sungrow's one IEEE vendor prefix, as Home Assistant's DHCP matcher writes
#: it (`manifest.json`, `macaddress`).
SUNGROW_MAC_PREFIX = "AC199F"

#: How a RAK WiFi module names itself to the router, before the last three
#: octets of its MAC (`rakmodule-01D066`).
RAK_HOSTNAME_PREFIX = "rakmodule-"

#: The module's device, by MAC: one module is one device, whichever entry
#: links it.
IDENTIFIER_PREFIX = "wifi_module_"

#: Entry data keys inside `CONF_WIFI_MODULE`.
MAC = "mac"
HOSTNAME = "hostname"


def is_sungrow_mac(mac: str) -> bool:
    """Return whether a MAC address carries Sungrow's vendor prefix."""
    return _bare(mac).startswith(SUNGROW_MAC_PREFIX)


def is_rak_module(hostname: str | None) -> bool:
    """Return whether a DHCP hostname is a RAK WiFi module's."""
    return (hostname or "").lower().startswith(RAK_HOSTNAME_PREFIX)


def web_page(module: dict[str, Any]) -> str:
    """Return the module's web page: plain HTTP, port 80, behind a login."""
    return f"http://{module[CONF_HOST]}/"


def inverter_entries(entries: list[ConfigEntry]) -> list[ConfigEntry]:
    """Return the entries a WiFi module can belong to: inverters, not wallboxes.

    A hybrid inverter's entry carries no kind; an SG's says so. A wallbox, an
    iHomeManager or a Logger has an entry of its own and no WiFi stick.
    """
    return [
        entry
        for entry in entries
        if entry.data.get(CONF_KIND) in (None, KIND_STRING_INVERTER)
    ]


def linked_to(entries: list[ConfigEntry], mac: str) -> ConfigEntry | None:
    """Return the entry this module is already linked to, if any."""
    for entry in entries:
        module = entry.data.get(CONF_WIFI_MODULE)
        if module and _bare(module.get(MAC, "")) == _bare(mac):
            return entry
    return None


@callback
def async_register(
    hass: HomeAssistant, entry: ConfigEntry, inverter: dr.DeviceInfo
) -> None:
    """Show the linked module under its inverter, and drop one no longer linked.

    A device of its own rather than the inverter's link: the inverter's
    *Visit* is the WiNet-S's page where one is the path (`route.py`), and a
    module that is not the path still has a page worth one click.
    """
    registry = dr.async_get(hass)
    module = entry.data.get(CONF_WIFI_MODULE)
    wanted = (DOMAIN, IDENTIFIER_PREFIX + _bare(module[MAC])) if module else None
    if module:
        registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={wanted},  # type: ignore[arg-type]
            connections={(dr.CONNECTION_NETWORK_MAC, dr.format_mac(module[MAC]))},
            manufacturer="RAKwireless",
            model="WiFi module",
            name=f"{entry.title} WiFi module",
            configuration_url=web_page(module),
            via_device=next(iter(inverter["identifiers"])),
        )
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if is_module_device(device) and wanted not in device.identifiers:
            registry.async_remove_device(device.id)


@callback
def async_refresh(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bring a loaded entry's module device in step with a changed link.

    The link is not something setup builds from, so changing it reloads
    nothing (`_built_from`); an entry not loaded catches up at its setup.
    """
    if entry.state is not ConfigEntryState.LOADED:
        return
    runtime = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime, "inverter_coordinator", None)
    if coordinator is not None:
        async_register(hass, entry, coordinator.device_info)


def is_module_device(device: dr.DeviceEntry) -> bool:
    """Return whether a device is a linked WiFi module's."""
    return any(
        domain == DOMAIN and str(key).startswith(IDENTIFIER_PREFIX)
        for domain, key in device.identifiers
    )


def diagnostics(entry: ConfigEntry) -> dict[str, Any] | None:
    """Name the linked module for a diagnostics download, with no address.

    The hostname's tail is the MAC's last three octets, so only its prefix
    goes in; the vendor prefix names a manufacturer, never one device.
    """
    module = entry.data.get(CONF_WIFI_MODULE)
    if not module:
        return None
    mac = dr.format_mac(module[MAC]).upper()
    return {
        "hostname_prefix": RAK_HOSTNAME_PREFIX
        if is_rak_module(module.get(HOSTNAME))
        else None,
        "mac_vendor_prefix": mac[:8],
        "web_page": "http://**REDACTED**/",
    }


def _bare(mac: str) -> str:
    return mac.replace(":", "").replace("-", "").upper()
