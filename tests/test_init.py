"""Test that the integration sets up under Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from sungrow_modbus import Capability

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    """Set up a config entry backed by the mock unit."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit",
        return_value=unit,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_entry_loads(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> None:
    """The entry reaches LOADED and registers the inverter as a device."""
    entry = await _setup(hass, sungrow_unit)

    assert entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Sungrow"
    assert device.model == "SH10RT"
    assert device.serial_number == SERIAL


async def test_total_dc_power_sensor(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The one milestone sensor exists and carries the decoded value."""
    await _setup(hass, sungrow_unit)

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_total_dc_power"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "7000"
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["device_class"] == "power"


async def test_entry_unloads(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> None:
    """Unloading tears the entry down cleanly."""
    entry = await _setup(hass, sungrow_unit)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_a_dropped_connection_names_its_usual_cause(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The message has to point somewhere useful.

    A Sungrow accepts very few Modbus sessions at once, so a dropped
    connection is nearly always a second client rather than a network fault.
    The bare library message -- "Connection lost before response was
    received" -- sends people to look at their cabling, which is what happened
    to the maintainer against his own inverter: the reads were fine, another
    client had the slots.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
        ),
        patch.object(
            type(sungrow_unit),
            "read_input_registers",
            side_effect=ModbusConnectionError("Connection lost"),
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert "accepts very few Modbus connections" in str(entry.reason)


async def test_a_capability_that_appears_later_reloads_the_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A block that missed the first poll must not cost its entities forever.

    Capabilities are probed once, after the first poll, because the entity
    list is built from them. On a Sungrow a block missing one poll is ordinary
    rather than exceptional, so without this an unlucky moment at setup costs
    MPPT3 until the next restart.
    """
    # Setup sees an SH10RT: MPPT3 absent, so no MPPT3 entities.
    entry = await _setup(hass, sungrow_unit)
    registry = er.async_get(hass)
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_mppt3_voltage")
        is None
    )
    assert Capability.MPPT3 not in entry.runtime_data.capabilities

    # The inverter now answers for MPPT3 -- what a block returning late, or a
    # tracker that was simply not read the first time, looks like.
    sungrow_unit.input[5014] = 3000
    sungrow_unit.input[5015] = 50

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        freezer_target = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(hass, freezer_target)
        await hass.async_block_till_done()
        await hass.async_block_till_done()

    assert Capability.MPPT3 in entry.runtime_data.capabilities
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_mppt3_voltage")
        == "sensor.sh10rt_mppt3_voltage"
    )


async def test_a_device_without_a_serial_fails_permanently_not_on_a_retry_loop(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Every unique id is built from the serial, so there is nothing to retry.

    Retrying every 30 seconds forever would only fill the log with a condition
    that will not change on its own.
    """
    sungrow_unit.input[4989] = [0] * 10  # answered, but with no serial

    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "no serial number" in str(entry.reason)


async def test_a_delayed_flag_waits_a_minute_then_reports_without_a_poll(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The `(delay)` twin of a power-flow bit, end to end.

    Its point is a dashboard that does not flicker, so the two things worth
    pinning are that it does not follow the bit immediately and that it does
    not wait for the next poll either — the entity it replaces was exact, and
    a 60-second delay reported up to a poll interval late would be a
    regression somebody would notice in an automation.
    """
    # Bit 0 of the power flow status: PV generating.
    sungrow_unit.input[13000] = 0x01
    await _setup(hass, sungrow_unit)

    registry = er.async_get(hass)
    plain = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{SERIAL}_pv_generating"
    )
    delayed = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{SERIAL}_pv_generating_delay"
    )
    assert plain is not None and delayed is not None

    assert hass.states.get(plain).state == "on"
    assert hass.states.get(delayed).state == "off", "followed the bit at once"

    # No poll in between: the wake-up alone has to write the new state.
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(delayed).state == "on"


