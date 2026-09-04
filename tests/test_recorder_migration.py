"""What survives when a Sungrow sensor's entity_id changes.

The integration is meant to replace modbus_sungrow.yaml, and both the recorder
and every dashboard card key on ``entity_id``. Whether the integration may
offer modern, device-scoped ids at all therefore depends on what Home
Assistant does to already-recorded data when an id changes -- which is a
question about core's behaviour, not about this integration, so it is settled
here by experiment rather than assumed.

The recorder answers it in
``homeassistant/components/recorder/entity_registry.py``: it listens for
entity registry updates carrying ``old_entity_id`` and renames the
``states_meta`` and ``statistics_meta`` rows, so no state rows are copied and
no data moves. These tests hold that behaviour, and the three ways it goes
wrong, in place:

* A registry rename carries both raw history and long-term statistics.
* A ``total_increasing`` sum keeps climbing across the rename, so the Energy
  dashboard sees neither a reset nor a spike.
* A rename into an entity_id the recorder already knows is **refused**, and
  the two histories stay separate. This is exactly the case a YAML migration
  walks into, because the YAML package's rows are already there.
* The way past that is to claim the legacy entity_id when the entity is
  created, instead of renaming into it afterwards. Then no migration runs at
  all: the integration's states land on the row the YAML package has been
  filling for years.
* Holding the entity_id is necessary but not sufficient. A unit from the same
  unit class is converted and the series continues; a unit from a different
  class is dropped, and long-term statistics then freeze flat instead of
  stopping visibly.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_recorder_block_till_done,
    async_wait_recording_done,
    do_adhoc_statistics,
    get_start_time,
    statistics_during_period,
)
from pytest_homeassistant_custom_component.typing import RecorderInstanceContextManager
from sqlalchemy import select

from homeassistant.components.recorder import Recorder, history
from homeassistant.components.recorder.db_schema import StatesMeta
from homeassistant.components.recorder.util import session_scope
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

#: The entity_id modbus_sungrow.yaml produces: a bare object id, because YAML
#: platform entities are not device-scoped.
LEGACY_ID = "sensor.total_pv_generation"

#: What the integration produces instead with `_attr_has_entity_name = True`
#: and a device named after the model.
MODERN_ID = "sensor.sh10rt_total_pv_generation"

#: Removing an entity records one empty state, so a migrated series carries a
#: single-row seam where the YAML package stopped. Raw history shows it as a
#: brief gap; long-term statistics, which the Energy dashboard reads, do not
#: see it at all.
SEAM = ""

#: Mirrors the `total_pv_generation` entry in modbus_sungrow.yaml: a
#: cumulative kWh meter, which is the hardest case to migrate because the
#: Energy dashboard reads its long-term statistics.
METER_ATTRS = {
    "device_class": SensorDeviceClass.ENERGY,
    "state_class": SensorStateClass.TOTAL_INCREASING,
    "unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
}


def _period_start() -> datetime:
    """Return a UTC 5-minute boundary, which is what statistics compile on."""
    return get_start_time(dt_util.utcnow())


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


@pytest.fixture(autouse=True)
async def setup_sensor_recorder(hass: HomeAssistant, recorder_mock: Recorder) -> None:
    """Set up the recorder and the sensor platform that compiles statistics."""
    await async_setup_component(hass, "sensor", {})
    await async_recorder_block_till_done(hass)


async def _record_meter(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    start: datetime,
    entity_id: str,
    readings: Iterable[float],
    attributes: dict[str, object] | None = None,
) -> None:
    """Write a rising meter reading once a minute from ``start``."""
    for minute, reading in enumerate(readings):
        freezer.move_to(start + timedelta(minutes=minute))
        hass.states.async_set(entity_id, str(reading), attributes or METER_ATTRS)
        await hass.async_block_till_done()
    await async_wait_recording_done(hass)


async def _retire(hass: HomeAssistant, entity_id: str) -> None:
    """Drop an entity from the state machine, keeping its recorded rows.

    This is what a restart after modbus_sungrow.yaml is removed leaves
    behind, and the state the migration actually starts from. It matters
    because the entity registry hands out an entity_id only if it is free in
    the registry *and* in the state machine -- a still-live legacy entity
    gets the integration a `_2` suffix instead of the id it wanted.
    """
    hass.states.async_remove(entity_id)
    await async_wait_recording_done(hass)


def _register_legacy_entity(entity_registry: er.EntityRegistry) -> None:
    """Register the YAML package's entity the way the modbus platform does.

    Every entry in modbus_sungrow.yaml carries a `unique_id`, so they all have
    entity registry entries -- which is what makes a registry-level migration
    possible at all.
    """
    entry = entity_registry.async_get_or_create(
        "sensor",
        "modbus",
        "sg_total_pv_generation",
        suggested_object_id="total_pv_generation",
    )
    assert entry.entity_id == LEGACY_ID


def _states_meta_ids(hass: HomeAssistant) -> set[str]:
    """Return every entity_id the recorder has a states_meta row for."""
    with session_scope(hass=hass, read_only=True) as session:
        return {row.entity_id for row in session.execute(select(StatesMeta)).scalars()}


def _recorded_states(hass: HomeAssistant, start: datetime, entity_id: str) -> list[str]:
    """Return the recorded state values for one entity_id."""
    significant = history.get_significant_states(
        hass, start - timedelta.resolution, None, [entity_id]
    )
    return [state.state for state in significant.get(entity_id, [])]


async def test_registry_rename_carries_raw_history(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Renaming through the registry moves the states_meta row, not the rows."""
    _register_legacy_entity(entity_registry)

    start = _period_start()
    with freeze_time(start) as freezer:
        await _record_meter(hass, freezer, start, LEGACY_ID, [1000.0, 1001.0, 1002.0])

        assert _recorded_states(hass, start, LEGACY_ID) == [
            "1000.0",
            "1001.0",
            "1002.0",
        ]

        entity_registry.async_update_entity(LEGACY_ID, new_entity_id=MODERN_ID)
        await async_wait_recording_done(hass)

    # The history did not move; the name it is filed under did.
    assert _recorded_states(hass, start, MODERN_ID) == ["1000.0", "1001.0", "1002.0"]
    assert _recorded_states(hass, start, LEGACY_ID) == []
    assert LEGACY_ID not in _states_meta_ids(hass)
    assert MODERN_ID in _states_meta_ids(hass)


