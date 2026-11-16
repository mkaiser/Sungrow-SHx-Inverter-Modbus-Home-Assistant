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
from custom_components.sungrow_modbus.wifi_module import is_locally_administered
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


def _found(host: str, *, direct: bool, mac: str | None = "AC:19:9F") -> dict:
    """One identified address, as `_async_identify` builds it."""
    return {
        "mac_prefix": mac,
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


def test_untold_apart_cards_fall_back_to_the_numeric_address() -> None:
    """The tiebreak that picks the default where nothing else can.

    Measured at the maintainer's house: a proxy at .125 in front of the
    inverter at .35, Home Assistant somewhere else again, so `local` names
    neither and no ARP entry exists to read a vendor prefix from. Every
    key above the address ties, and a text sort then offered .125 -- not
    because it was the better address but because "1" sorts before "3".
    """
    hosts = ["192.168.178.125", "192.168.178.35", "192.168.178.9"]
    described = _described(
        {host: _found(host, direct=True, mac=None) for host in hosts}
    )

    assert list(described) == [
        "192.168.178.9",
        "192.168.178.35",
        "192.168.178.125",
    ]


def test_a_hostname_sorts_after_the_addresses() -> None:
    """A name has no numeric order, and must not break the sort either."""
    described = _described(
        {
            "inverter.local": _found("inverter.local", direct=True, mac=None),
            "192.168.178.35": _found("192.168.178.35", direct=True, mac=None),
        }
    )

    assert list(described) == ["192.168.178.35", "inverter.local"]


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


def test_a_foreign_mac_says_something_is_relaying() -> None:
    """The half the local-address test cannot reach: a proxy on a third machine.

    `AC:19:9F` is Sungrow's one IEEE registration, so an address answering
    as an inverter from another vendor's hardware is not the inverter. This
    is the only evidence here that works when the proxy is neither this
    machine nor the device.
    """
    described = _described(
        {
            CABLE: _found(CABLE, direct=True),
            PROXY: _found(PROXY, direct=True, mac="B8:27:EB"),
        }
    )

    assert "B8:27:EB" in described[PROXY]["label"]
    assert "relaying" in described[PROXY]["label"]
    assert "relaying" not in described[CABLE]["label"]


@pytest.mark.parametrize(
    ("prefix", "invented"),
    [
        ("AC:19:9F", False),  # Sungrow, measured at an inverter's own LAN port
        ("AC:1F:09", False),  # RAKwireless, a communication module's own port
        ("B8:27:EB", False),  # Raspberry Pi, a real maker of real hardware
        ("02:42:AC", True),  # Docker's bridge
        ("02:D2:D3", True),  # the shape the maintainer's proxy answered with
        ("", False),  # no answer is not an accusation
        ("not a mac", False),
    ],
)
def test_the_u_l_bit_tells_an_issued_port_from_an_invented_one(
    prefix: str, invented: bool
) -> None:
    """Bit 1 of the first octet, and nothing else.

    `AC` and `B8` are even; `02` is not. The point of reading the bit rather
    than keeping a list of hypervisor prefixes is that IEEE issues no prefix
    with it set, so the rule cannot go stale.
    """
    assert is_locally_administered(prefix) is invented


def test_an_invented_mac_is_decided_and_not_merely_noted() -> None:
    """The one prefix test strong enough to rank a card.

    Measured at the maintainer's house: the inverter at its own LAN port
    answered Sungrow's `AC:19:9F`, and the proxy beside it a locally
    administered prefix -- its Home Assistant runs on a virtual machine, as
    most do, and a hypervisor invents its NIC's address. Nothing a
    manufacturer ships can answer this way, so unlike a foreign registered
    prefix there is no second reading to wait for.
    """
    described = _described(
        {
            CABLE: _found(CABLE, direct=True),
            PROXY: _found(PROXY, direct=True, mac="02:42:AC"),
        }
    )

    assert described[PROXY]["proxy"] is True
    assert "Modbus proxy" in described[PROXY]["label"]
    # And it ranks, which is the whole difference from the note below.
    assert list(described) == [PROXY, CABLE]


def test_an_invented_mac_in_front_of_a_dongle_is_still_a_proxy() -> None:
    """A dongle has a maker, so the two cannot be confused.

    A WiNet-S or a RAK stick is hardware with an issued prefix; a proxy in
    front of one is a host with an invented one. Which is why this test
    needs no help from the route -- and the route still decides first, so
    the proxied dongle stays below a cable.
    """
    described = _described(
        {
            CABLE: _found(CABLE, direct=True),
            PROXY: _found(PROXY, direct=False, mac="02:42:AC"),
        }
    )

    assert described[PROXY]["proxy"] is True
    assert list(described) == [CABLE, PROXY]


def test_a_registered_foreign_mac_stays_a_note() -> None:
    """The weaker half, held where it was: said, never ranked.

    A second Sungrow registration would make this wrong, and a card that
    only reads oddly costs less than a card that ranks wrongly.
    """
    described = _described(
        {
            CABLE: _found(CABLE, direct=True),
            PROXY: _found(PROXY, direct=True, mac="B8:27:EB"),
        }
    )

    assert not described[PROXY].get("proxy")


def test_no_arp_entry_accuses_nobody() -> None:
    """Three-valued, like every probe here: absent is not foreign.

    An ARP entry exists only on the same segment, so behind a router, a VPN
    or a container bridge every address answers `None` -- which is the
    devcontainer this is developed in. Reading that as "not Sungrow" would
    label every inverter a proxy wherever the cache cannot see.
    """
    described = _described(
        {
            CABLE: _found(CABLE, direct=True, mac=None),
            DONGLE: _found(DONGLE, direct=False, mac=None),
        }
    )

    assert not any("relaying" in entry["label"] for entry in described.values())


def test_a_sungrow_mac_is_left_unremarked() -> None:
    """The ordinary case says nothing: a note everybody gets is noise."""
    described = _described({CABLE: _found(CABLE, direct=True)})

    assert "AC:19:9F" not in described[CABLE]["label"]


def test_the_two_proxy_tests_agree_and_do_not_repeat_each_other() -> None:
    """Home Assistant's own address *and* a foreign MAC: both said, once each."""
    described = _described(
        {
            CABLE: _found(CABLE, direct=True),
            PROXY: _found(PROXY, direct=True, mac="B8:27:EB"),
        },
        local={PROXY},
    )
    label = described[PROXY]["label"]

    assert label.count("Modbus proxy") == 2
    assert "Home Assistant's own address" in label
    assert "B8:27:EB" in label