async def test_a_delayed_flag_follows_the_bit_down_immediately(
    hass: HomeAssistant,
    sungrow_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Delayed on, immediate off. That asymmetry is what `delay_on` means."""
    sungrow_unit.input[13000] = 0x01
    await _setup(hass, sungrow_unit)

    delayed = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{SERIAL}_pv_generating_delay"
    )
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(delayed).state == "on"

    # The bit drops, and the next poll -- the realtime tier, every 5 s -- is
    # enough. No second minute.
    sungrow_unit.input[13000] = 0x00
    freezer.tick(timedelta(seconds=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(delayed).state == "off"


async def test_the_filtered_energy_sensor_averages_over_its_window(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The one `filter` entity the YAML had, ported.

    Its unit, device class and state class have to be the source's, because
    that is what Home Assistant's own filter sensor copies off the source
    state — and a replacement in a different unit class freezes long-term
    statistics flat while raw history keeps filling.
    """
    await _setup(hass, sungrow_unit)

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_daily_consumed_energy_filtered"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["unit_of_measurement"] == "kWh"
    assert state.attributes["device_class"] == "energy"
    assert state.attributes["state_class"] == "total"

    source = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_daily_consumed_energy"
    )
    # One sample in, so the average is the reading itself.
    assert float(state.state) == pytest.approx(float(hass.states.get(source).state))


async def test_a_preview_release_says_so_where_a_tester_will_look(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """One repair issue, raised at setup, saying names may still change.

    Three things label this a preview and they reach different people: a PEP
    440 pre-release version, which `pip` will not install without `--pre`; the
    integration's name in the Add integration dialog; and this, which is the
    only one somebody already running it will ever see.

    Not fixable, because there is nothing to fix -- it is a statement, and it
    is deleted when the preview ends.
    """
    from custom_components.sungrow_modbus import PREVIEW_ISSUE
    from homeassistant.helpers import issue_registry as ir

    await _setup(hass, sungrow_unit)

    issue = ir.async_get(hass).async_get_issue(DOMAIN, PREVIEW_ISSUE)
    assert issue is not None
    assert issue.is_fixable is False
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_key == PREVIEW_ISSUE

    # And the text exists, which is the half a translation key cannot assert.
    import json
    from pathlib import Path

    strings = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "sungrow_modbus"
            / "strings.json"
        ).read_text(encoding="utf-8")
    )
    text = strings["issues"][PREVIEW_ISSUE]
    assert "preview" in text["title"].lower()
    # The claim that matters, and the one this project got wrong for a while:
    # a rename does not move an id somebody already has.
    assert "does not move the ids you already have" in text["description"]


async def test_a_chosen_name_becomes_the_device_name_and_the_ids(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The other half of the name step: what the flow stores has to be used.

    A name is only worth asking for if it reaches the device registry, since
    that is what `has_entity_name` builds every entity id from. Without it
    the entry title changes and the ids stay `sensor.sh10rt_...`, which is
    the failure the question exists to prevent -- two inverters, one id and
    one `..._2`.
    """
    from homeassistant.const import CONF_NAME

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_NAME: "Garage"},
        unique_id=SERIAL,
        title="Garage",
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    assert device.name == "Garage"
    # The model is still reported, because it is what the hardware is -- the
    # name says where it is, which no register knows.
    assert device.model == "SH10RT"

    ids = {
        item.entity_id
        for item in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
    }
    assert "sensor.garage_total_dc_power" in ids, sorted(ids)[:5]


async def test_an_entry_without_a_name_keeps_the_device_it_always_had(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Every entry created before the name step has no name stored.

    So the absence has to mean "unchanged", not "call it something". If a
    default leaked in here, upgrading would rename the device on every
    existing install -- which does not move the ids already created, but does
    make a house set up before the upgrade disagree with one set up after.
    """
    entry = await _setup(hass, sungrow_unit)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    assert device.name_by_user is None
    ids = {
        item.entity_id
        for item in er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
    }
    assert "sensor.sh10rt_total_dc_power" in ids, sorted(ids)[:5]