async def test_registry_rename_carries_long_term_statistics(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """Statistics follow the rename too, which is what the Energy dashboard reads."""
    _register_legacy_entity(entity_registry)

    period0 = _period_start()
    with freeze_time(period0) as freezer:
        await _record_meter(hass, freezer, period0, LEGACY_ID, [1000.0, 1001.0, 1002.0])
        do_adhoc_statistics(hass, start=period0)
        await async_wait_recording_done(hass)

        before = statistics_during_period(hass, period0, period="5minute")
        assert before[LEGACY_ID][0]["sum"] == pytest.approx(2.0)

        entity_registry.async_update_entity(LEGACY_ID, new_entity_id=MODERN_ID)
        await async_wait_recording_done(hass)

    after = statistics_during_period(hass, period0, period="5minute")
    assert LEGACY_ID not in after
    assert after[MODERN_ID] == before[LEGACY_ID]


async def test_total_increasing_sum_keeps_climbing_across_a_rename(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """The sum continues from its high-water mark: no reset, no spike."""
    _register_legacy_entity(entity_registry)

    period0 = _period_start()
    period1 = period0 + timedelta(minutes=5)
    with freeze_time(period0) as freezer:
        await _record_meter(hass, freezer, period0, LEGACY_ID, [1000.0, 1001.0, 1002.0])
        do_adhoc_statistics(hass, start=period0)
        await async_wait_recording_done(hass)

        entity_registry.async_update_entity(LEGACY_ID, new_entity_id=MODERN_ID)
        await async_wait_recording_done(hass)

        # The meter keeps counting under the new id, as the inverter's own
        # register does; only Home Assistant's name for it changed.
        await _record_meter(hass, freezer, period1, MODERN_ID, [1003.0, 1005.0])
        do_adhoc_statistics(hass, start=period1)
        await async_wait_recording_done(hass)

    stats = statistics_during_period(hass, period0, period="5minute")[MODERN_ID]
    assert [row["sum"] for row in stats] == [pytest.approx(2.0), pytest.approx(5.0)]
    assert [row["state"] for row in stats] == [
        pytest.approx(1002.0),
        pytest.approx(1005.0),
    ]


async def test_rename_into_an_id_the_recorder_knows_is_refused(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The YAML migration's trap: the target id already has history.

    A user who removes the YAML package's registry entries still leaves its
    recorded rows behind. Renaming an integration entity onto that id is then
    refused and the two histories stay apart -- the failure is a log line, not
    an exception, so nothing surfaces in the UI.
    """
    start = _period_start()
    with freeze_time(start) as freezer:
        # Years of YAML history, its registry entry since deleted.
        await _record_meter(hass, freezer, start, LEGACY_ID, [1000.0, 1002.0])
        await _retire(hass, LEGACY_ID)
        assert entity_registry.async_get(LEGACY_ID) is None

        entity_registry.async_get_or_create(
            "sensor",
            "sungrow_shx",
            "A2340600123_total_pv_generation",
            suggested_object_id="sh10rt_total_pv_generation",
        )
        await _record_meter(hass, freezer, start, MODERN_ID, [1003.0])

        entity_registry.async_update_entity(MODERN_ID, new_entity_id=LEGACY_ID)
        await async_wait_recording_done(hass)

    assert "the new entity_id is already in use" in caplog.text
    assert _states_meta_ids(hass) >= {LEGACY_ID, MODERN_ID}
    assert _recorded_states(hass, start, LEGACY_ID) == ["1000.0", "1002.0", SEAM]
    assert _recorded_states(hass, start, MODERN_ID) == ["1003.0"]


async def test_claiming_the_legacy_id_at_creation_continues_history(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """The migration that works: take the legacy id, do not rename into it.

    An entity created directly on the legacy entity_id writes to the
    states_meta row that is already there, so raw history and statistics
    continue with no recorder surgery and nothing to refuse.
    """
    period0 = _period_start()
    period1 = period0 + timedelta(minutes=5)
    with freeze_time(period0) as freezer:
        # The YAML package's years of history.
        await _record_meter(hass, freezer, period0, LEGACY_ID, [1000.0, 1001.0, 1002.0])
        do_adhoc_statistics(hass, start=period0)
        await async_wait_recording_done(hass)

        await _retire(hass, LEGACY_ID)

        # The integration takes over the same id under its own platform.
        entry = entity_registry.async_get_or_create(
            "sensor",
            "sungrow_shx",
            "A2340600123_total_pv_generation",
            suggested_object_id="total_pv_generation",
        )
        assert entry.entity_id == LEGACY_ID

        await _record_meter(hass, freezer, period1, LEGACY_ID, [1003.0, 1005.0])
        do_adhoc_statistics(hass, start=period1)
        await async_wait_recording_done(hass)

    assert _recorded_states(hass, period0, LEGACY_ID) == [
        "1000.0",
        "1001.0",
        "1002.0",
        SEAM,
        "1003.0",
        "1005.0",
    ]
    assert _states_meta_ids(hass) == {LEGACY_ID}

    stats = statistics_during_period(hass, period0, period="5minute")[LEGACY_ID]
    assert [row["sum"] for row in stats] == [pytest.approx(2.0), pytest.approx(5.0)]


async def test_a_compatible_unit_change_is_converted_not_lost(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """A different but convertible unit is fine: statistics are converted.

    Useful headroom for the port, because the library holds each register in
    its raw unit while the YAML applies a scale. As long as the published
    value is physically the same quantity and its unit belongs to the same
    unit class, the recorder converts into the unit the statistics were
    compiled in and the series continues.
    """
    _register_legacy_entity(entity_registry)

    period0 = _period_start()
    period1 = period0 + timedelta(minutes=5)
    with freeze_time(period0) as freezer:
        await _record_meter(hass, freezer, period0, LEGACY_ID, [1000.0, 1002.0])
        do_adhoc_statistics(hass, start=period0)
        await async_wait_recording_done(hass)

        # The same meter, published in Wh instead of kWh.
        await _record_meter(
            hass,
            freezer,
            period1,
            LEGACY_ID,
            [1_003_000.0, 1_005_000.0],
            attributes=METER_ATTRS | {"unit_of_measurement": UnitOfEnergy.WATT_HOUR},
        )
        do_adhoc_statistics(hass, start=period1)
        await async_wait_recording_done(hass)

    # Queried in kWh explicitly: the display unit of a statistics query
    # follows the entity's current unit, so asking without pinning it returns
    # the same data expressed in Wh and looks like a thousandfold jump.
    stats = statistics_during_period(
        hass, period0, period="5minute", units={"energy": UnitOfEnergy.KILO_WATT_HOUR}
    )[LEGACY_ID]
    assert [row["sum"] for row in stats] == [pytest.approx(2.0), pytest.approx(5.0)]
    assert [row["state"] for row in stats] == [
        pytest.approx(1002.0),
        pytest.approx(1005.0),
    ]


async def test_an_incompatible_unit_freezes_statistics_flat(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A unit from another unit class is dropped, and the sum stops growing.

    The port's sharpest edge. The entity stays alive and its raw history
    keeps filling, so nothing looks broken -- but every later statistics
    period just repeats the last good state and sum, so the Energy dashboard
    draws a flat line rather than a gap: it reads as a system producing
    nothing, not as a system that is misconfigured. Only a log line says
    otherwise. Each ported entity therefore has to stay in the unit class of
    the YAML entry it replaces.
    """
    _register_legacy_entity(entity_registry)

    period0 = _period_start()
    period1 = period0 + timedelta(minutes=5)
    with freeze_time(period0) as freezer:
        await _record_meter(hass, freezer, period0, LEGACY_ID, [1000.0, 1002.0])
        do_adhoc_statistics(hass, start=period0)
        await async_wait_recording_done(hass)

        await _record_meter(
            hass,
            freezer,
            period1,
            LEGACY_ID,
            [1003.0, 1005.0],
            attributes=METER_ATTRS | {"unit_of_measurement": UnitOfPower.WATT},
        )
        do_adhoc_statistics(hass, start=period1)
        await async_wait_recording_done(hass)

    assert "cannot be converted to the unit of previously compiled" in caplog.text

    # States kept recording; only the statistics stopped.
    assert _recorded_states(hass, period0, LEGACY_ID) == [
        "1000.0",
        "1002.0",
        "1003.0",
        "1005.0",
    ]
    stats = statistics_during_period(hass, period0, period="5minute")[LEGACY_ID]
    assert [row["sum"] for row in stats] == [pytest.approx(2.0), pytest.approx(2.0)]
    assert [row["state"] for row in stats] == [
        pytest.approx(1002.0),
        pytest.approx(1002.0),
    ]
