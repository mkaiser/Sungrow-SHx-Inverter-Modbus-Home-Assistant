"""Promoting a diagnostics entry to a full one, from the options page.

The one place a diagnostics entry is asked the question its setup skipped:
which entity ids years of recorder history continue on. Each branch is a
different answer for a real house, so each is walked here:

* no YAML package was ever here -- promoted on new ids, nothing asked;
* its rows are in the registry -- asked, and taking them over is stored;
* it is still running -- taking over is refused, because its live entities
  hold the ids and adoption would quietly append `_2`;
* its slot cannot be determined -- said so, and promoted on new ids, since
  a guessed slot could hand this inverter another one's history.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_recorder_block_till_done,
)
from pytest_homeassistant_custom_component.typing import RecorderInstanceContextManager

from custom_components.sungrow_modbus.const import (
    CONF_ADD_DEVICES,
    CONF_ENTITY_IDS,
    CONF_INTERVALS,
    CONF_LEGACY_SLOT,
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    SECTION_ADVANCED,
    SECTION_CONTROL_TEST,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import SERIAL

LEGACY_ID = "sensor.total_pv_generation"
ENTRY_DATA = {
    CONF_HOST: "127.0.0.1",
    CONF_PORT: 5020,
    CONF_UNIT_ID: 1,
    CONF_MODE: MODE_DIAGNOSTICS,
}
INTERVALS = {"realtime": 7, "fast": 10, "medium": 60, "slowest": 600}


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


@pytest.fixture(autouse=True)
async def recorder(
    hass: HomeAssistant, recorder_mock: Recorder, devices_mode_offered: None
) -> None:
    await async_setup_component(hass, "sensor", {})
    await async_recorder_block_till_done(hass)


@pytest.fixture(autouse=True)
def _unit(sungrow_unit: MockModbusUnit):
    """Every reload in these tests reaches the same mock inverter."""
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        yield


async def _diagnostics_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _yaml_package_was_here(hass: HomeAssistant) -> None:
    """Leave the YAML package's registry row behind, as removing it does."""
    er.async_get(hass).async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )


async def _promote(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    """Tick "add devices" on the options page, with a changed poll interval."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    return await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ADD_DEVICES: True,
            SECTION_POLLING: INTERVALS,
            SECTION_PERMISSIONS: {},
            SECTION_EXTERNAL: {},
            SECTION_ADVANCED: {},
            SECTION_SURVEY: {},
            SECTION_CONTROL_TEST: {},
        },
    )


def _assert_promoted(entry: MockConfigEntry, entity_ids: str) -> None:
    assert entry.data[CONF_MODE] == MODE_DEVICES
    assert entry.data[CONF_ENTITY_IDS] == entity_ids
    # What was typed beside the checkbox is kept, not lost to the detour.
    assert entry.options[CONF_INTERVALS] == INTERVALS


async def test_a_house_without_the_yaml_package_is_promoted_without_a_question(
    hass: HomeAssistant,
) -> None:
    entry = await _diagnostics_entry(hass)

    result = await _promote(hass, entry)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    _assert_promoted(entry, ENTITY_IDS_NEW)
    assert entry.data[CONF_LEGACY_SLOT] == ""


async def test_the_yaml_package_s_ids_are_offered_and_taken_over(
    hass: HomeAssistant,
) -> None:
    _yaml_package_was_here(hass)
    entry = await _diagnostics_entry(hass)

    result = await _promote(hass, entry)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "promote"
    assert result["description_placeholders"]["example"] == LEGACY_ID

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_MIGRATE}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    _assert_promoted(entry, ENTITY_IDS_MIGRATE)


async def test_taking_over_is_refused_while_the_yaml_package_runs(
    hass: HomeAssistant,
) -> None:
    _yaml_package_was_here(hass)
    hass.states.async_set(LEGACY_ID, "1")
    entry = await _diagnostics_entry(hass)

    result = await _promote(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_MIGRATE}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "legacy_package_still_loaded"}
    assert entry.data[CONF_MODE] == MODE_DIAGNOSTICS

    # Starting fresh is still open.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_ENTITY_IDS: ENTITY_IDS_NEW}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    _assert_promoted(entry, ENTITY_IDS_NEW)


async def test_an_undetermined_slot_is_said_and_promotes_on_new_ids(
    hass: HomeAssistant,
) -> None:
    _yaml_package_was_here(hass)
    entry = await _diagnostics_entry(hass)

    with patch(
        "custom_components.sungrow_modbus.config_flow.async_resolve_legacy_slot",
        return_value=None,
    ):
        result = await _promote(hass, entry)
    assert result["step_id"] == "slot_unknown"

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    _assert_promoted(entry, ENTITY_IDS_NEW)
    # `None`, not `""`: an unanswered slot claims no ids at all.
    assert entry.data[CONF_LEGACY_SLOT] is None
