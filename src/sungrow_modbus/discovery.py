"""Finding inverters on a network, without asking the user to know their IP.

Two things make this less trivial than sweeping for open ports.

**An open port 502 is not a Modbus device.** Sweeping the maintainer's own LAN
turned up a RAKwireless gateway that accepts a connection on 502 and echoes
whatever it is sent. Anything that reports open ports as "inverters found"
will hand that to a user as a candidate. So the sweep here only produces
*candidates*, and something has to read a register before any of them is
called an inverter — which the config flow does, because it has Home
Assistant's shared connection to do it with.

**A sweep is a network event, not a query.** Every address probed is an ARP
entry and a SYN. A /24 finishes in about a second; a /16 takes minutes and
floods the segment. So the size is capped and the caller has to raise the cap
deliberately rather than discover it by waiting.

Nothing here imports Home Assistant, and nothing here opens a Modbus
connection — the point is that both sides can use it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import ipaddress
import socket
from typing import Any, NamedTuple, cast

from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .addresses import IHOMEMANAGER_PROTOCOL, IHOMEMANAGER_TYPE, field_address
from .const import model_for
from .model import words_text

#: Sweeping more than this many addresses at once is almost always a mistake —
#: a mistyped prefix rather than an intent. A /24 is 254 hosts.
MAX_HOSTS = 1024

#: Open sockets at a time. High enough that a /24 finishes in about a second,
#: low enough not to exhaust file descriptors on a small system.
CONCURRENCY = 64

#: Per-address connect timeout. A device on the same segment answers in
#: milliseconds; this only has to outlast a slow switch.
TIMEOUT = 1.0

DEFAULT_PORT = 502


async def async_mdns_services(seconds: float = 2.0) -> dict[str, dict[str, object]]:
    """Browse available mDNS services when the optional extra is installed.

    Importing ``zeroconf`` lazily keeps the base wheel suitable for headless
    Modbus clients and Home Assistant. Callers can catch ``RuntimeError`` and
    offer the package extra or a regular network sweep instead.
    """
    try:
        from zeroconf import ServiceBrowser, ServiceStateChange
        from zeroconf.asyncio import AsyncZeroconf
    except ModuleNotFoundError as err:
        raise RuntimeError(
            "mDNS discovery requires the optional 'discovery' extra "
            "(pip install sungrow-modbus[discovery])"
        ) from err

    found: dict[str, dict[str, object]] = {}
    discovered_types: set[str] = set()
    azc = AsyncZeroconf()
    zc = azc.zeroconf

    def on_type(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: object,
        **kwargs: object,
    ) -> None:
        if state_change is ServiceStateChange.Added:
            discovered_types.add(name)

    meta = ServiceBrowser(zc, "_services._dns-sd._udp.local.", handlers=[on_type])
    await asyncio.sleep(seconds)
    meta.cancel()

    def on_change(
        zeroconf: Any,
        service_type: str,
        name: str,
        state_change: object,
        **kwargs: object,
    ) -> None:
        if state_change is not ServiceStateChange.Added:
            return
        info = zeroconf.get_service_info(service_type, name, timeout=2000)
        if info is None:
            return
        properties = {
            (key.decode(errors="replace") if isinstance(key, bytes) else key): (
                value.decode(errors="replace") if isinstance(value, bytes) else value
            )
            for key, value in (info.properties or {}).items()
        }
        found[name] = {
            "type": service_type,
            "addresses": [str(address) for address in info.parsed_addresses()],
            "port": info.port,
            "properties": properties,
        }

    types = sorted(discovered_types) or (
        "_http._tcp.local.",
        "_workstation._tcp.local.",
        "_device-info._tcp.local.",
    )
    browsers = [
        ServiceBrowser(zc, service_type, handlers=[on_change]) for service_type in types
    ]
    await asyncio.sleep(seconds)
    for browser in browsers:
        browser.cancel()
    await azc.async_close()
    return found


#: Unit ids tried when looking for an inverter at an address, in order.
#:
#: 1 first, because it is what Sungrow's app and manual assume and what all
#: but one measured machine uses. Then 2, measured on 2026-09-09 at a house
#: with two inverters: the second answers on unit **2** at its own LAN port
#: and times out on 1, because a cluster slave's own device address is 2.
#: Then 3 to 5, which the specification allows for further slaves and which
#: nothing has been measured on.
#:
#: Only inverter-shaped units: a battery at 200 and a wallbox at 3 are found
#: behind an endpoint that has already answered. The config flow and the
#: survey's `identify()` both sweep this list.
IDENTIFY_UNITS: tuple[int, ...] = (1, 2, 3, 4, 5)
IHOMEMANAGER_UNIT = 247


class Identity(NamedTuple):
    """Identity reported by a Sungrow endpoint."""

    serial: str | None
    device_type_code: int | None
    model: str | None
    error: str | None = None
    unit: int | None = None
    kind: str | None = None


class NetworkTooLarge(ValueError):
    """Raised when a sweep would probe more addresses than MAX_HOSTS."""

    def __init__(self, network: str, hosts: int, limit: int) -> None:
        """Say what was asked for and what the limit is."""
        super().__init__(
            f"{network} holds {hosts} addresses, over the limit of {limit}"
        )
        self.network = network
        self.hosts = hosts
        self.limit = limit


def host_count(network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> int:
    """Return how many usable addresses a network holds, without listing them."""
    if network.num_addresses <= 2:
        # A /31 or /32: no network and broadcast address to set aside.
        return network.num_addresses
    return network.num_addresses - 2


def hosts_in(network: str, *, limit: int = MAX_HOSTS) -> list[str]:
    """Return every usable address in a network, or raise if there are too many.

    The size is checked **arithmetically, before any address is generated**.
    Counting by building the list first works and is a line shorter, but a
    user who types /8 into the search box then waits twenty seconds and
    several gigabytes for the error that was knowable immediately.
    """
    parsed = ipaddress.ip_network(network, strict=False)
    count = host_count(parsed)
    if count > limit:
        raise NetworkTooLarge(str(parsed), count, limit)
    # A /32 has no "hosts" in the iterator's sense, but scanning one address is
    # a perfectly reasonable thing to ask for.
    return [str(host) for host in parsed.hosts()] or [str(parsed.network_address)]


async def async_port_open(host: str, port: int, timeout: float = TIMEOUT) -> bool:
    """Return whether a TCP connection to host:port completes."""
    try:
        connect = asyncio.open_connection(host, port)
        _, writer = await asyncio.wait_for(connect, timeout)
    except (TimeoutError, OSError):
        return False
    writer.close()
    with contextlib.suppress(OSError, asyncio.TimeoutError):
        await writer.wait_closed()
    return True


async def async_sweep(
    network: str,
    *,
    port: int = DEFAULT_PORT,
    concurrency: int = CONCURRENCY,
    timeout: float = TIMEOUT,
    limit: int = MAX_HOSTS,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[str]:
    """Return the addresses in `network` with `port` open.

    Candidates, not inverters. The caller reads a register to decide.

    `on_progress(done, total)` is called as each address is settled, so a
    caller can show a bar. A `/24` at the default concurrency is quick, but
    the timeout is what a sweep spends most of its time on -- every address
    with nothing listening costs the full `timeout` -- so a sweep of a quiet
    network is exactly the case where somebody wonders whether it has hung.
    Plain callback rather than anything cleverer: this package has no Home
    Assistant in it and no event loop of its own to hook into.
    """
    addresses = hosts_in(network, limit=limit)
    semaphore = asyncio.Semaphore(concurrency)
    total = len(addresses)
    settled = 0

    async def check(host: str) -> str | None:
        nonlocal settled
        async with semaphore:
            open_port = await async_port_open(host, port, timeout)
        settled += 1
        if on_progress is not None:
            on_progress(settled, total)
        return host if open_port else None

    found = await asyncio.gather(*(check(host) for host in addresses))
    return [host for host in found if host is not None]


async def async_hostname(host: str, timeout: float = TIMEOUT) -> str | None:
    """Return the reverse-DNS name for an address, or None.

    Worth doing even though it often fails: on a home network the router is
    usually the DNS server and does serve PTR records — a Fritz!Box answers
    `<name>.fritz.box` — so a list of bare addresses becomes a list of names
    the user recognises. Where there is no PTR record this returns None and
    the caller shows the address, which is no worse than not having tried.
    """
    loop = asyncio.get_running_loop()
    try:
        name, _ = await asyncio.wait_for(
            loop.getnameinfo((host, 0), socket.NI_NAMEREQD), timeout
        )
    except (TimeoutError, OSError, socket.gaierror):
        return None
    return None if name == host else name


async def async_identify(
    host: str,
    port: int = DEFAULT_PORT,
    *,
    timeout: float = 5,
    connection_factory: Callable[..., Any] = ModbusConnection,
) -> Identity:
    """Identify the first inverter-like unit answering at an endpoint."""
    connection = connection_factory(
        ModbusTcpParams(host=host, port=port), timeout=timeout
    )
    try:
        first_error: str | None = None
        serial_address = field_address("serial_number")
        type_address = field_address("device_type_code")
        for unit_id in IDENTIFY_UNITS:
            unit = connection.for_unit(unit_id)
            try:
                values = await _read_words(unit, serial_address)
            except (ModbusError, TimeoutError, OSError) as err:
                if first_error is None:
                    first_error = type(err).__name__
                continue
            serial = words_text(values).strip()
            if not serial:
                return Identity(
                    None,
                    None,
                    None,
                    "answered, but reported no serial",
                    unit_id,
                )
            try:
                device_type = await _read_words(unit, type_address)
            except (ModbusError, TimeoutError, OSError):
                return Identity(serial, None, None, None, unit_id)
            code = int(device_type[0])
            return Identity(serial, code, model_for(code), None, unit_id)

        manager = await _identify_ihomemanager(connection)
        if manager is not None:
            return manager
        tried = ", ".join(str(unit_id) for unit_id in IDENTIFY_UNITS)
        return Identity(None, None, None, f"no serial at unit {tried} ({first_error})")
    finally:
        await connection.close()


async def _read_words(unit: Any, address: tuple[str, int, int]) -> list[int]:
    """Read one mapped field through the appropriate Modbus table."""
    space, register, count = address
    reader = (
        unit.read_holding_registers if space == "holding" else unit.read_input_registers
    )
    return cast("list[int]", await reader(register, count))


async def _identify_ihomemanager(connection: Any) -> Identity | None:
    """Return an iHomeManager identity if its identifying input answers."""
    unit = connection.for_unit(IHOMEMANAGER_UNIT)
    try:
        space, start, count = IHOMEMANAGER_TYPE
        values = await _read_words(unit, (space, start, count))
    except (ModbusError, TimeoutError, OSError):
        return None
    if not values or int(values[0]) in (0, 0xFFFF):
        return None
    code = int(values[0])
    try:
        space, start, count = IHOMEMANAGER_PROTOCOL
        raw = await _read_words(unit, (space, start, count))
    except (ModbusError, TimeoutError, OSError):
        return Identity(
            None, code, "iHomeManager", None, IHOMEMANAGER_UNIT, "ihomemanager"
        )
    protocol = words_text(raw, "utf-8").strip()
    model = "iHomeManager" if not protocol else f"iHomeManager (protocol {protocol})"
    return Identity(None, code, model, None, IHOMEMANAGER_UNIT, "ihomemanager")


def network_of(address: str, prefix: int) -> str:
    """Return the network an interface address belongs to, as a CIDR string."""
    interface = ipaddress.ip_interface(f"{address}/{prefix}")
    return str(interface.network)
