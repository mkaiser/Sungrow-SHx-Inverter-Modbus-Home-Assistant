"""Moving an entry between legacy and modern ids, after setup.

The setup flow asks once which ids the entities take. Until the options page
could ask again, changing the answer meant removing the entry and adding it
back -- history survived that, every setting on the page did not.

What the switch must get right is where each series ends up, so these run
against a real recorder: a rename carries the series, a rename into an id the
recorder already knows is refused (`test_recorder_migration.py`), and the
switch has to route around that rather than discover it in the log.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun import freeze_time
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_recorder_block_till_done,
    async_wait_recording_done,
    get_start_time,
)
from pytest_homeassistant_custom_component.typing import RecorderInstanceContextManager
from sqlalchemy import select

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_LEGACY_SLOT,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
    SECTION_ADVANCED,
    SECTION_CONTROL_TEST,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
from homeassistant.components.recorder import Recorder, history
from homeassistant.components.recorder.db_schema import StatesMeta
from homeassistant.components.recorder.util import session_scope
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .conftest import SERIAL

LEGACY_ID = "sensor.total_pv_generation"
MODERN_ID = "sensor.sh10rt_total_pv_generation"
ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}
UNIQUE_ID = f"{SERIAL}_total_pv_generation"


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


@pytest.fixture
async def recorder(hass: HomeAssistant, recorder_mock: Recorder) -> None:
    await async_setup_component(hass, "sensor", {})
    await async_recorder_block_till_done(hass)


@pytest.fixture(autouse=True)
def _unit(sungrow_unit: MockModbusUnit):
    """Every reload in these tests reaches the same mock inverter."""
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        yield


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, entity_ids: str
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_ENTITY_IDS: entity_ids},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _yaml_package_was_here(entity_registry: er.EntityRegistry) -> None:
    """Leave the YAML package's registry row behind, as removing it does."""
    entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )


def _submission(entity_ids: str) -> dict:
    return {
        CONF_ENTITY_IDS: entity_ids,
        SECTION_POLLING: {"realtime": 5, "fast": 10, "medium": 60, "slowest": 600},
        SECTION_PERMISSIONS: {},
        SECTION_EXTERNAL: {},
        SECTION_ADVANCED: {},
        SECTION_SURVEY: {},
        SECTION_CONTROL_TEST: {},
    }


async def _ask(hass: HomeAssistant, entry: MockConfigEntry, entity_ids: str) -> dict:
    """Open the options page and change the id style; return the confirmation."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], _submission(entity_ids)
    )


async def _switch(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MockModbusUnit,
    entity_ids: str,
) -> dict:
    """Change the id style and confirm it."""
    result = await _ask(hass, entry, entity_ids)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    return result


def _meta(hass: HomeAssistant) -> set[str]:
    with session_scope(hass=hass, read_only=True) as session:
        return {row.entity_id for row in session.execute(select(StatesMeta)).scalars()}


def _states(hass: HomeAssistant, start, entity_id: str) -> list[str]:
    return [
        state.state
        for state in history.get_significant_states(
            hass, start - timedelta.resolution, None, [entity_id]
        ).get(entity_id, [])
    ]


def _where(registry: er.EntityRegistry) -> str | None:
    return registry.async_get_entity_id("sensor", DOMAIN, UNIQUE_ID)


async def test_the_page_offers_the_current_style(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"](_submission(ENTITY_IDS_NEW))[CONF_ENTITY_IDS] == (
        ENTITY_IDS_NEW
    )


async def test_leaving_it_alone_moves_nothing(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
    result = await _ask(hass, entry, ENTITY_IDS_NEW)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _where(entity_registry) == MODERN_ID


async def test_modern_to_legacy_carries_the_series_when_the_id_is_unused(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """No YAML history to continue, so the integration's own series moves."""
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
    await async_wait_recording_done(hass)
    assert MODERN_ID in _meta(hass)

    confirm = await _ask(hass, entry, ENTITY_IDS_MIGRATE)
    assert confirm["step_id"] == "entity_ids_legacy"
    assert (
        "move, history and statistics with them"
        in (confirm["description_placeholders"]["changes"])
    )

    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert entry.data[CONF_ENTITY_IDS] == ENTITY_IDS_MIGRATE
    assert _where(entity_registry) == LEGACY_ID
    assert hass.states.get(LEGACY_ID) is not None
    meta = _meta(hass)
    assert LEGACY_ID in meta
    assert MODERN_ID not in meta


