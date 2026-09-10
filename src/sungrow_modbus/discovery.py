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


def network_of(address: str, prefix: int) -> str:
    """Return the network an interface address belongs to, as a CIDR string."""
    interface = ipaddress.ip_interface(f"{address}/{prefix}")
    return str(interface.network)
