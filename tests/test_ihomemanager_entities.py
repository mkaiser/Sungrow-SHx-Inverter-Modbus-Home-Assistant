"""An iHomeManager's readings, from the one unit measured.

The registers are that unit's own words, from its committed document
(SV930.001.00.P020, read 2026-11-10), so the decoding is checked against
what a device answered rather than against the map. The wiring is checked
with them in Home Assistant: which entities exist, and what they show.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_KIND,
    CONF_TLS,
    CONF_UNIT_ID,
    DOMAIN,
    KIND_IHOMEMANAGER,
)
from custom_components.sungrow_modbus.ihomemanager_descriptions import (
    IHOMEMANAGER_DESCRIPTIONS,
    PREFIX,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from sungrow_modbus.ihomemanager import TIER_COMPONENTS, SungrowIHomeManager

DOCUMENT = (
    Path(__file__).resolve().parent.parent
    / "device-diagnosis"
    / "results"
    / "ihomemanager"
    / "ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503.json"
)
HOST = "192.168.1.70"


def _measured() -> MockModbusUnit:
    """Return a unit answering the measured words; what did not answer is absent."""
    dump = json.loads(DOCUMENT.read_text(encoding="utf-8"))["ihomemanager"][
        "register_dump"
    ]
    unit = MockModbusConnection().for_unit(247)
    unit.input = {int(a): w for a, w in dump["input"].items() if w is not None}
    unit.holding = {int(a): w for a, w in dump["holding"].items() if w is not None}
    return unit


async def _polled() -> SungrowIHomeManager:
    device = SungrowIHomeManager(_measured())
    for tier in TIER_COMPONENTS:
        report = await device.async_update_tier(tier)
        assert not report.failed, report.failed
    return device


def test_every_description_reads_a_decoded_field() -> None:
    """A field that exists, never a `_raw` code, under the device's prefix."""
    names = SungrowIHomeManager(_measured()).field_names
    keys = [d.key for d in IHOMEMANAGER_DESCRIPTIONS]
    assert len(keys) == len(set(keys))
    for description in IHOMEMANAGER_DESCRIPTIONS:
        assert description.key == f"{PREFIX}{description.field}"
        assert description.field in names, description.field
        assert not description.field.endswith("_raw")


def test_every_component_is_polled_by_one_tier() -> None:
    polled = [c for components in TIER_COMPONENTS.values() for c in components]
    assert len(polled) == len(set(polled))
    for description in IHOMEMANAGER_DESCRIPTIONS:
        assert description.component in polled


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("ems_mode", "self-consumption"),
        ("charge_command", "discharge"),
        ("feed_in_limitation", "off"),
        ("charger_enabled", "on"),
        ("grid_draw_permitted", "off"),
        ("charger_status", "charging completed"),
        ("protocol_version", "V1.0.1"),
        ("battery_level", 85.0),
        ("battery_power", 0.81),
        ("total_rated_active_power", 20.0),
        ("total_rated_battery_capacity", 40.5),
        ("grid_import_energy", 184.5),
        ("grid_export_energy", 3453.6),
        ("voltage_a", 416.1),
        ("phase_a_voltage", 240.3),
        ("phase_a_power", 311),
        ("phase_b_power", -159),
        ("vpp_heartbeat", 300),
    ],
)
async def test_the_measured_unit_decodes(field: str, expected: object) -> None:
    """The values its document published, now through the device."""
    device = await _polled()
    assert device.field(field) == pytest.approx(expected)


async def test_its_software_version_is_read() -> None:
    device = await _polled()
    assert device.software_version == "iHomeManager-SV930.001.00.P020"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PORT: 503,
            CONF_UNIT_ID: 247,
            CONF_KIND: KIND_IHOMEMANAGER,
            CONF_TLS: False,
        },
        unique_id=f"{KIND_IHOMEMANAGER}-{HOST}-503",
        title="iHomeManager",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=_measured()
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _keys(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, str]:
    """Each entity's key, to its entity id."""
    return {
        e.unique_id.removeprefix(f"{entry.unique_id}_"): e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    }


async def test_the_entry_shows_its_readings_beside_its_diagnosis(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass)

    assert entry.state is ConfigEntryState.LOADED
    keys = _keys(hass, entry)
    assert {"diagnosis_start", "diagnosis_progress"} <= set(keys)
    assert {d.key for d in IHOMEMANAGER_DESCRIPTIONS} <= set(keys)
    # Left out on purpose: the unclear output type and codes.
    for left_out in ("output_type", "start_stop", "charger_mode", "channel_2"):
        assert not any(left_out in key for key in keys), left_out


async def test_the_states_are_the_measured_values(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    keys = _keys(hass, entry)

    def state(key: str) -> str:
        found = hass.states.get(keys[f"{PREFIX}{key}"])
        assert found is not None
        return found.state

    assert state("ems_mode") == "self-consumption"
    assert state("charger_status") == "charging completed"
    assert float(state("battery_level")) == 85.0
    assert float(state("grid_import_energy")) == 184.5


async def test_its_device_carries_the_software_version(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    (device,) = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert (DOMAIN, entry.unique_id) in device.identifiers
    assert device.sw_version == "iHomeManager-SV930.001.00.P020"


async def test_a_field_that_reads_nothing_gets_no_entity(
    hass: HomeAssistant,
) -> None:
    """The document's "unavailable" word: no entity, rather than one forever unknown."""
    unit = _measured()
    # 8161-8162, battery power, as S32 0x7FFFFFFF, low word first.
    unit.input[8160] = 0xFFFF
    unit.input[8161] = 0x7FFF
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: HOST,
            CONF_PORT: 503,
            CONF_UNIT_ID: 247,
            CONF_KIND: KIND_IHOMEMANAGER,
            CONF_TLS: False,
        },
        unique_id=f"{KIND_IHOMEMANAGER}-{HOST}-503",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    keys = _keys(hass, entry)
    assert f"{PREFIX}battery_power" not in keys
    assert f"{PREFIX}battery_level" in keys
