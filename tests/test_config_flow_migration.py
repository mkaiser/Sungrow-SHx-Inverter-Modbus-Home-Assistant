"""The setup question: migrate the existing entities, or create new ones.

A user with years of `modbus_sungrow.yaml` history and a user installing this
for the first time need different things, and only the first has a decision to
make. So the question is asked when there is something to migrate and skipped
when there is not — a newcomer is never shown a choice about a package they
have never heard of.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL

USER_INPUT = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

LEGACY_ID = "sensor.total_pv_generation"


@pytest.fixture
def probe(sungrow_unit: MockModbusUnit):
    """Answer the config flow's probe with the mock inverter."""

    class _Unit:
        async def __aenter__(self) -> MockModbusUnit:
            return sungrow_unit

        async def __aexit__(self, *args: object) -> None:
            return None

    # The entry that the flow creates is set up for real straight afterwards,
    # which would reach for the network. These tests are about the flow, so
    # setup is stubbed rather than mocked out device by device.
    with (
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            return_value=_Unit(),
        ),
        patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True),
    ):
        yield


def _register_yaml_package(entity_registry: er.EntityRegistry) -> None:
    """Register the YAML package's entity the way the modbus platform does."""
    entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )


async def _connect(hass: HomeAssistant) -> dict:
    """Walk the flow through the menu and the manual connection step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    # The flow now opens on a menu: search the network, or say where it is.
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    assert result["step_id"] == "manual"
    return await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)


async def test_a_newcomer_is_not_asked_about_migrating(
    hass: HomeAssistant, probe: None
) -> None:
    """No YAML package, no question, no mention of one."""
    result = await _connect(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENTITY_IDS] == ENTITY_IDS_NEW


async def test_an_existing_user_is_asked(
    hass: HomeAssistant, probe: None, entity_registry: er.EntityRegistry
) -> None:
    """With entities to take over, the choice is put to the user."""
    _register_yaml_package(entity_registry)

    result = await _connect(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "entity_ids"
    # The description says how many and gives one by name, so the user can see
    # what is actually at stake rather than a generic warning.
    assert result["description_placeholders"]["count"] == "1"
    assert result["description_placeholders"]["example"] == LEGACY_ID

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_MIGRATE}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENTITY_IDS] == ENTITY_IDS_MIGRATE
    assert result["data"][CONF_HOST] == USER_INPUT[CONF_HOST]
    assert result["context"]["unique_id"] == SERIAL


async def test_choosing_new_entities_is_offered_the_same_way(
    hass: HomeAssistant, probe: None, entity_registry: er.EntityRegistry
) -> None:
    """The other answer is a real answer, not a fallback."""
    _register_yaml_package(entity_registry)

    result = await _connect(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_NEW}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ENTITY_IDS] == ENTITY_IDS_NEW


async def test_the_dialog_says_whether_the_package_is_still_running(
    hass: HomeAssistant, probe: None, entity_registry: er.EntityRegistry
) -> None:
    """Checked and stated, not warned about.

    The requirement was in the dialog text from the start and still caught
    people out: a sentence about what you ought to have done reads very
    differently from a line saying what is true right now. So the step looks,
    and reports what it found.
    """
    _register_yaml_package(entity_registry)

    result = await _connect(hass)
    assert "not running" in result["description_placeholders"]["status"]
    # And the answer that works is the one pre-selected.
    assert result["data_schema"]({})[CONF_ENTITY_IDS] == ENTITY_IDS_MIGRATE


async def test_a_running_package_is_reported_before_the_choice_is_made(
    hass: HomeAssistant, probe: None, entity_registry: er.EntityRegistry
) -> None:
    _register_yaml_package(entity_registry)
    hass.states.async_set(LEGACY_ID, "1234.5")

    result = await _connect(hass)

    status = result["description_placeholders"]["status"]
    assert "still running" in status
    # How many are holding ids, so it is a fact about this instance rather
    # than a general caution.
    assert "1 of its entities" in status
    # Migrating cannot work, so it is not what the form offers by default.
    assert result["data_schema"]({})[CONF_ENTITY_IDS] == ENTITY_IDS_NEW


async def test_migrating_is_refused_while_the_yaml_package_is_loaded(
    hass: HomeAssistant, probe: None, entity_registry: er.EntityRegistry
) -> None:
    """The `_2` trap, turned into something the user can act on.

    A live legacy entity holds its id, so adoption would quietly produce
    `sensor.total_pv_generation_2` and orphan the history it was supposed to
    inherit. The flow says so instead, and stays on the step.
    """
    _register_yaml_package(entity_registry)
    hass.states.async_set(LEGACY_ID, "1234.5")

    result = await _connect(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_MIGRATE}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "legacy_package_still_loaded"}

    # Choosing new entities is still possible: nothing is being taken over,
    # so a loaded YAML package is not in the way.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_NEW}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
