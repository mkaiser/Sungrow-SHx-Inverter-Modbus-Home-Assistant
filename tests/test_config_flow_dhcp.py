"""What DHCP shows Home Assistant: a Sungrow port, offered; a RAK module, linked.

A Sungrow network port (MAC prefix `AC:19:9F`, Sungrow's one in the IEEE
registry) announces nothing over mDNS, so a DHCP sighting is the only way Home
Assistant notices one by itself. Held here as for zeroconf: the sighting only
decides whether to **offer**, nothing is read over Modbus until the owner
confirms, anything already set up is left alone. A RAK WiFi module is no
Modbus device; the owner says which inverter it is plugged into, and that
inverter's device page then links the module's web page. The MACs are made up
but for their vendor prefixes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wifi_module
from custom_components.sungrow_modbus.const import (
    CONF_KIND,
    CONF_UNIT_ID,
    CONF_WIFI_MODULE,
    DOMAIN,
    KIND_WALLBOX,
)
from custom_components.sungrow_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.config_entries import SOURCE_DHCP, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .conftest import SERIAL
from .test_config_flow_search import _probe
from .test_config_flow_zeroconf import DONGLE_HOST, _dongle
from .test_init import ENTRY_DATA

PORT_HOST = "192.168.1.61"
MODULE_HOST = "192.168.1.62"
SUNGROW_MAC = "ac199f000001"
RAK_MAC = "ac1f09000002"
RAK_NAME = "rakmodule-000002"
FLOW = "custom_components.sungrow_modbus.config_flow"


def _port(host: str = PORT_HOST) -> DhcpServiceInfo:
    return DhcpServiceInfo(ip=host, hostname="", macaddress=SUNGROW_MAC)


def _module(host: str = MODULE_HOST) -> DhcpServiceInfo:
    return DhcpServiceInfo(ip=host, hostname=RAK_NAME, macaddress=RAK_MAC)


async def _discover(hass: HomeAssistant, info: DhcpServiceInfo) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_DHCP}, data=info
    )


def _inverter(hass: HomeAssistant, **data: object) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SERIAL,
        title="SH10RT",
        data={CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: 1, **data},
    )
    entry.add_to_hass(hass)
    return entry


def test_the_manifest_matches_sungrows_prefix_and_the_rak_module() -> None:
    manifest = json.loads(
        (
            Path(__file__).parent.parent
            / "custom_components"
            / "sungrow_modbus"
            / "manifest.json"
        ).read_text()
    )
    assert manifest["dhcp"] == [
        {"macaddress": wifi_module.SUNGROW_MAC_PREFIX + "*"},
        {"hostname": wifi_module.RAK_HOSTNAME_PREFIX + "*"},
    ]


async def test_a_sungrow_port_is_offered_without_a_modbus_read(
    hass: HomeAssistant,
) -> None:
    with patch(f"{FLOW}.async_get_temporary_unit") as connect:
        result = await _discover(hass, _port())
    connect.assert_not_called()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "dhcp_confirm"
    assert result["description_placeholders"] == {"host": PORT_HOST}


async def test_confirming_identifies_over_modbus_and_creates_the_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    result = await _discover(hass, _port())
    with (
        _probe(sungrow_unit),
        patch(f"{FLOW}.async_hostname", return_value=None),
        patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == PORT_HOST
    # The serial replaces the sighting's stand-in once Modbus has answered.
    assert result["context"]["unique_id"] == SERIAL


async def test_a_port_that_does_not_answer_is_not_added(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    result = await _discover(hass, _port())
    with _probe(sungrow_unit, only=set()):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_identified"


async def test_an_address_already_set_up_is_left_alone(hass: HomeAssistant) -> None:
    _inverter(hass)
    result = await _discover(hass, _port("192.168.1.50"))
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_another_vendor_is_not_offered(hass: HomeAssistant) -> None:
    info = DhcpServiceInfo(ip=PORT_HOST, hostname="printer", macaddress="f8a26d0000ff")
    result = await _discover(hass, info)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_one_device_seen_both_ways_is_offered_once(hass: HomeAssistant) -> None:
    """The mDNS record names the inverter; it takes over the DHCP offer."""
    first = await _discover(hass, _port(DONGLE_HOST))
    assert first["step_id"] == "dhcp_confirm"
    await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_ZEROCONF}, data=_dongle()
    )
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_ZEROCONF]
    again = await _discover(hass, _port(DONGLE_HOST))
    assert again["reason"] == "already_in_progress"


async def test_a_rak_module_with_no_inverter_set_up_is_not_offered(
    hass: HomeAssistant,
) -> None:
    result = await _discover(hass, _module())
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wifi_module_no_inverter"


async def test_a_rak_module_is_linked_to_the_inverter_the_owner_picks(
    hass: HomeAssistant,
) -> None:
    entry = _inverter(hass)
    _inverter_wallbox = MockConfigEntry(
        domain=DOMAIN,
        unique_id="W123456789",
        title="AC22E-01",
        data={CONF_HOST: "192.168.1.70", CONF_KIND: KIND_WALLBOX},
    )
    _inverter_wallbox.add_to_hass(hass)
    with patch(f"{FLOW}.async_get_temporary_unit") as connect:
        result = await _discover(hass, _module())
    connect.assert_not_called()
    assert result["step_id"] == "wifi_module"
    assert result["description_placeholders"] == {
        "host": MODULE_HOST,
        "hostname": RAK_NAME,
        "url": f"http://{MODULE_HOST}/",
    }
    # Only inverters to choose from, never the wallbox.
    options = result["data_schema"].schema["inverter"].config["options"]
    assert [option["label"] for option in options] == ["SH10RT"]
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"inverter": entry.entry_id}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wifi_module_linked"
    assert entry.data[CONF_WIFI_MODULE] == {
        CONF_HOST: MODULE_HOST,
        "mac": "ac:1f:09:00:00:02",
        "hostname": RAK_NAME,
    }


async def test_a_linked_module_at_a_new_address_is_followed(
    hass: HomeAssistant,
) -> None:
    entry = _inverter(
        hass,
        **{
            CONF_WIFI_MODULE: {
                CONF_HOST: "192.168.1.99",
                "mac": "ac:1f:09:00:00:02",
                "hostname": RAK_NAME,
            }
        },
    )
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        result = await _discover(hass, _module())
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_WIFI_MODULE][CONF_HOST] == MODULE_HOST


async def test_the_linked_module_shows_under_the_inverter_with_its_page(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    module = {CONF_HOST: MODULE_HOST, "mac": "ac:1f:09:00:00:02", "hostname": RAK_NAME}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SERIAL,
        title="SH10RT",
        data={**ENTRY_DATA, CONF_WIFI_MODULE: module},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    registry = dr.async_get(hass)
    inverter = registry.async_get_device_by_identifier((DOMAIN, SERIAL), entry.entry_id)
    device = registry.async_get_device_by_identifier(
        (DOMAIN, "wifi_module_AC1F09000002"), entry.entry_id
    )
    assert inverter is not None and device is not None
    assert device.configuration_url == f"http://{MODULE_HOST}/"
    assert device.via_device_id == inverter.id
    assert device.manufacturer == "RAKwireless"
    # The inverter's own link stays the WiNet-S's, and there is none here.
    assert inverter.configuration_url is None

    report = await async_get_config_entry_diagnostics(hass, entry)
    assert report["wifi_module"] == {
        "hostname_prefix": "rakmodule-",
        "mac_vendor_prefix": "AC:1F:09",
        "web_page": "http://**REDACTED**/",
    }
    assert MODULE_HOST not in json.dumps(report)


def test_the_rules() -> None:
    assert wifi_module.is_sungrow_mac("AC:19:9F:12:34:56")
    assert wifi_module.is_sungrow_mac("ac199f123456")
    assert not wifi_module.is_sungrow_mac("ac1f09123456")
    assert wifi_module.is_rak_module("rakmodule-01D066")
    assert wifi_module.is_rak_module("RAKmodule-01d066")
    assert not wifi_module.is_rak_module(None)
    assert not wifi_module.is_rak_module("rak-gateway")


async def test_deleting_the_module_device_unlinks_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The owner's link, so the owner's to undo: the device stays gone."""
    module = {CONF_HOST: MODULE_HOST, "mac": "ac:1f:09:00:00:02", "hostname": RAK_NAME}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SERIAL,
        title="SH10RT",
        data={**ENTRY_DATA, CONF_WIFI_MODULE: module},
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = dr.async_get(hass)
        device = registry.async_get_device_by_identifier(
            (DOMAIN, "wifi_module_AC1F09000002"), entry.entry_id
        )
        assert device is not None
        inverter = registry.async_get_device_by_identifier(
            (DOMAIN, SERIAL), entry.entry_id
        )
        assert inverter is not None
        # The inverter itself refuses: the next poll would recreate it.
        from custom_components.sungrow_modbus import async_remove_config_entry_device

        assert not await async_remove_config_entry_device(hass, entry, inverter)
        assert await async_remove_config_entry_device(hass, entry, device)
        registry.async_remove_device(device.id)
        await hass.async_block_till_done()
    assert CONF_WIFI_MODULE not in entry.data
    assert (
        registry.async_get_device_by_identifier(
            (DOMAIN, "wifi_module_AC1F09000002"), entry.entry_id
        )
        is None
    )


async def test_linking_a_loaded_inverter_shows_the_module_at_once(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """No reload: the module's device appears under the running inverter."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=SERIAL, title="SH10RT", data=ENTRY_DATA
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        result = await _discover(hass, _module())
        with patch("homeassistant.config_entries.ConfigEntries.async_reload") as reload:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"inverter": entry.entry_id}
            )
            await hass.async_block_till_done()
        reload.assert_not_called()
    assert result["reason"] == "wifi_module_linked"
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "wifi_module_AC1F09000002"), entry.entry_id
    )
    assert device is not None
    assert device.configuration_url == f"http://{MODULE_HOST}/"