async def test_modern_to_legacy_continues_the_yaml_history(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """What somebody who chose "start fresh" and regrets it is after.

    The YAML package's years continue under its id; the weeks recorded under
    the modern id stay there rather than being merged, which the recorder
    cannot do.
    """
    start = get_start_time(dt_util.utcnow())
    sungrow_unit.input[13002] = [10030 & 0xFFFF, 10030 >> 16]
    with freeze_time(start) as freezer:
        for minute, reading in enumerate([1000.0, 1002.0]):
            freezer.move_to(start + timedelta(minutes=minute))
            hass.states.async_set(LEGACY_ID, str(reading))
            await hass.async_block_till_done()
        hass.states.async_remove(LEGACY_ID)
        await async_wait_recording_done(hass)

        freezer.move_to(start + timedelta(minutes=5))
        entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
        await async_wait_recording_done(hass)
        entity_registry.async_update_entity(MODERN_ID, name="PV total")

        confirm = await _ask(hass, entry, ENTITY_IDS_MIGRATE)
        assert (
            "YAML package's history" in confirm["description_placeholders"]["changes"]
        )
        freezer.move_to(start + timedelta(minutes=10))
        await _switch(hass, entry, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert _where(entity_registry) == LEGACY_ID
    # The owner's own name came along with the entity.
    assert entity_registry.async_get(LEGACY_ID).name == "PV total"
    assert _states(hass, start, LEGACY_ID)[:2] == ["1000.0", "1002.0"]
    assert _states(hass, start, LEGACY_ID)[-1] == "1003.0"
    assert MODERN_ID in _meta(hass)


async def test_legacy_to_modern_moves_the_series_and_drops_the_raw_sensors(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    _yaml_package_was_here(entity_registry)
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)
    await async_wait_recording_done(hass)
    assert _where(entity_registry) == LEGACY_ID
    raw = [
        entity_id
        for description in SENSOR_DESCRIPTIONS
        if description.legacy_only
        and (
            entity_id := entity_registry.async_get_entity_id(
                "sensor", DOMAIN, f"{SERIAL}_{description.key}"
            )
        )
    ]
    assert raw

    confirm = await _ask(hass, entry, ENTITY_IDS_NEW)
    assert confirm["step_id"] == "entity_ids_modern"
    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_NEW)

    assert entry.data[CONF_ENTITY_IDS] == ENTITY_IDS_NEW
    assert _where(entity_registry) == MODERN_ID
    meta = _meta(hass)
    assert MODERN_ID in meta
    assert LEGACY_ID not in meta
    for entity_id in raw:
        assert entity_registry.async_get(entity_id) is None


async def test_an_occupied_modern_id_is_archived_not_merged(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Rows already under the modern id are moved aside, then the rename runs.

    Without the archive the recorder refuses the rename and the long series
    is left behind under the legacy id while the entity writes elsewhere.
    """
    start = get_start_time(dt_util.utcnow())
    with freeze_time(start) as freezer:
        hass.states.async_set(MODERN_ID, "7.0")
        await hass.async_block_till_done()
        hass.states.async_remove(MODERN_ID)
        await async_wait_recording_done(hass)

        freezer.move_to(start + timedelta(minutes=5))
        _yaml_package_was_here(entity_registry)
        entry = await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)
        await async_wait_recording_done(hass)

        confirm = await _ask(hass, entry, ENTITY_IDS_NEW)
        assert (
            f"`{MODERN_ID}_archive`" in confirm["description_placeholders"]["changes"]
        )
        await _switch(hass, entry, sungrow_unit, ENTITY_IDS_NEW)

    assert _where(entity_registry) == MODERN_ID
    assert _states(hass, start, f"{MODERN_ID}_archive")[0] == "7.0"
    assert "7.0" not in _states(hass, start, MODERN_ID)
    assert LEGACY_ID not in _meta(hass)


async def test_a_round_trip_returns_everything(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    _yaml_package_was_here(entity_registry)
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)
    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_NEW)
    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert _where(entity_registry) == LEGACY_ID
    meta = _meta(hass)
    assert LEGACY_ID in meta
    assert MODERN_ID not in meta
    assert f"{LEGACY_ID}_2" not in meta


async def test_an_id_the_owner_chose_is_left_alone(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
    entity_registry.async_update_entity(MODERN_ID, new_entity_id="sensor.my_pv")
    await hass.async_block_till_done()

    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert _where(entity_registry) == "sensor.my_pv"


async def test_a_running_yaml_package_refuses_the_move_to_legacy(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Its live entities hold the ids, so the move would hand out `_2`."""
    entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )
    hass.states.async_set(LEGACY_ID, "1000.0")
    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)

    confirm = await _ask(hass, entry, ENTITY_IDS_MIGRATE)
    assert "still running" in confirm["description_placeholders"]["status"]
    result = await hass.config_entries.options.async_configure(confirm["flow_id"], {})

    assert result["errors"] == {"base": "legacy_package_still_loaded"}
    assert entry.data[CONF_ENTITY_IDS] == ENTITY_IDS_NEW
    assert _where(entity_registry) == MODERN_ID


async def test_a_disabled_entity_lands_on_the_target_too(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """A disabled entity's old id is free, and would be handed back.

    It has no state, so nothing holds the id in the state machine, and the
    registry gives a re-created entry its old id whenever it can. The join
    reserves it for that moment.
    """
    hass.states.async_set(LEGACY_ID, "1000.0")
    await hass.async_block_till_done()
    hass.states.async_remove(LEGACY_ID)
    await async_wait_recording_done(hass)

    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)
    entity_registry.async_update_entity(
        MODERN_ID, disabled_by=er.RegistryEntryDisabler.USER
    )
    await hass.async_block_till_done()
    assert hass.states.get(MODERN_ID) is None

    await _switch(hass, entry, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert _where(entity_registry) == LEGACY_ID
    assert entity_registry.async_get(LEGACY_ID).disabled_by is (
        er.RegistryEntryDisabler.USER
    )


async def test_an_undetermined_slot_refuses_the_move_to_legacy(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Refused on the options page itself, before anything is planned.

    A numbered YAML slot existed and this inverter's serial matches none, so
    the legacy ids could be another inverter's history.
    """
    for suffix in ("", "_inv_2"):
        entity_registry.async_get_or_create(
            "sensor",
            "modbus",
            f"sg_total_pv_generation{suffix}",
            suggested_object_id=f"total_pv_generation{suffix}",
        )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_ENTITY_IDS: ENTITY_IDS_NEW, CONF_LEGACY_SLOT: None},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await _ask(hass, entry, ENTITY_IDS_MIGRATE)

    assert result["step_id"] == "init"
    assert result["errors"] == {"base": "legacy_slot_unknown"}
    assert entry.data[CONF_ENTITY_IDS] == ENTITY_IDS_NEW
    assert entry.data[CONF_LEGACY_SLOT] is None
    assert _where(entity_registry) == MODERN_ID
