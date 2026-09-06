"""Searching the network instead of asking the user for an IP address.

The first question this flow used to open with — what is the inverter's IP
address — is one many users cannot answer without going to look at their
router. So it offers to look instead.

The property worth defending is the negative one: **an open Modbus port is not
an inverter.** A sweep of the maintainer's own LAN found a RAKwireless gateway
listening on 502 that echoes whatever it is sent. Offering that as a candidate
would be worse than not searching at all, so nothing reaches the picker until
it has answered a read of its device type register.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest

from custom_components.sungrow_modbus.config_flow import NOT_LISTED
from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_NETWORK,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import SERIAL

SEARCH_INPUT = {CONF_NETWORK: "192.168.1.0/24", CONF_PORT: 502}


@pytest.fixture
def no_setup():
    """Stop the created entry from reaching for the network."""
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        yield


def _probe(sungrow_unit: MockModbusUnit, only: set[str] | None = None):
    """Answer the identity probe for `only` hosts, and fail for the rest."""

    class _Unit:
        async def __aenter__(self) -> MockModbusUnit:
            return sungrow_unit

        async def __aexit__(self, *args: object) -> None:
            return None

    def temporary_unit(hass, params, unit_id):
        if only is not None and params.host not in only:
            raise ModbusError("not a Sungrow inverter")
        return _Unit()

    return patch(
        "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
        side_effect=temporary_unit,
    )


async def _search(hass: HomeAssistant, user_input: dict | None = None) -> dict:
    """Open the flow, choose Search, and submit the range."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"search", "manual"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "search"}
    )
    assert result["step_id"] == "search"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input or SEARCH_INPUT
    )


async def test_the_range_is_prefilled_with_the_network_home_assistant_is_on(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "search"}
    )
    default = result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK]
    # Whatever the test machine's adapters are, the prefill must be something
    # a sweep will actually accept rather than a /16 the user has to fix.
    assert default.endswith("/24") or default.endswith("/23")


async def test_an_inverter_that_answers_is_offered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, no_setup: None
) -> None:
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.1.50"],
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value="inverter.fritz.box",
        ),
        _probe(sungrow_unit),
    ):
        result = await _search(hass)

        assert result["step_id"] == "pick"
        assert result["description_placeholders"]["count"] == "1"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: "192.168.1.50"}
        )

    # And done. No migration question, because this instance has no YAML
    # package to migrate from -- so a new user reaches a configured inverter
    # in three clicks and never types an address.
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENTITY_IDS] == "new"
    assert result["title"] == "SH10RT"
    assert result["data"][CONF_HOST] == "192.168.1.50"
    assert result["data"][CONF_PORT] == 502
    assert result["data"][CONF_UNIT_ID] == 1
    assert result["context"]["unique_id"] == SERIAL


async def test_an_open_port_that_is_not_an_inverter_is_not_offered(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The RAKwireless case: listening on 502, and not a Sungrow."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.1.36", "192.168.1.50"],
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _probe(sungrow_unit, only={"192.168.1.50"}),
    ):
        result = await _search(hass)

    assert result["step_id"] == "pick"
    # One of the two, and it is the one that answered.
    assert result["description_placeholders"]["count"] == "1"
    options = result["data_schema"]({})[CONF_HOST]
    assert options == "192.168.1.50"


async def test_nothing_found_offers_a_way_out_rather_than_an_error(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A dead end has to be actionable.

    An error on a form leaves the user looking at the same fields with nowhere
    to go but the close button -- which is exactly what happened the first
    time this was tried on a real instance. A menu renders as buttons, so the
    step has somewhere to send them.
    """
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.1.36"],
        ),
        _probe(sungrow_unit, only=set()),
    ):
        result = await _search(hass)

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "nothing_found"
    assert set(result["menu_options"]) == {"search", "manual", "start_over"}
    # How many had the port open, so "nothing on the network" and "something
    # is there but would not talk" read differently.
    assert result["description_placeholders"]["candidates"] == "1"
    assert result["description_placeholders"]["scanned"] == "192.168.1.0/24"


async def test_the_dead_end_leads_back_to_the_first_menu(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The thing that was missing: a way back to where you started."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=[],
        ),
        _probe(sungrow_unit, only=set()),
    ):
        result = await _search(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "start_over"}
        )

    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {"search", "manual"}


async def test_the_dead_end_leads_to_entering_an_address(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=[],
        ),
        _probe(sungrow_unit, only=set()),
    ):
        result = await _search(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "manual"}
        )

    assert result["step_id"] == "manual"


async def test_the_search_form_can_be_retried_with_another_range(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """And the retry keeps the range that was tried, to edit rather than retype."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=[],
        ),
        _probe(sungrow_unit, only=set()),
    ):
        result = await _search(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    assert result["step_id"] == "search"
    assert result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK] == "192.168.1.0/24"


async def test_none_of_these_leads_to_entering_an_address(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A found inverter may not be the one you meant -- a neighbour's, say."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.1.50"],
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _probe(sungrow_unit),
    ):
        result = await _search(hass)
        assert result["step_id"] == "pick"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: NOT_LISTED}
        )

    assert result["step_id"] == "manual"


async def test_a_range_too_large_is_refused_before_it_is_swept(
    hass: HomeAssistant,
) -> None:
    """Not after twenty seconds of sweeping: the size is knowable up front."""
    result = await _search(hass, {CONF_NETWORK: "10.0.0.0/8", CONF_PORT: 502})

    assert result["step_id"] == "search"
    assert result["errors"] == {"base": "network_too_large"}
    assert result["description_placeholders"]["hosts"] == "16777214"


async def test_a_nonsense_range_is_reported_on_its_own_field(
    hass: HomeAssistant,
) -> None:
    result = await _search(hass, {CONF_NETWORK: "not a network", CONF_PORT: 502})

    assert result["step_id"] == "search"
    assert result["errors"] == {CONF_NETWORK: "invalid_network"}


async def test_the_label_falls_back_to_the_address_without_dns(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Reverse DNS is a nicety; a home network may not serve PTR records."""
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_sweep",
            return_value=["192.168.1.50"],
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        _probe(sungrow_unit),
    ):
        result = await _search(hass)

    labels = [
        option["label"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    ]
    # The inverter, then the escape hatch.
    assert labels[0] == "SH10RT at 192.168.1.50"
    assert len(labels) == 2
