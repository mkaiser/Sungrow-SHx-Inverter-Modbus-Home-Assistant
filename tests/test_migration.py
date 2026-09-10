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
    async_legacy_ids_with_history,
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


async def test_another_integrations_entity_is_not_mistaken_for_ours(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The id alone cannot identify a YAML entity, and must not be used to.

    69 of the 127 legacy ids carry nothing Sungrow-specific --
    `sensor.battery_level`, `sensor.grid_frequency`,
    `binary_sensor.battery_charging`. Somebody with a BMS integration, or a
    template sensor of their own, plausibly owns one. Matching on the id would
    have counted it as a YAML entity, offered to migrate, and then **deleted
    its registry entry** to take the id.
    """
    stranger = entity_registry.async_get_or_create(
        "sensor",
        "some_battery_integration",
        "bms-pack-1-soc",
        suggested_object_id="battery_level",
    )
    assert stranger.entity_id == "sensor.battery_level"

    # Not ours, so there is nothing to migrate and no question to ask.
    assert async_legacy_ids_known(hass) == set()

    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    # Still theirs, still registered, still under the same platform.
    survivor = entity_registry.async_get("sensor.battery_level")
    assert survivor is not None
    assert survivor.platform == "some_battery_integration"
    assert survivor.unique_id == "bms-pack-1-soc"
    # And ours took a device-scoped id rather than fighting for that one.
    assert _entity_id(entity_registry, "battery_level") == "sensor.sh10rt_battery_level"


async def test_a_renamed_yaml_entity_is_followed_to_where_its_history_is(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Renaming moved the recorder's rows, so the new id is the one to claim.

    Slugifying the YAML's old name would claim `sensor.total_pv_generation`,
    which nothing has written to since the user renamed it -- inheriting an
    empty series and orphaning the real one.
    """
    _register_yaml_package(entity_registry)
    entity_registry.async_update_entity(
        LEGACY_ID, new_entity_id="sensor.pv_total_lifetime"
    )

    assert async_legacy_ids_known(hass) == {"sensor.pv_total_lifetime"}

    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert (
        _entity_id(entity_registry, "total_pv_generation") == "sensor.pv_total_lifetime"
    )


async def test_history_is_found_even_after_the_orphans_were_deleted(
    hass: HomeAssistant,
    recorder: None,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The registry is not the only evidence a YAML package was here.

    doc/cleanup_entities.md has told users for years to delete the orphaned
    entries a removed YAML platform leaves behind, and plenty have. Their
    registry is then clean while the recorder still holds years of rows under
    those ids -- migratable history the registry can no longer point at.
    Without the recorder as a second source, those users are handed
    device-scoped ids and a stranded history, and are never offered the
    choice.
    """
    start = get_start_time(dt_util.utcnow())
    sungrow_unit.input[13002] = [10030 & 0xFFFF, 10030 >> 16]

    with freeze_time(start) as freezer:
        for minute, reading in enumerate([1000.0, 1001.0, 1002.0]):
            freezer.move_to(start + timedelta(minutes=minute))
            hass.states.async_set(LEGACY_ID, str(reading), METER_ATTRS)
            await hass.async_block_till_done()
        await async_wait_recording_done(hass)
        hass.states.async_remove(LEGACY_ID)
        await async_wait_recording_done(hass)

        # No registry entry was ever created -- this is the state after the
        # user tidied the orphans away.
        assert entity_registry.async_get(LEGACY_ID) is None
        assert async_legacy_ids_known(hass) == set()

        # But the recorder knows, so the offer still stands.
        assert LEGACY_ID in await async_legacy_ids_with_history(hass)

        freezer.move_to(start + timedelta(minutes=5))
        await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)
        await async_wait_recording_done(hass)

    assert _entity_id(entity_registry, "total_pv_generation") == LEGACY_ID
    recorded = [
        state.state
        for state in history.get_significant_states(
            hass, start - timedelta.resolution, None, [LEGACY_ID]
        ).get(LEGACY_ID, [])
    ]
    assert recorded == ["1000.0", "1001.0", "1002.0", "", "1003.0"]


async def test_no_recorder_means_nothing_to_find_rather_than_an_error(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """No recorder is legitimate: no recorder, no history to preserve."""
    assert "recorder" not in hass.config.components
    assert await async_legacy_ids_with_history(hass) == set()


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


async def test_a_number_claims_the_yaml_numbers_id_not_the_sensors(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The YAML had two entities per setting, and both have history.

    `sensor.battery_min_soc` read the register and `number.battery_min_soc`
    wrote it, under different platforms and different unique_ids. A migration
    has to claim both, from the right one each time -- claiming the sensor's
    id for the number would put the setting where the readings are.
    """
    sensor = entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "uid_sg_battery_min_soc",
        suggested_object_id="battery_min_soc",
    )
    number = entity_registry.async_get_or_create(
        "number",
        "template",
        "uid_battery_min_soc",
        suggested_object_id="battery_min_soc",
    )
    assert sensor.entity_id == "sensor.battery_min_soc"
    assert number.entity_id == "number.battery_min_soc"

    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    registry = entity_registry
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_battery_min_soc")
        == "sensor.battery_min_soc"
    )
    assert (
        registry.async_get_entity_id("number", DOMAIN, f"{SERIAL}_battery_min_soc")
        == "number.battery_min_soc"
    )


async def test_the_filter_platforms_entity_is_found_and_claimed(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """The one YAML entity registered by neither `modbus` nor `template`.

    `sensor.daily_consumed_energy_filtered` comes from the `filter` platform,
    so the migration only finds it if it looks it up under that platform.
    Every other entity is `modbus` or `template`, which is exactly why a
    third one is worth a test of its own: the lookup would come back None,
    the id would be left alone, and the entity would silently arrive as
    `sensor.sh10rt_daily_consumed_energy_filtered` with none of the history.
    """
    entry = entity_registry.async_get_or_create(
        "sensor",
        "filter",
        "sg_daily_consumed_energy_filtered",
        suggested_object_id="daily_consumed_energy_filtered",
    )
    assert entry.entity_id == "sensor.daily_consumed_energy_filtered"

    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    assert (
        _entity_id(entity_registry, "daily_consumed_energy_filtered")
        == "sensor.daily_consumed_energy_filtered"
    )


async def test_a_delayed_flag_claims_its_own_id_not_its_twins(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    """Two entities read one register, and each must keep its own id.

    `binary_sensor.pv_generating` and `binary_sensor.pv_generating_delay` are
    computed from the same bit and differ only in the delay. Keying anything
    by the *field* rather than by the entity would collapse them, and one of
    the pair would lose its id to a `_2` suffix -- which is what happened to
    the sensor/number pairs before the migration was keyed by (platform, key).
    """
    for unique_id, object_id in (
        ("sg_pv_generating", "pv_generating"),
        ("sg_pv_generating_delay", "pv_generating_delay"),
    ):
        created = entity_registry.async_get_or_create(
            "binary_sensor", "template", unique_id, suggested_object_id=object_id
        )
        assert created.entity_id == f"binary_sensor.{object_id}"

    await _setup(hass, sungrow_unit, ENTITY_IDS_MIGRATE)

    def claimed(key: str) -> str | None:
        return entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{SERIAL}_{key}"
        )

    assert claimed("pv_generating") == "binary_sensor.pv_generating"
    assert claimed("pv_generating_delay") == "binary_sensor.pv_generating_delay"
