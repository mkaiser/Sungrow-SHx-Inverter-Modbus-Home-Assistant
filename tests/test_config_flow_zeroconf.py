"""A WiNet-S or a wallbox that announces itself over mDNS is offered by Home Assistant.

The records are gerd's (wiki: *gerd's devices over mDNS*), with the test
serials. What is held here: the announcement only decides whether to
**offer** -- nothing is read over Modbus until the owner confirms, anything
already set up is left alone, and once confirmed the device is identified
over Modbus as the search identifies it.
"""

from __future__ import annotations

from ipaddress import ip_address
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_KIND,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_WALLBOX,
    WALLBOX_TLS_PORT,
)
from homeassistant.config_entries import SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .conftest import SERIAL
from .test_config_flow_search import _probe

DONGLE_HOST = "192.168.1.60"
WALLBOX_HOST = "192.168.1.70"
WALLBOX_SERIAL = "W123456789"
FLOW = "custom_components.sungrow_modbus.config_flow"


def _dongle(serial: str = SERIAL, inverter: bool = True) -> ZeroconfServiceInfo:
    properties = {"board": "SUNGROW;1;WiNet-S;B123456789;1;", "ethinfo": ""}
    if inverter:
        properties["inverter"] = f"1;3598;{serial};1;516;SH10RT;1;4;"
    return ZeroconfServiceInfo(
        ip_address=ip_address(DONGLE_HOST),
        ip_addresses=[ip_address(DONGLE_HOST)],
        port=80,
        hostname="SUNGROWB123456789.local.",
        type="_http._tcp.local.",
        name="WiNet-WebServer._http._tcp.local.",
        properties=properties,
    )


def _wallbox() -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address(WALLBOX_HOST),
        ip_addresses=[ip_address(WALLBOX_HOST)],
        port=516,
        hostname=f"SUNGROW{WALLBOX_SERIAL}.local.",
        type="_http._tcp.local.",
        name=f"SUNGROW{WALLBOX_SERIAL}._http._tcp.local.",
        properties={
            "board": f"SUNGROW;3;AC22E-01;{WALLBOX_SERIAL};1;248;",
            "info": "16256;516;1;",
        },
    )


@pytest.fixture
def no_setup():
    """Stop the created entry from reaching for the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


@pytest.fixture(autouse=True)
def _open_the_alpha_gate(devices_mode_offered: None) -> None:
    """Open the devices path, as the search tests do."""


def test_the_manifest_matches_both_announcements() -> None:
    manifest = json.loads(
        (
            Path(__file__).parent.parent
            / "custom_components"
            / "sungrow_modbus"
            / "manifest.json"
        ).read_text()
    )
    names = {matcher["name"] for matcher in manifest["zeroconf"]}
    assert names == {"winet-webserver*", "sungrow*"}
    assert "zeroconf" in manifest["after_dependencies"]


async def _discover(hass: HomeAssistant, info: ZeroconfServiceInfo) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=info
    )


async def test_a_dongle_is_offered_without_a_modbus_read(
    hass: HomeAssistant,
) -> None:
    with patch(f"{FLOW}.async_get_temporary_unit") as connect:
        result = await _discover(hass, _dongle())
    connect.assert_not_called()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"] == {
        "model": "SH10RT",
        "host": DONGLE_HOST,
        "via": "WiNet-S",
    }
    flow = hass.config_entries.flow.async_get(result["flow_id"])
    assert flow["context"]["unique_id"] == SERIAL
    assert flow["context"]["title_placeholders"] == {"name": f"SH10RT ({DONGLE_HOST})"}


async def test_confirming_identifies_over_modbus_and_creates_the_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, no_setup: None
) -> None:
    result = await _discover(hass, _dongle())
    with (
        _probe(sungrow_unit),
        patch(f"{FLOW}.async_hostname", return_value=None),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == DONGLE_HOST
    assert result["data"][CONF_PORT] == 502
    assert result["data"][CONF_UNIT_ID] == 1
    assert result["context"]["unique_id"] == SERIAL


async def test_a_dongle_that_does_not_answer_is_not_added(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    result = await _discover(hass, _dongle())
    with _probe(sungrow_unit, only=set()):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_identified"


async def test_an_inverter_already_set_up_is_left_alone(hass: HomeAssistant) -> None:
    # Set up on its own LAN port: the dongle announcing it must not move it.
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SERIAL,
        data={CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    result = await _discover(hass, _dongle())
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "192.168.1.50"


async def test_an_address_already_set_up_is_left_alone(hass: HomeAssistant) -> None:
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="A987654321",
        data={CONF_HOST: DONGLE_HOST, CONF_PORT: 502, CONF_UNIT_ID: 1},
    ).add_to_hass(hass)
    result = await _discover(hass, _dongle(serial="not-a-serial"))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_a_dongle_naming_no_inverter_is_not_offered(hass: HomeAssistant) -> None:
    result = await _discover(hass, _dongle(inverter=False))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_something_else_on_http_is_not_offered(hass: HomeAssistant) -> None:
    info = _dongle()
    info.properties = {"board": "OTHER;1;Thing;X;1;"}
    info.name = "Sungrow-lookalike._http._tcp.local."
    result = await _discover(hass, info)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_a_wallbox_gets_an_entry_of_its_own(
    hass: HomeAssistant, no_setup: None
) -> None:
    result = await _discover(hass, _wallbox())
    assert result["step_id"] == "discovery_confirm"
    assert result["description_placeholders"]["model"] == "AC22E-01"
    with patch(
        f"{FLOW}._async_probe_wallbox",
        AsyncMock(return_value=("AC22E-01", WALLBOX_SERIAL)),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_KIND] == KIND_WALLBOX
    assert result["data"][CONF_PORT] == WALLBOX_TLS_PORT
    assert result["context"]["unique_id"] == WALLBOX_SERIAL


async def test_a_wallbox_at_a_new_address_is_followed(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=WALLBOX_SERIAL,
        data={
            CONF_HOST: "192.168.1.99",
            CONF_PORT: WALLBOX_TLS_PORT,
            CONF_UNIT_ID: 248,
            CONF_KIND: KIND_WALLBOX,
        },
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        result = await _discover(hass, _wallbox())
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == WALLBOX_HOST


async def test_a_wallbox_that_does_not_answer_is_not_added(hass: HomeAssistant) -> None:
    result = await _discover(hass, _wallbox())
    with patch(f"{FLOW}._async_probe_wallbox", AsyncMock(return_value=None)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_identified"
