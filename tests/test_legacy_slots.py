"""A house with several inverters: each one takes its own YAML slot.

The YAML package's copy for inverter *n* suffixes every name ` inv <n>` and
every unique_id `_inv_<n>`. Which inverter was which is measured by comparing
serials, and getting it wrong hands one inverter another's years of history
(wiki: legacy-slot), so each step of that is held here.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.components.recorder.common import (
    async_recorder_block_till_done,
    async_wait_recording_done,
)
from pytest_homeassistant.typing import RecorderInstanceContextManager

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_LEGACY_SLOT,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
)
from custom_components.sungrow_modbus.migration import (
    LEGACY_SUFFIXES,
    async_resolve_legacy_slot,
    legacy_entity_ids,
)
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL

#: Two more inverters. Not serial-shaped, so nothing here can be a real one.
SECOND = "second-inverter"
THIRD = "third-inverter"

#: The two layouts in the wild: the plain file plus `_inv_2`, or `_inv_1` plus
#: `_inv_2`; and a third inverter.
LAYOUTS: dict[str, dict[str, str]] = {
    "plain and 2": {"": SERIAL, "_inv_2": SECOND},
    "1 and 2": {"_inv_1": SERIAL, "_inv_2": SECOND},
    "1, 2 and 3": {"_inv_1": SERIAL, "_inv_2": SECOND, "_inv_3": THIRD},
}


@pytest.fixture
async def mock_recorder_before_hass(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Start the recorder before hass, as recorder tests must."""


@pytest.fixture
async def recorder(hass: HomeAssistant, recorder_mock: Recorder) -> None:
    """Wait for the recorder the slot is looked up in."""
    await async_recorder_block_till_done(hass)


def _register(
    registry: er.EntityRegistry, uid: str, object_id: str, suffix: str
) -> str:
    return registry.async_get_or_create(
        "sensor",
        "modbus",
        f"{uid}{suffix}",
        suggested_object_id=f"{object_id}{suffix}",
    ).entity_id


def _register_slots(
    hass: HomeAssistant, registry: er.EntityRegistry, layout: dict[str, str]
) -> dict[str, str]:
    """Register each slot's serial sensor and lifetime counter, serials live."""
    ids = {}
    for suffix, serial in layout.items():
        ids[suffix] = _register(
            registry, "sg_inverter_serial", "sungrow_inverter_serial", suffix
        )
        hass.states.async_set(ids[suffix], serial)
        _register(registry, "sg_total_pv_generation", "total_pv_generation", suffix)
    return ids


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=LAYOUTS)
async def test_each_serial_finds_its_own_slot_while_the_package_runs(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, layout: dict[str, str]
) -> None:
    _register_slots(hass, entity_registry, layout)

    for suffix, serial in layout.items():
        assert await async_resolve_legacy_slot(hass, serial) == suffix


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=LAYOUTS)
async def test_a_stranger_is_undetermined_and_not_the_first_slot(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, layout: dict[str, str]
) -> None:
    _register_slots(hass, entity_registry, layout)

    assert await async_resolve_legacy_slot(hass, "an-inverter-not-there") is None


async def test_an_unavailable_serial_sensor_is_undetermined(
    hass: HomeAssistant, entity_registry: er.EntityRegistry
) -> None:
    """The inverter being off says nothing about which slot it was."""
    ids = _register_slots(hass, entity_registry, LAYOUTS["1 and 2"])
    hass.states.async_set(ids["_inv_2"], STATE_UNAVAILABLE)

    assert await async_resolve_legacy_slot(hass, SECOND) is None
    assert await async_resolve_legacy_slot(hass, SERIAL) == "_inv_1"


@pytest.mark.parametrize("layout", LAYOUTS.values(), ids=LAYOUTS)
async def test_a_removed_package_is_found_in_the_recorder(
    hass: HomeAssistant,
    recorder: None,
    entity_registry: er.EntityRegistry,
    layout: dict[str, str],
) -> None:
    """The order the guide gives: the package gone, its rows still there."""
    ids = _register_slots(hass, entity_registry, layout)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    for entity_id in ids.values():
        hass.states.async_remove(entity_id)
    await async_wait_recording_done(hass)

    for suffix, serial in layout.items():
        assert await async_resolve_legacy_slot(hass, serial) == suffix


async def test_a_serial_recorded_under_two_slots_belongs_to_neither(
    hass: HomeAssistant, recorder: None, entity_registry: er.EntityRegistry
) -> None:
    """Files swapped between inverters: no evidence for either."""
    ids = _register_slots(hass, entity_registry, LAYOUTS["1 and 2"])
    await hass.async_block_till_done()
    hass.states.async_set(ids["_inv_2"], SERIAL)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    for entity_id in ids.values():
        hass.states.async_remove(entity_id)
    await async_wait_recording_done(hass)

    assert await async_resolve_legacy_slot(hass, SERIAL) is None


async def _setup_slot(
    hass: HomeAssistant, unit: MockModbusUnit, slot: str | None
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 5020,
            CONF_UNIT_ID: 1,
            CONF_ENTITY_IDS: ENTITY_IDS_MIGRATE,
            CONF_LEGACY_SLOT: slot,
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


@pytest.mark.parametrize("slot", LEGACY_SUFFIXES)
async def test_an_entry_claims_its_own_slots_id_and_leaves_the_others(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
    slot: str,
) -> None:
    """The claim itself, with every slot's counter there to be taken by mistake."""
    ids = {
        suffix: _register(
            entity_registry, "sg_total_pv_generation", "total_pv_generation", suffix
        )
        for suffix in LEGACY_SUFFIXES
    }

    await _setup_slot(hass, sungrow_unit, slot)

    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{SERIAL}_total_pv_generation"
        )
        == ids[slot]
        == f"sensor.total_pv_generation{slot}"
    )
    for suffix, entity_id in ids.items():
        if suffix != slot:
            entry = entity_registry.async_get(entity_id)
            assert entry is not None and entry.platform == "modbus"


async def test_an_undetermined_slot_claims_nothing(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    entity_registry: er.EntityRegistry,
) -> None:
    ids = [
        _register(
            entity_registry, "sg_total_pv_generation", "total_pv_generation", suffix
        )
        for suffix in LEGACY_SUFFIXES
    ]

    await _setup_slot(hass, sungrow_unit, None)

    for entity_id in ids:
        entry = entity_registry.async_get(entity_id)
        assert entry is not None and entry.platform == "modbus"


def test_no_two_slots_share_an_entity_id() -> None:
    seen: set[str] = set()
    for suffix in LEGACY_SUFFIXES:
        ids = legacy_entity_ids(suffix)
        assert not seen & ids
        seen |= ids
