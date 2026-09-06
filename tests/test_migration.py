"""Taking over the YAML package's entity ids, end to end.

`tests/test_recorder_migration.py` establishes what the recorder does with a
bare registry. This asserts that the integration actually does it: that a
config entry set up in migrate mode produces entities on the YAML package's
ids, that one set up in new mode does not, and that the traps around both are
handled rather than hoped about.

The important property, and the one worth stating outright: a migrated entity
is not a degraded one. It carries the same device-scoped name, translation
key, device class and diagnostic category as any other. Only the id is
inherited.
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
    do_adhoc_statistics,
    get_start_time,
    statistics_during_period,
)
from pytest_homeassistant_custom_component.typing import RecorderInstanceContextManager
from sqlalchemy import select

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    ENTITY_IDS_NEW,
)
from custom_components.sungrow_modbus.migration import (
    async_legacy_ids_known,
    async_legacy_ids_live,
    legacy_entity_ids,
)
from homeassistant.components.recorder import Recorder, history
from homeassistant.components.recorder.db_schema import StatesMeta
from homeassistant.components.recorder.util import session_scope
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from .conftest import SERIAL

#: One of the YAML package's cumulative meters — the hardest case, because the
#: Energy dashboard reads its long-term statistics.
LEGACY_ID = "sensor.total_pv_generation"
MODERN_ID = "sensor.sh10rt_total_pv_generation"

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


def _register_yaml_package(entity_registry: er.EntityRegistry) -> None:
    """Register the YAML package's entity the way the modbus platform does."""
    entry = entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )
    assert entry.entity_id == LEGACY_ID


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, entity_ids: str
) -> MockConfigEntry:
    """Set up a config entry in one of the two id styles."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_ENTITY_IDS: entity_ids},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit",
        return_value=unit,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity_id(registry: er.EntityRegistry, key: str) -> str | None:
    return registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_{key}")


async def test_migrate_mode_claims_the_legacy_id(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The entity comes up on the id the YAML package used."""
    _register_yaml_package(entity_registry)

    entry = await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert entry.state is ConfigEntryState.LOADED
    assert _entity_id(entity_registry, "total_pv_generation") == LEGACY_ID


