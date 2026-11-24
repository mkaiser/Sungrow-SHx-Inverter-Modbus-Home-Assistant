"""What a search found and the owner did not pick is offered afterwards.

A flow makes one entry, so the picker takes one device and each of the others
becomes a *Discovered* card of its own, confirmed without searching again.
Held here: one card per inverter **serial** (a cable and a dongle to one
machine are one card, and the picked inverter's other path is none), wallboxes
and unit-247 devices are offered too, nothing already set up is offered, a
card reads nothing until confirmed, and a confirmed card ends where the
picker would have.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.config_flow import NOT_LISTED, SungrowConfigFlow
from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_KIND,
    CONF_TLS,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_IHOMEMANAGER,
    KIND_WALLBOX,
    WALLBOX_TLS_PORT,
)
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .test_config_flow_search import _search

FLOW = "custom_components.sungrow_modbus.config_flow"
SECOND = "A987654321"
WALLBOX_SERIAL = "W123456789"


def _inverter(host: str, serial: str, *, direct: bool) -> dict[str, Any]:
    return {
        CONF_HOST: host,
        CONF_PORT: 502,
        CONF_UNIT_ID: 1,
        "serial": serial,
        "model": "SH10RT",
        "kind": {},
        "hostname": None,
        "direct": direct,
        "battery": None,
        "label": f"SH10RT at {host}",
    }


#: A house with two inverters, the first reached by cable and by dongle, a
#: wallbox at its own address and an iHomeManager.
FOUND = {
    "192.168.1.50": _inverter("192.168.1.50", "A123456789", direct=True),
    "192.168.1.51": _inverter("192.168.1.51", "A123456789", direct=False),
    "192.168.1.52": _inverter("192.168.1.52", SECOND, direct=True),
}
WALLBOXES = {
    "192.168.1.70": {
        CONF_HOST: "192.168.1.70",
        "model": "AC22E-01",
        "serial": WALLBOX_SERIAL,
        "label": "AC22E-01 (wallbox) at 192.168.1.70",
    }
}
UNIT_247 = {
    "192.168.1.80:502": {
        CONF_HOST: "192.168.1.80",
        CONF_PORT: 502,
        CONF_TLS: False,
        CONF_KIND: KIND_IHOMEMANAGER,
        "model": "iHomeManager",
        "label": "iHomeManager at 192.168.1.80, port 502",
    }
}


@pytest.fixture
def no_setup():
    """Stop the created entries from reaching for the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


@pytest.fixture
def house():
    """Have the search find `FOUND`, `WALLBOXES` and `UNIT_247`."""

    async def sweep(self: SungrowConfigFlow) -> None:
        self._found = {host: dict(entry) for host, entry in FOUND.items()}
        self._wallboxes = dict(WALLBOXES)
        self._unit_247 = dict(UNIT_247)

    with patch.object(SungrowConfigFlow, "_async_sweep_and_identify", sweep):
        yield


def _offers(hass: HomeAssistant) -> dict[str, dict]:
    """Return the cards on show, by their unique id."""
    return {
        flow["context"]["unique_id"]: flow
        for flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        if flow["context"]["source"] == SOURCE_INTEGRATION_DISCOVERY
    }


async def _pick(hass: HomeAssistant, host: str) -> dict:
    result = await _search(hass)
    assert result["step_id"] == "pick"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: host}
    )
    await hass.async_block_till_done()
    return result


async def test_every_device_not_picked_is_offered_once(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    await _pick(hass, "192.168.1.50")
    offers = _offers(hass)
    # Not the picked inverter's dongle path: it is the same machine.
    assert set(offers) == {SECOND, WALLBOX_SERIAL, "ihomemanager-192.168.1.80-502"}
    for flow in offers.values():
        assert flow["step_id"] == "offered_confirm"
    assert offers[SECOND]["context"]["title_placeholders"] == {
        "name": "SH10RT at 192.168.1.52"
    }


async def test_picking_a_wallbox_offers_each_inverter_by_its_first_path(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    with patch(f"{FLOW}.async_get_temporary_unit") as connect:
        result = await _pick(hass, "wallbox:192.168.1.70")
    connect.assert_not_called()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    offers = _offers(hass)
    assert set(offers) == {"A123456789", SECOND, "ihomemanager-192.168.1.80-502"}
    flow = hass.config_entries.flow._progress[offers["A123456789"]["flow_id"]]
    # The cable, which `_described` ranks above the dongle.
    assert flow._offered[CONF_HOST] == "192.168.1.50"


async def test_anything_already_set_up_is_not_offered(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=SECOND, data={}).add_to_hass(hass)
    MockConfigEntry(domain=DOMAIN, unique_id=WALLBOX_SERIAL, data={}).add_to_hass(hass)
    await _pick(hass, "192.168.1.50")
    assert set(_offers(hass)) == {"ihomemanager-192.168.1.80-502"}


async def test_a_confirmed_inverter_card_is_named_and_created(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    await _pick(hass, "192.168.1.50")
    flow_id = _offers(hass)[SECOND]["flow_id"]
    result = await hass.config_entries.flow.async_configure(flow_id, {})
    # Two inverters were found, so this one is asked its name too.
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(
        flow_id, {CONF_NAME: "Garage"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garage"
    assert result["data"][CONF_HOST] == "192.168.1.52"
    assert result["data"][CONF_ENTITY_IDS] == "new"
    assert result["context"]["unique_id"] == SECOND
    # A card hands nothing on: the other cards are the ones already there.
    assert set(_offers(hass)) == {WALLBOX_SERIAL, "ihomemanager-192.168.1.80-502"}


async def test_confirmed_wallbox_and_unit_247_cards_create_their_entries(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    await _pick(hass, "192.168.1.50")
    offers = _offers(hass)
    result = await hass.config_entries.flow.async_configure(
        offers[WALLBOX_SERIAL]["flow_id"], {}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == WALLBOX_TLS_PORT
    assert result["data"][CONF_KIND] == KIND_WALLBOX
    result = await hass.config_entries.flow.async_configure(
        offers["ihomemanager-192.168.1.80-502"]["flow_id"], {}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_KIND] == KIND_IHOMEMANAGER
    assert result["data"][CONF_HOST] == "192.168.1.80"


async def test_none_of_these_offers_nothing(
    hass: HomeAssistant, house: None, no_setup: None
) -> None:
    result = await _pick(hass, NOT_LISTED)
    assert _offers(hass) == {}
    assert result["step_id"] == "manual"


@pytest.mark.parametrize(
    ("direct", "wallboxes", "expected"),
    [(False, True, True), (True, True, False), (False, False, False)],
)
async def test_a_wallbox_beside_a_dongle_is_said_to_be_read_on_its_own(
    hass: HomeAssistant, *, direct: bool, wallboxes: bool, expected: bool
) -> None:
    """Only a dongle forwards a wallbox, so only there could both be expected."""

    async def sweep(self: SungrowConfigFlow) -> None:
        self._found = {"192.168.1.51": _inverter("192.168.1.51", SECOND, direct=direct)}
        self._wallboxes = dict(WALLBOXES) if wallboxes else {}
        self._unit_247 = dict(UNIT_247)

    with patch.object(SungrowConfigFlow, "_async_sweep_and_identify", sweep):
        result = await _search(hass)

    note = result["description_placeholders"]["note"]
    assert ("The wallbox has an address of its own" in note) is expected
