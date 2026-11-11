"""Which path an endpoint is: the inverter's own port, or a module in between.

Register 6100 decides it (`.wiki/wiki/concepts/transport-detection.md`): it
answers with no communication module in the path, and a WiNet-S or a Logger
refuses it. Whether a WiNet-S is on its cable or its WiFi no register says,
so nothing here guesses it.
"""

from __future__ import annotations

from collections.abc import Awaitable

from modbus_connection import (
    ModbusError,
    ModbusExceptionError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

from .coordinator import SungrowConfigEntry

#: The Modbus TCP port, left out of the address shown on the device page.
DEFAULT_MODBUS_PORT = 502


async def async_direct(probe: Awaitable[object]) -> bool | None:
    """Return whether register 6100 says this endpoint is the inverter's own port.

    Three answers. Answered is a cable: no communication module forwards the
    block. Refused is a module in the path -- a refusal is the transport
    answering, and only a refusal is. Anything else is `None`: 0x06 says "ask
    me later" rather than "no such register", and so does 0x04 from a WiNet-S
    other clients are polling; and a lost, timed-out or desynced read is the
    link not carrying the question. Reading either as a refusal would tell a
    house with no module fitted that it has a dongle.
    """
    try:
        await probe
    except (ServerDeviceBusyError, ServerDeviceFailureError):
        return None
    except ModbusExceptionError:
        return False
    except (ModbusError, HomeAssistantError, TimeoutError, OSError):
        return None
    return True


#: The *Connection* sensor's states, and the label each has on the device
#: page, where Home Assistant does not translate.
ROUTE_DIRECT = "direct"
ROUTE_WINET = "winet"
ROUTE_MODULE = "module"
ROUTE_LABELS: dict[str, str] = {
    ROUTE_DIRECT: "direct, no dongle",
    ROUTE_WINET: "via WiNet-S",
    ROUTE_MODULE: "via a communication module",
}

#: Entities this module names, by domain and translation key, for
#: `scripts/generate/descriptions.py strings` (`naming.OVERRIDES`).
ROUTE_ENTITIES: tuple[tuple[str, str], ...] = (("sensor", "connection"),)


def route_key(direct: bool | None, module: str | None) -> str | None:
    """Name the path, or None when 6100 could not say.

    Direct covers an RS485 converter as well as the LAN port: 6100 answers on
    both, so it says only that no module is in between. Through a module, the
    fitted one is named where it is a WiNet-S; a Logger refuses 6100 too, and
    is not what 13265 reports.
    """
    if direct is True:
        return ROUTE_DIRECT
    if direct is False:
        if module and module.upper().startswith("WINET"):
            return ROUTE_WINET
        return ROUTE_MODULE
    return None


def address(entry: SungrowConfigEntry) -> str:
    """Return the host, and the port where it is not Modbus TCP's own."""
    host = str(entry.data.get(CONF_HOST, ""))
    port = entry.data.get(CONF_PORT, DEFAULT_MODBUS_PORT)
    return host if port == DEFAULT_MODBUS_PORT else f"{host}:{port}"


def web_interface(entry: SungrowConfigEntry, route: str | None) -> str | None:
    """Return the WiNet-S's web interface, the endpoint's own host, or None.

    Only through a WiNet-S: the inverter's own LAN port serves no web page,
    and a link that leads nowhere is worse than none. HTTPS, not HTTP: a
    WiNet-S refuses port 80 and serves its page on 443, under a self-signed
    certificate the browser asks about once (measured at two houses; its
    mDNS record still names port 80).
    """
    if route != ROUTE_WINET:
        return None
    return f"https://{entry.data.get(CONF_HOST, '')}"


def connection_text(entry: SungrowConfigEntry, route: str | None) -> str:
    """Return the address, and the path where it is known, for the device page."""
    label = ROUTE_LABELS.get(route or "")
    return f"{address(entry)} · {label}" if label else address(entry)
