"""Mode flags, and the three-state question the YAML got wrong.

The YAML package's Modbus switches treat any value other than the `on` code
as off. That is fine until the register answers 0xFFFF -- the specification's
"unavailable" -- and the interface then says a feature is *disabled* when the
model simply does not have it. Two of these tests exist for that.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_modbus.entity import SungrowSwitchDescription
from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from sungrow_modbus import Capability

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

BACKUP = "switch.sh10rt_backup_mode"
BACKUP_ADDRESS = 13074


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    sungrow_unit.holding[BACKUP_ADDRESS] = 0x55  # off
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=sungrow_unit
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _call(hass: HomeAssistant, service: str, entity_id: str) -> None:
    await hass.services.async_call(
        SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


async def test_the_two_codes_the_specification_states_are_the_two_states(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    assert hass.states.get(BACKUP).state == "off"

    await _call(hass, SERVICE_TURN_ON, BACKUP)
    assert sungrow_unit.holding[BACKUP_ADDRESS] == 0xAA
    assert hass.states.get(BACKUP).state == "on"

    await _call(hass, SERVICE_TURN_OFF, BACKUP)
    assert sungrow_unit.holding[BACKUP_ADDRESS] == 0x55
    assert hass.states.get(BACKUP).state == "off"


async def test_an_unavailable_register_is_unknown_not_off(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """The bug this avoids: "off" and "your model has not got it" are different.

    The YAML's switches call anything that is not the `on` code off, so a
    register answering 0xFFFF reads as a feature the user has switched off.
    """
    sungrow_unit.holding[BACKUP_ADDRESS] = 0xFFFF
    await entry.runtime_data.coordinator_for("fast_holding").async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(BACKUP).state == STATE_UNKNOWN


async def test_a_value_neither_code_is_also_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Guessing at an undocumented value is worse than admitting to it."""
    sungrow_unit.holding[BACKUP_ADDRESS] = 0x42
    await entry.runtime_data.coordinator_for("fast_holding").async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(BACKUP).state == STATE_UNKNOWN


async def test_the_new_state_is_visible_without_waiting_for_a_poll(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """`verify: true` in the YAML was the right instinct, and it is kept."""
    assert hass.states.get(BACKUP).state == "off"
    await _call(hass, SERVICE_TURN_ON, BACKUP)
    assert hass.states.get(BACKUP).state == "on"


async def test_a_flag_the_inverter_refuses_is_shown_as_refused(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """An inverter may reject a mode it cannot enter right now."""

    async def refuse(address: int, value: int) -> None:
        return None  # accepted on the wire, ignored by the device

    with patch.object(type(sungrow_unit), "write_register", side_effect=refuse):
        await _call(hass, SERVICE_TURN_ON, BACKUP)

    # The register still says off, and so does the entity -- not "on" because
    # that is what was asked for.
    assert sungrow_unit.holding[BACKUP_ADDRESS] == 0x55
    assert hass.states.get(BACKUP).state == "off"


async def test_a_failed_write_is_reported_rather_than_swallowed(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    with (
        patch.object(
            type(sungrow_unit),
            "write_register",
            side_effect=ModbusError("device rejected the write"),
        ),
        pytest.raises(HomeAssistantError, match="Could not write"),
    ):
        await _call(hass, SERVICE_TURN_ON, BACKUP)


async def test_all_three_flags_exist_and_are_configuration(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for key in (
        "backup_mode",
        "export_power_limit_mode",
        "load_adjustment_mode_enable",
    ):
        entity_id = registry.async_get_entity_id("switch", DOMAIN, f"{SERIAL}_{key}")
        assert entity_id is not None, key
        assert registry.async_get(entity_id).entity_category is er.EntityCategory.CONFIG


async def test_a_second_change_inside_the_debounce_window_is_still_shown(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """The coordinator's refresh debouncer has a ten second cooldown.

    Routed through it, a second change is written to the register and never
    read back, so the interface shows the previous value for up to ten
    seconds. That is exactly what the YAML package's
    `homeassistant.update_entity` calls existed to work around, and it is why
    a write refreshes immediately rather than requesting one.
    """
    for service, code, expected in (
        (SERVICE_TURN_ON, 0xAA, "on"),
        (SERVICE_TURN_OFF, 0x55, "off"),
        (SERVICE_TURN_ON, 0xAA, "on"),
    ):
        await _call(hass, service, BACKUP)
        assert sungrow_unit.holding[BACKUP_ADDRESS] == code
        assert hass.states.get(BACKUP).state == expected, service


# -- the discharge windows, and the hour a `time` cannot hold ------------------


def _switch(key: str) -> SungrowSwitchDescription:
    """Return the generated description with this key."""
    return next(d for d in SWITCH_DESCRIPTIONS if d.key == key)


ALL_DAY = "weekday_discharge_end_1_all_day"


def test_a_window_end_switch_writes_the_hour_a_time_cannot_hold() -> None:
    """24:00 is the end of the day, and a `time` entity holds 23:59 at most.

    Every untouched house reads its discharge windows as 00:00 to 24:00, so
    without this switch the `time` beside it could read such a window and
    never write it back.
    """
    description = _switch(ALL_DAY)
    assert description.field == "weekday_discharge_end_1_hour"
    assert description.minute_field == "weekday_discharge_end_1_minute"
    assert (description.on_value, description.on_minute) == (24, 0)
    assert (description.off_value, description.off_minute) == (23, 59)


def test_every_discharge_window_end_has_one() -> None:
    """Four windows, four switches: two weekday and two weekend."""
    keys = {d.key for d in SWITCH_DESCRIPTIONS if d.key.endswith("_all_day")}
    assert keys == {
        f"{day}_discharge_end_{window}_all_day"
        for day in ("weekday", "weekend")
        for window in (1, 2)
    }


def test_the_discharge_entities_need_a_watched_write() -> None:
    """Answering the register is not leave to write it.

    The windows are outside Sungrow's document, so what writing them does was
    settled by watching a discharge stop, on two firmwares -- and the
    capability that carries that is granted by firmware, never by a probe.
    """
    for description in SWITCH_DESCRIPTIONS:
        if "discharge" in description.key and "forced" not in description.key:
            assert description.requires is Capability.DISCHARGE_SCHEDULE_CONTROL, (
                description.key
            )
