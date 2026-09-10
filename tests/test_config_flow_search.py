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
    # The flow opens by asking what the entry is for; these
    # tests are about the ordinary one.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_devices"}
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
    # The flow opens by asking what the entry is for; these
    # tests are about the ordinary one.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup_devices"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "search"}
    )
    default = result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK]
    # Whatever the test machine's adapters are, the prefill must be something
    # a sweep will actually accept rather than a /16 the user has to fix --
    # or **empty**, which is the honest answer when the only adapter is a
    # container bridge and there is nothing to detect from. What it must
    # never be is a range that looks usable and is not.
    assert default == "" or default.endswith(("/24", "/23")), default


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
    """And the retry offers a **different** range, not the one that just failed.

    It used to prefill what was tried, on the reasoning that a user is
    usually correcting a typo. After a sweep that completed and found
    nothing, that reasoning does not hold: the one range certainly not worth
    trying again is the one just swept. So it is dropped from the picker and
    listed as already searched instead.
    """
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
    offered = {
        option["value"]
        for option in result["data_schema"].schema[CONF_NETWORK].config["options"]
    }
    assert "192.168.1.0/24" not in offered, "that range just found nothing"
    assert offered, "something else has to be offered, or this is a dead end"
    # And the form says what was covered, so a third attempt is informed.
    assert "192.168.1.0/24" in result["description_placeholders"]["detected"]
    assert "Already searched" in result["description_placeholders"]["detected"]


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
    # The inverter, then the escape hatch. Two things are on the label
    # whatever DNS said. The **route**, because the two ways in do not answer
    # the same registers -- a dongle forwards 1020 of 1510 dumped addresses
    # where a cable forwards 1461. And the **serial**, because it is printed
    # on the unit's case and is the one identifier somebody can walk up to
    # the hardware and check; a model and an address mean nothing on a roof.
    assert labels[0] == (
        "SH10RT at 192.168.1.50 -- the inverter's own LAN port (serial A123456789)"
    )
    assert len(labels) == 2


async def test_a_container_bridge_is_not_offered_as_the_network_to_search(
    hass: HomeAssistant,
) -> None:
    """The case this project's own devcontainer is in, every day.

    Home Assistant in Docker with bridge networking sits on `172.17.0.2/16`
    and reports exactly that. A `/24` around it is `172.17.0.0/24`, which is
    the bridge and never the inverter -- while the inverter stays perfectly
    reachable, because the bridge forwards outbound traffic and follows the
    host's routing. So a search looks like it should work, sweeps 254
    addresses of nothing, and reports the inverter absent.

    Nothing inside the container can discover the right range: the bridge
    hides the host's routing and multicast does not cross it, so mDNS finds
    nothing either. An empty field and a sentence explaining it is therefore
    the honest answer, and a default that looks right is the harmful one.
    """
    with patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [{"address": "172.17.0.2", "network_prefix": 16}],
            }
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        # The flow opens by asking what the entry is for; these
        # tests are about the ordinary one.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    assert result["step_id"] == "search"
    offered = {
        option["value"]
        for option in result["data_schema"].schema[CONF_NETWORK].config["options"]
    }
    assert "172.17.0.0/24" not in offered, (
        "that is the container's own bridge and never the inverter"
    )
    assert "172.17.0.2/24" not in offered
    # Something is still offered, because a dead end is the failure this
    # replaced: the common router defaults are guesses, and a guess somebody
    # can recognise beats a blank CIDR field.
    assert offered
    default = result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK]
    assert default in offered
    # And the form says the range could not be detected, so a suggestion is
    # not mistaken for a finding.
    assert "could not work out" in result["description_placeholders"]["detected"]


async def test_a_real_adapter_is_still_prefilled(hass: HomeAssistant) -> None:
    """The common case must keep working: most instances are on the LAN.

    The exclusion is deliberately narrow -- `172.16.0.0/12` and Podman's
    `10.88.0.0/16` -- rather than every private range, because a great many
    real homes are `192.168.x.x` and plenty are `10.x.x.x`. Excluding those
    would break detection everywhere it currently works.
    """
    with patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [{"address": "192.168.178.35", "network_prefix": 24}],
            }
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        # The flow opens by asking what the entry is for; these
        # tests are about the ordinary one.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    assert result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK] == "192.168.178.0/24"
    assert (
        "almost always the right one"
        in (result["description_placeholders"]["detected"])
    )


async def test_a_lan_adapter_wins_over_a_bridge_on_the_same_host(
    hass: HomeAssistant,
) -> None:
    """A container with both keeps the useful one.

    Host networking, or a second interface, gives Home Assistant a real LAN
    address alongside the bridge. The bridge must not shadow it just by being
    listed first.
    """
    with patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "docker0",
                "enabled": True,
                "ipv4": [{"address": "172.17.0.1", "network_prefix": 16}],
            },
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [{"address": "192.168.1.50", "network_prefix": 24}],
            },
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        # The flow opens by asking what the entry is for; these
        # tests are about the ordinary one.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    assert result["data_schema"]({CONF_PORT: 502})[CONF_NETWORK] == "192.168.1.0/24"


async def test_a_range_is_something_to_pick_and_not_only_to_type(
    hass: HomeAssistant,
) -> None:
    """CIDR is not a thing to ask a user to produce from nothing.

    Somebody whose sweep found nothing, or whose Home Assistant could not
    detect a network at all, is being asked for `192.168.178.0/24` with no
    help. The picker offers the router defaults this project's users actually
    have -- and still accepts anything typed, because no list covers every
    network.
    """
    with patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [{"address": "172.17.0.2", "network_prefix": 16}],
            }
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        # The flow opens by asking what the entry is for; these
        # tests are about the ordinary one.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    selector = result["data_schema"].schema[CONF_NETWORK]
    assert selector.config["custom_value"] is True, (
        "no list covers every network, so typing one must still work"
    )
    labels = [option["label"] for option in selector.config["options"]]
    assert labels, "a container has nothing to detect, so suggestions are all there is"
    # Each option says where it came from, so a guess is not read as a finding.
    assert all("router default" in label or "own network" in label for label in labels)


async def test_the_detected_network_is_offered_first_and_labelled_as_detected(
    hass: HomeAssistant,
) -> None:
    """A real reading outranks a guess, and says which it is."""
    with patch(
        "custom_components.sungrow_modbus.config_flow.network.async_get_adapters",
        return_value=[
            {
                "name": "eth0",
                "enabled": True,
                "ipv4": [{"address": "192.168.50.10", "network_prefix": 24}],
            }
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        # The flow opens by asking what the entry is for; these
        # tests are about the ordinary one.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )

    options = result["data_schema"].schema[CONF_NETWORK].config["options"]
    assert options[0]["value"] == "192.168.50.0/24"
    assert "own network" in options[0]["label"]
    # The common defaults follow it rather than replacing it.
    assert "192.168.178.0/24" in {option["value"] for option in options[1:]}
