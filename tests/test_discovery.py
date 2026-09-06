"""Finding inverters on a network.

The load-bearing claim here is a negative one: **an open port 502 is not a
Modbus device.** Sweeping the maintainer's own LAN turned up a RAKwireless
gateway that accepts the connection and echoes bytes back. Any discovery that
reports open ports as "inverters found" hands that to the user as a candidate,
so the sweep produces candidates and something else has to read a register.
"""

from __future__ import annotations

import asyncio
import socket
from unittest.mock import patch

import pytest

from sungrow_modbus import NetworkTooLarge, async_sweep, hosts_in, network_of
from sungrow_modbus.discovery import async_hostname, async_port_open


def test_a_slash_24_is_the_254_usable_addresses() -> None:
    hosts = hosts_in("192.168.1.0/24")
    assert len(hosts) == 254
    assert hosts[0] == "192.168.1.1"
    assert hosts[-1] == "192.168.1.254"


def test_a_single_address_is_scannable() -> None:
    # /32 has no hosts in the iterator's sense, but scanning one address is a
    # perfectly reasonable thing to ask for.
    assert hosts_in("192.168.1.50/32") == ["192.168.1.50"]


def test_a_network_too_large_is_refused_with_the_numbers() -> None:
    # Every address probed is an ARP entry and a SYN on somebody's network, so
    # this fails immediately rather than after several minutes of sweeping.
    with pytest.raises(NetworkTooLarge) as raised:
        hosts_in("10.0.0.0/16")
    assert raised.value.hosts == 65534
    assert str(raised.value.limit) in str(raised.value)


def test_an_unparseable_range_is_a_value_error() -> None:
    with pytest.raises(ValueError):
        hosts_in("not-a-network")


def test_network_of_derives_the_subnet_from_an_interface_address() -> None:
    assert network_of("192.168.1.50", 24) == "192.168.1.0/24"
    assert network_of("172.17.0.2", 16) == "172.17.0.0/16"


async def test_a_closed_port_is_not_reported_open(socket_enabled: None) -> None:
    # Port 1 on the loopback: nothing listens there, and it refuses fast.
    assert await async_port_open("127.0.0.1", 1, timeout=1.0) is False


async def test_an_open_port_is_found_and_the_sweep_finds_it(
    socket_enabled: None,
) -> None:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        assert await async_port_open("127.0.0.1", port) is True
        assert await async_sweep("127.0.0.1/32", port=port) == ["127.0.0.1"]
    finally:
        server.close()
        await server.wait_closed()


async def test_the_sweep_refuses_a_range_it_should_not_probe() -> None:
    with pytest.raises(NetworkTooLarge):
        await async_sweep("10.0.0.0/8")


async def test_a_hostname_without_a_ptr_record_is_none_rather_than_an_error() -> None:
    # Most home networks answer for some addresses and not others, so the
    # caller has to cope with None -- it shows the address instead. Mocked
    # rather than resolved for real: a test must not depend on what the
    # machine running it can look up.
    with patch("sungrow_modbus.discovery.asyncio.get_running_loop") as loop:
        loop.return_value.getnameinfo = _raises(socket.gaierror("no PTR record"))
        assert await async_hostname("192.0.2.1", timeout=1.0) is None


async def test_a_slow_resolver_does_not_hold_the_flow_up() -> None:
    # A name is a nicety; waiting on a resolver that never answers is not.
    with patch("sungrow_modbus.discovery.asyncio.get_running_loop") as loop:
        loop.return_value.getnameinfo = _never_returns
        assert await async_hostname("192.168.1.50", timeout=0.05) is None


async def test_a_resolvable_address_gives_its_name() -> None:
    with patch("sungrow_modbus.discovery.asyncio.get_running_loop") as loop:
        loop.return_value.getnameinfo = _returns(("inverter.fritz.box", "0"))
        assert await async_hostname("192.168.1.50") == "inverter.fritz.box"


async def test_a_name_that_is_just_the_address_back_is_not_a_name() -> None:
    with patch("sungrow_modbus.discovery.asyncio.get_running_loop") as loop:
        loop.return_value.getnameinfo = _returns(("192.168.1.50", "0"))
        assert await async_hostname("192.168.1.50") is None


async def _never_returns(*args: object, **kwargs: object) -> None:
    """Stand in for a resolver that is not going to answer."""
    await asyncio.sleep(30)


def _raises(error: Exception):
    """Return an async callable that raises `error`."""

    async def _call(*args: object, **kwargs: object) -> None:
        raise error

    return _call


def _returns(value):
    """Return an async callable yielding `value`."""

    async def _call(*args, **kwargs):
        return value

    return _call
