"""The diagnosis button's `network_names`, read through Home Assistant's zeroconf."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.sungrow_modbus import network_records
from homeassistant.core import HomeAssistant
from sungrow_modbus.network_names import Advert

HOST = "192.0.2.10"

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
            "async_browse",
            AsyncMock(return_value=heard),
        ) as browse,
    ):
        adverts = await REAL_ADVERTS(hass)
    assert adverts == heard
    assert browse.await_args.kwargs == {"zeroconf": shared.zeroconf}


async def test_the_section_marks_this_device_and_carries_no_serial(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def heard(_hass: object) -> list[Advert]:
        return [
            Advert(
                instance="WiNet-WebServer",
                addresses=(HOST,),
                properties={"inverter": "1;3598;A123456789;1;516;SH10RT;1;4;"},
            )
        ]

    async def prefix(_host: str) -> str:
        return "A4:CF:12"

    monkeypatch.setattr(network_records, "_async_adverts", heard)
    monkeypatch.setattr(network_records, "async_mac_prefix", prefix)
    section = await network_records.async_network_names(hass, HOST, ["A123456789"])
    assert section["mdns"]["state"] == "answered"
    assert section["mdns"]["services"][0]["this_device"] is True
    assert section["mac_vendor_prefix"] == "A4:CF:12"
    assert "A123456789" not in str(section)


async def test_a_failed_browse_is_recorded_as_not_browsed(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def refused(_hass: object) -> list[Advert]:
        raise OSError("no multicast here")

    monkeypatch.setattr(network_records, "_async_adverts", refused)
    section = await network_records.async_network_names(hass, HOST)
    assert section["mdns"] == {
        "state": "not_browsed",
        "why": "OSError: no multicast here",
    }