async def test_new_mode_leaves_the_legacy_id_alone(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """New mode is device-scoped and does not touch the YAML package's entry."""
    _register_yaml_package(entity_registry)

    await _setup(hass, sungrow_unit, ENTITY_IDS_NEW)

    assert _entity_id(entity_registry, "total_pv_generation") == MODERN_ID
    # The YAML package's registry entry is untouched, so its history stays
    # reachable under the id it was always on.
    assert entity_registry.async_get(LEGACY_ID).platform == "modbus"


async def test_a_migrated_entity_is_not_a_degraded_one(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Only the id is inherited; everything else is the modern entity.

    This is the difference between a migration and a compatibility mode. A
    migrated installation gets translated names, device classes and diagnostic
    categories exactly like a fresh one, so there is only ever one set of
    behaviour to maintain.
    """
    _register_yaml_package(entity_registry)
    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    entry = entity_registry.async_get(LEGACY_ID)
    assert entry.platform == DOMAIN
    assert entry.has_entity_name is True
    assert entry.translation_key == "total_pv_generation"
    assert entry.device_id is not None

    diagnostic = entity_registry.async_get(
        _entity_id(entity_registry, "running_state_raw")
    )
    assert diagnostic.entity_category is er.EntityCategory.DIAGNOSTIC


async def test_a_live_legacy_entity_is_detected_rather_than_suffixed(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The `_2` trap, made visible.

    An id is handed out only if it is free in the registry *and* in the state
    machine. With the YAML package still loaded the registry would silently
    hand out `sensor.total_pv_generation_2`, so the config flow refuses the
    choice instead — and this is the check it refuses on.
    """
    _register_yaml_package(entity_registry)
    assert async_legacy_ids_live(hass) == set()

    hass.states.async_set(LEGACY_ID, "1234.5")
    await hass.async_block_till_done()

    assert LEGACY_ID in async_legacy_ids_live(hass)


async def test_our_own_entities_do_not_read_as_a_yaml_package(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """After migrating, a reload must not see its own ids as something to adopt."""
    _register_yaml_package(entity_registry)
    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    # The ids are now ours, so there is nothing left to take over -- otherwise
    # a second inverter would be offered a migration that cannot happen.
    assert async_legacy_ids_known(hass) == set()


async def test_every_legacy_id_matches_the_generated_map() -> None:
    """The ids derived at runtime are the ids the YAML package really made.

    Derived by slugifying `legacy_name` rather than read from a table, so this
    is what stops the two drifting apart.
    """
    import json
    from pathlib import Path

    mapped = {
        entity["entity_id"]
        for entity in json.loads(
            (
                Path(__file__).resolve().parent.parent
                / "doc"
                / "legacy_entity_map.json"
            ).read_text(encoding="utf-8")
        )["entities"]
    }
    assert legacy_entity_ids() <= mapped


# -- the claim that matters: history really continues ----------------------

#: Mirrors the YAML package's `total_pv_generation`: a cumulative kWh meter,
#: which is the hardest case because the Energy dashboard reads its long-term
#: statistics rather than its raw states.
METER_ATTRS = {
    "device_class": SensorDeviceClass.ENERGY,
    "state_class": SensorStateClass.TOTAL_INCREASING,
    "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
}


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


@pytest.fixture
async def recorder(hass: HomeAssistant, recorder_mock: Recorder) -> None:
    """Set up the recorder and the sensor platform that compiles statistics."""
    await async_setup_component(hass, "sensor", {})
    await async_recorder_block_till_done(hass)


async def test_migrating_continues_the_recorded_history(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Years of YAML history, then the integration, on one unbroken series.

    This is the whole point of the feature, so it is asserted against a real
    recorder rather than inferred from the registry: one `states_meta` row,
    the old readings still queryable, the integration's own first reading
    appended to them, and the long-term statistics still there afterwards.

    The inverter is seeded to report 1003.0 kWh so that its reading continues
    the meter the YAML package left at 1002.0 — which is what a real handover
    looks like, and what makes the statistics assertion meaningful.
    """
    start = get_start_time(dt_util.utcnow())
    # 1003.0 kWh at scale 0.1, low word first, as the inverter sends it.
    sungrow_unit.input[13002] = [10030 & 0xFFFF, 10030 >> 16]

    with freeze_time(start) as freezer:
        # What the YAML package recorded before anybody had heard of this
        # integration.
        _register_yaml_package(entity_registry)
        for minute, reading in enumerate([1000.0, 1001.0, 1002.0]):
            freezer.move_to(start + timedelta(minutes=minute))
            hass.states.async_set(LEGACY_ID, str(reading), METER_ATTRS)
            await hass.async_block_till_done()
        await async_wait_recording_done(hass)
        do_adhoc_statistics(hass, start=start)
        await async_wait_recording_done(hass)

        before = statistics_during_period(hass, start, period="5minute")[LEGACY_ID]

        # The user removes the YAML package and restarts: the entity stops
        # existing, but its recorded rows and its orphaned registry entry both
        # remain. That is the state a real migration starts from.
        hass.states.async_remove(LEGACY_ID)
        await async_wait_recording_done(hass)

        freezer.move_to(start + timedelta(minutes=5))
        await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)
        assert _entity_id(entity_registry, "total_pv_generation") == LEGACY_ID
        await async_wait_recording_done(hass)

    # One row, not two: the integration writes where the YAML package wrote.
    with session_scope(hass=hass, read_only=True) as session:
        meta = {row.entity_id for row in session.execute(select(StatesMeta)).scalars()}
    assert LEGACY_ID in meta
    assert f"{LEGACY_ID}_2" not in meta

    # The old readings are still there, then the single empty seam the removal
    # wrote, then the integration's own first reading on the same series.
    recorded = [
        state.state
        for state in history.get_significant_states(
            hass, start - timedelta.resolution, None, [LEGACY_ID]
        ).get(LEGACY_ID, [])
    ]
    assert recorded == ["1000.0", "1001.0", "1002.0", "", "1003.0"]

    # And the Energy dashboard's view: the statistics compiled from the YAML
    # package's years are still attached to this id, not orphaned under an
    # old one.
    after = statistics_during_period(hass, start, period="5minute")[LEGACY_ID]
    assert [row["sum"] for row in after] == [row["sum"] for row in before]
    assert [row["state"] for row in before] == [pytest.approx(1002.0)]
