"""A Modbus proxy is an address that answers as the inverter, because it is.

A proxy forwards everything: the serial, the device type, register 6100. So
over Modbus the proxy and the inverter are one device at two addresses, which
is the cable-and-dongle shape the picker already understood -- except that
here the route note is identical too, so the two cards are indistinguishable.

The one thing the flow *can* know is that an address belongs to Home
Assistant itself, which is where a proxy add-on runs. That is what names it,
and it is also what lets the move dialog say what moving off a proxy costs:
the inverter grants very few sessions, and a proxy is what shares them.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.config_flow_schemas import _described
from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DEVICES,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .test_config_flow_topology import SERIAL_A, _house

#: Home Assistant's own address, where a proxy add-on listens.
PROXY = "192.168.176.125"
CABLE = "192.168.176.34"
DONGLE = "192.168.176.28"


@pytest.fixture(autouse=True)
def _no_network_on_reload():
    """Keep a reloaded entry off the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


def _adapters(*addresses: str):
    """Patch Home Assistant's own addresses to exactly these."""
    return patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [
                    {"address": address, "network_prefix": 24} for address in addresses
                ],
            }
        ],
    )


def _found(host: str, *, direct: bool) -> dict:
    """One identified address, as `_async_identify` builds it."""
    return {
        CONF_HOST: host,
        CONF_PORT: 502,
        CONF_UNIT_ID: 1,
        "serial": SERIAL_A,
        "model": "SH10RT",
        "kind": {},
        "hostname": None,
        "direct": direct,
        "battery": True,
        "label": "",
    }


def test_home_assistants_own_address_is_named_as_a_proxy() -> None:
    """Otherwise two cards read the same and only the address differs.

    A proxy forwards 6100, so the route note describes what is *behind* it:
    both addresses say "the inverter's own LAN port". Without this the only
    thing telling a user which card is the proxy is recognising their own
    Home Assistant's IP address on sight.
    """
    described = _described(
        {CABLE: _found(CABLE, direct=True), PROXY: _found(PROXY, direct=True)},
        local={PROXY},
    )

    assert "Modbus proxy" in described[PROXY]["label"]
    assert "Modbus proxy" not in described[CABLE]["label"]
    # Still said to be one inverter, which is what makes the pair legible.
    assert CABLE in described[PROXY]["label"]
    assert PROXY in described[CABLE]["label"]


def test_the_proxy_is_offered_first() -> None:
    """It reaches the same path and shares the port rather than taking it."""
    described = _described(
        {CABLE: _found(CABLE, direct=True), PROXY: _found(PROXY, direct=True)},
        local={PROXY},
    )

    assert list(described) == [PROXY, CABLE]


def test_a_proxy_in_front_of_a_dongle_never_outranks_a_cable() -> None:
    """The route decides first, and only then the proxy.

    A proxy's `direct` describes what is behind it, so a proxied dongle is
    still a dongle -- which forwards 1020 of 1510 addresses where a cable
    forwards 1461. Ranking it first would cost entities to save sessions.
    """
    described = _described(
        {CABLE: _found(CABLE, direct=True), PROXY: _found(PROXY, direct=False)},
        local={PROXY},
    )

    assert list(described) == [CABLE, PROXY]


def test_nothing_is_a_proxy_when_no_address_is_ours() -> None:
    """The default: `local` empty says nothing rather than guessing."""
    described = _described(
        {CABLE: _found(CABLE, direct=True), DONGLE: _found(DONGLE, direct=False)}
    )

    assert not any("proxy" in entry["label"] for entry in described.values())
    assert not any(entry.get("proxy") for entry in described.values())


def _entry(hass: HomeAssistant, host: str) -> MockConfigEntry:
    """Return an inverter entry reached at `host`."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: host,
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DEVICES,
        },
        unique_id=SERIAL_A,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    return entry


async def _move_to(hass: HomeAssistant, entry: MockConfigEntry, host: str) -> dict:
    """Reconfigure `entry` onto `host` and return the move dialog."""
    result = await entry.start_reconfigure_flow(hass)
    with (
        _house({PROXY: {1: SERIAL_A}, CABLE: {1: SERIAL_A}}),
        _adapters(PROXY),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: host, CONF_PORT: 502, CONF_UNIT_ID: 1}
        )
    assert result["step_id"] == "move", result
    return result


async def test_moving_off_a_proxy_says_what_it_costs(hass: HomeAssistant) -> None:
    """The DHCP trap, caught at the only point where damage is done.

    A DHCP sighting carries the *inverter's* address -- the proxy has Home
    Assistant's MAC, so it is never a DHCP candidate -- and the sighting's
    unique id is the MAC, settled before any register is read. So neither
    the address check nor the unique id can match an entry that reaches the
    same inverter through a proxy, and the offer arrives here looking like
    any other new path.
    """
    entry = _entry(hass, PROXY)
    result = await _move_to(hass, entry, CABLE)

    assert "Modbus proxy" in result["description_placeholders"]["proxy"]
    assert "{proxy}" not in result["description_placeholders"]["proxy"]


async def test_moving_onto_a_proxy_says_nothing(hass: HomeAssistant) -> None:
    """Nothing is lost in that direction, so there is nothing to warn about."""
    entry = _entry(hass, CABLE)
    result = await _move_to(hass, entry, PROXY)

    assert result["description_placeholders"]["proxy"] == ""
