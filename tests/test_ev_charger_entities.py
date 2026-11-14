"""The managed wallbox's controls, on the inverter's entry, on watched firmware.

Registers 33540 (charging on/off), 33541 (mode), 33545 (user-defined current)
and 33550 (energy purchase), outside Sungrow's document, watched at gerd's on
P022 (wiki: gerd-wallbox-inverter-control-2026-11-14). Created only where the
mode reads a named code and the firmware is one the writes were watched on.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.hybrid_inverter import capabilities, ev_charger as ev
from sungrow_modbus.hybrid_inverter.capabilities import Capability, probe, resolve

from .conftest import SERIAL, encode_string

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol address of register 13250, the inverter's firmware.
INVERTER_FIRMWARE_ADDRESS = 13249
WATCHED = "SAPPHIRE-H_B001.V000.P022"
UNWATCHED = "SAPPHIRE-H_B001.V000.P023"


async def _setup(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    *,
    firmware: str = WATCHED,
    mode: int = ev.FAST,
    charging: int = ev.ON,
) -> MockConfigEntry:
    unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(firmware, 15)
    unit.holding[ev.CHARGING] = charging
    unit.holding[ev.MODE] = mode
    unit.holding[ev.USER_CURRENT] = 160
    unit.holding[ev.GRID_SURPLUS] = ev.OFF
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity_id(hass: HomeAssistant, domain: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}")


def test_only_the_watched_firmware_is_confirmed() -> None:
    assert capabilities.CONFIRMED_ON_FIRMWARE[
        Capability.EV_CHARGER_CONTROL
    ] == frozenset({WATCHED})


@pytest.mark.parametrize(
    ("word", "granted"),
    [(160, True), (161, True), (162, True), (163, True), (0, False), (164, False)],
)
def test_only_a_named_mode_grants_the_ev_charger(word: int, granted: bool) -> None:
    """0 and an unnamed code are not a managed wallbox, as far as anyone knows."""
    found = probe(lambda field: word if field == "ev_charger_mode_raw" else None)
    assert (Capability.EV_CHARGER in found) is granted


def test_control_needs_the_read_and_the_firmware() -> None:
    answered = frozenset({Capability.EV_CHARGER})
    assert Capability.EV_CHARGER_CONTROL in resolve(0x0E03, 1, answered, WATCHED)
    assert Capability.EV_CHARGER_CONTROL not in resolve(0x0E03, 1, frozenset(), WATCHED)
    assert Capability.EV_CHARGER_CONTROL not in resolve(0x0E03, 1, answered, UNWATCHED)


async def test_watched_firmware_gets_the_four_controls(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)

    assert (
        hass.states.get(_entity_id(hass, "switch", "ev_charger_charging")).state == "on"
    )
    assert (
        hass.states.get(_entity_id(hass, "switch", "ev_charger_grid_purchase")).state
        == "off"
    )
    assert (
        hass.states.get(_entity_id(hass, "select", "ev_charger_mode")).state == "fast"
    )
    assert float(
        hass.states.get(_entity_id(hass, "number", "ev_charger_user_current")).state
    ) == pytest.approx(16.0)


@pytest.mark.parametrize(("firmware", "mode"), [(UNWATCHED, ev.FAST), (WATCHED, 0)])
async def test_no_controls_without_watched_firmware_or_a_named_mode(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, firmware: str, mode: int
) -> None:
    await _setup(hass, sungrow_unit, firmware=firmware, mode=mode)

    for domain, key in (
        ("switch", "ev_charger_charging"),
        ("switch", "ev_charger_grid_purchase"),
        ("select", "ev_charger_mode"),
        ("number", "ev_charger_user_current"),
    ):
        assert _entity_id(hass, domain, key) is None


async def test_the_charging_switch_writes_the_on_and_off_words(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)
    entity_id = _entity_id(hass, "switch", "ev_charger_charging")

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert sungrow_unit.holding[ev.CHARGING] == ev.OFF
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    assert sungrow_unit.holding[ev.CHARGING] == ev.ON


async def _select(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {
            ATTR_ENTITY_ID: _entity_id(hass, "select", "ev_charger_mode"),
            ATTR_OPTION: option,
        },
        blocking=True,
    )


async def test_a_mode_change_that_ends_the_session_switches_charging_on_again(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Fast to PV surplus ended the session at gerd's; charging on restarted it."""
    await _setup(hass, sungrow_unit, mode=ev.FAST, charging=ev.ON)
    writes: list[tuple[int, int]] = []
    original = sungrow_unit.write_register

    async def record(address: int, value: int, *args: object, **kwargs: object) -> None:
        writes.append((address, value))
        # The inverter ends the session when it leaves fast charge.
        await original(address, value, *args, **kwargs)
        if address == ev.MODE:
            sungrow_unit.holding[ev.CHARGING] = ev.OFF

    with patch.object(sungrow_unit, "write_register", record):
        await _select(hass, "pv_surplus")

    assert writes == [(ev.MODE, ev.PV_SURPLUS), (ev.CHARGING, ev.ON)]
    assert sungrow_unit.holding[ev.CHARGING] == ev.ON


async def test_user_defined_leaves_charging_off_when_it_was_off(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """To user defined switched charging on by itself, even from off."""
    await _setup(hass, sungrow_unit, mode=ev.FAST, charging=ev.OFF)

    await _select(hass, "user_defined")

    assert sungrow_unit.holding[ev.MODE] == ev.USER_DEFINED
    assert sungrow_unit.holding[ev.CHARGING] == ev.OFF


async def _set_current(hass: HomeAssistant, amps: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: _entity_id(hass, "number", "ev_charger_user_current"),
            ATTR_VALUE: amps,
        },
        blocking=True,
    )


async def test_the_user_current_is_written_in_user_defined_mode(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit, mode=ev.USER_DEFINED)

    await _set_current(hass, 10)

    assert sungrow_unit.holding[ev.USER_CURRENT] == 100


async def test_the_user_current_is_refused_before_writing_in_any_other_mode(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The inverter refuses 33545 outside user defined: say so, write nothing."""
    await _setup(hass, sungrow_unit, mode=ev.FAST)

    with pytest.raises(ServiceValidationError) as raised:
        await _set_current(hass, 10)

    assert raised.value.translation_key == "ev_charger_user_current_mode"
    assert raised.value.translation_placeholders["mode_entity"] == _entity_id(
        hass, "select", "ev_charger_mode"
    )
    assert sungrow_unit.holding[ev.USER_CURRENT] == 160
