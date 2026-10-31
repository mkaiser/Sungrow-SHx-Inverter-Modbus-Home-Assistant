"""Which connection an inverter's entry uses is the owner's choice, and changes.

One inverter is often reachable two ways -- its own LAN port and a WiNet-S --
and somebody who lays a cable wants the entry they already have to use it,
with every entity id and all of their history where they were. The entry
belongs to the inverter (its serial), so it can move; it must never move to
a *different* inverter.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.config_flow import _loses_wallbox
from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_SURVEY_COMMENT,
    CONF_SURVEY_TRANSPORT,
    CONF_UNIT_ID,
    CONF_WALLBOX_HOST,
    DOMAIN,
    MODE_DEVICES,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .test_config_flow_topology import SERIAL_A, SERIAL_B, _house

DONGLE = "192.168.176.28"
CABLE = "192.168.176.34"
OTHER = "192.168.176.32"

#: Serial A at both of its addresses, serial B at a third.
TOPOLOGY = {DONGLE: {1: SERIAL_A}, CABLE: {1: SERIAL_A}, OTHER: {1: SERIAL_B}}


@pytest.fixture(autouse=True)
def _gate_and_setup(devices_mode_offered: None):
    """Open the devices path, and keep a reloaded entry off the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return an inverter set up through its dongle, with testimony about that path."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: DONGLE,
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DEVICES,
        },
        options={CONF_SURVEY_TRANSPORT: "winet_lan", CONF_SURVEY_COMMENT: "kept"},
        unique_id=SERIAL_A,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    return entry


def _address(host: str) -> dict:
    return {CONF_HOST: host, CONF_PORT: 502, CONF_UNIT_ID: 1}


async def test_reconfigure_moves_the_entry_to_a_cable(hass: HomeAssistant) -> None:
    """Same serial at the new address: the entry moves and keeps everything else."""
    entry = _entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    with _house(TOPOLOGY):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _address(CABLE)
        )
    assert result["step_id"] == "move", result
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "connection_moved"
    assert entry.data[CONF_HOST] == CABLE
    assert entry.data[CONF_MODE] == MODE_DEVICES
    assert entry.unique_id == SERIAL_A
    # The testimony about the old path goes; everything else stays.
    assert CONF_SURVEY_TRANSPORT not in entry.options
    assert entry.options[CONF_SURVEY_COMMENT] == "kept"


async def test_reconfigure_never_moves_to_another_inverter(hass: HomeAssistant) -> None:
    """Another serial there is another machine: abort, and change nothing."""
    entry = _entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    with _house(TOPOLOGY):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _address(OTHER)
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert entry.data[CONF_HOST] == DONGLE


async def test_reconfigure_to_nothing_keeps_the_form_and_the_entry(
    hass: HomeAssistant,
) -> None:
    """An address that does not answer is an error to correct, not a move."""
    entry = _entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    with _house(TOPOLOGY):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _address("192.168.176.99")
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_HOST] == DONGLE


async def test_reconfigure_to_the_same_connection_changes_nothing(
    hass: HomeAssistant,
) -> None:
    entry = _entry(hass)
    result = await entry.start_reconfigure_flow(hass)
    with _house(TOPOLOGY):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], _address(DONGLE)
        )
    assert result["reason"] == "connection_unchanged"


async def _add_by_address(hass: HomeAssistant, host: str) -> dict:
    """Walk Add integration to the address form and submit it."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_devices"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    with _house(TOPOLOGY):
        return await hass.config_entries.flow.async_configure(
            result["flow_id"], _address(host)
        )


async def test_adding_a_configured_inverter_elsewhere_offers_to_move_it(
    hass: HomeAssistant,
) -> None:
    """It used to abort `already_configured`, leaving remove-and-re-add."""
    entry = _entry(hass)
    result = await _add_by_address(hass, CABLE)
    assert result["step_id"] == "move", result
    assert DONGLE in result["description_placeholders"]["old"]
    assert CABLE in result["description_placeholders"]["new"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert result["reason"] == "connection_moved"
    assert entry.data[CONF_HOST] == CABLE
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_adding_it_at_the_same_connection_is_still_already_configured(
    hass: HomeAssistant,
) -> None:
    _entry(hass)
    result = await _add_by_address(hass, DONGLE)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


def test_a_wallbox_read_through_the_dongle_is_warned_about_before_a_cable() -> None:
    """Only a direct path loses it, and only without its own address set."""
    with_wallbox = SimpleNamespace(
        options={}, runtime_data=SimpleNamespace(wallbox=object())
    )
    own_address = SimpleNamespace(
        options={CONF_WALLBOX_HOST: "192.168.176.23"},
        runtime_data=SimpleNamespace(wallbox=object()),
    )
    without = SimpleNamespace(options={}, runtime_data=SimpleNamespace(wallbox=None))

    assert _loses_wallbox(with_wallbox, direct=True)
    assert not _loses_wallbox(with_wallbox, direct=False)
    assert not _loses_wallbox(with_wallbox, direct=None)
    assert not _loses_wallbox(own_address, direct=True)
    assert not _loses_wallbox(without, direct=True)


async def test_the_address_form_has_every_placeholder_on_first_showing(
    hass: HomeAssistant,
) -> None:
    """A placeholder missing from the first showing reads as a formatjs error.

    The frontend renders `Translation [formatjs Error: MISSING_VALUE]` in
    place of the whole description, which is what a user saw on the address
    form until `error` was passed before any error had happened.
    """
    import json
    from pathlib import Path
    import re

    import custom_components.sungrow_modbus as component

    strings = json.loads((Path(component.__file__).parent / "strings.json").read_text())
    wanted = set(
        re.findall(r"{(\w+)}", strings["config"]["step"]["manual"]["description"])
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_diagnostics"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["step_id"] == "manual"
    assert wanted <= set(result["description_placeholders"] or {})
