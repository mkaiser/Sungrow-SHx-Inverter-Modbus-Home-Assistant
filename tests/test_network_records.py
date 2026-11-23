"""The diagnosis button's `network_names`, read through Home Assistant's zeroconf."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import network_records
from custom_components.sungrow_modbus.const import DOMAIN
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery_flow import DiscoveryKey
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from sungrow_modbus.network_names import Advert, BrowseResult

HOST = "192.0.2.10"
ENTRY = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})

#: Taken at import, before `conftest`'s autouse stub replaces it for the test.
REAL_ADVERTS = network_records._async_adverts


async def test_the_browse_goes_through_home_assistant_s_instance(
    hass: HomeAssistant,
) -> None:
    shared = MagicMock()
    heard = [
        Advert(
            instance="WiNet-WebServer",
            addresses=(HOST,),
            properties={"board": "SUNGROW;1;WiNet-S;B123456789;1;"},
        )
    ]
    with (
        patch.object(
            network_records.ha_zeroconf,
            "async_get_async_instance",
            AsyncMock(return_value=shared),
        ),
        patch.object(
            network_records.network_names,
            "async_browse_result",
            AsyncMock(return_value=BrowseResult(adverts=tuple(heard), heard=4)),
        ) as browse,
    ):
        browsed = await REAL_ADVERTS(hass)
    assert list(browsed.adverts) == heard
    # Carried through, because it is the half that says whether this machine
    # could have heard anything at all.
    assert browsed.heard == 4
    assert browse.await_args.kwargs == {"zeroconf": shared.zeroconf}


async def test_the_section_marks_this_device_and_carries_no_serial(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def heard(_hass: object) -> BrowseResult:
        return BrowseResult(
            adverts=(
                Advert(
                    instance="WiNet-WebServer",
                    addresses=(HOST,),
                    properties={"inverter": "1;3598;A123456789;1;516;SH10RT;1;4;"},
                ),
            ),
            heard=3,
        )

    async def prefix(_host: str) -> str:
        return "A4:CF:12"

    monkeypatch.setattr(network_records, "_async_adverts", heard)
    monkeypatch.setattr(network_records, "async_mac_prefix", prefix)
    section = await network_records.async_network_names(hass, ENTRY, ["A123456789"])
    assert section["mdns"]["state"] == "answered"
    assert section["mdns"]["services"][0]["this_device"] is True
    assert section["mac_vendor_prefix"] == "A4:CF:12"
    assert section["mdns"]["services_heard"] == 3
    assert "A123456789" not in str(section)


async def test_a_failed_browse_is_recorded_as_not_browsed(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def refused(_hass: object) -> BrowseResult:
        raise OSError("no multicast here")

    monkeypatch.setattr(network_records, "_async_adverts", refused)
    section = await network_records.async_network_names(hass, ENTRY)
    assert section["mdns"] == {
        "state": "not_browsed",
        "why": "OSError: no multicast here",
    }


async def test_what_home_assistant_s_discovery_knows(hass: HomeAssistant) -> None:
    section = await network_records.async_network_names(hass, ENTRY)
    # DHCP discovery does not run here, which is not the same as not knowing.
    assert section["home_assistant"] == {"set_up_by": [], "dhcp_knows_address": None}

    found = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        discovery_keys={
            "dhcp": (DiscoveryKey(domain="dhcp", key="aabbccddeeff", version=1),)
        },
    )
    hass.config.components.add("dhcp")
    for address, known in ((HOST, True), ("192.0.2.11", False)):
        seen = [DhcpServiceInfo(ip=address, hostname="x", macaddress="aabbccddeeff")]
        with patch(
            "homeassistant.components.dhcp.async_discovered_service_info",
            return_value=seen,
        ):
            section = await network_records.async_network_names(hass, found)
        assert section["home_assistant"] == {
            "set_up_by": ["dhcp"],
            "dhcp_knows_address": known,
        }
        assert "aabbcc" not in str(section).lower()
