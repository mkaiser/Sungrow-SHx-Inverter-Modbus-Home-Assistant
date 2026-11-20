"""The managed wallbox's controls, on the inverter's entry, on watched firmware.

Registers 33540 (charging on/off), 33541 (mode), 33545 (user-defined current)
and 33550 (energy purchase), outside Sungrow's document, watched at gerd's on
P022 (wiki: gerd-wallbox-inverter-control-2026-11-14). Created only where the
mode reads a named code and the firmware is one the writes were watched on.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection import ServerDeviceFailureError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
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
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.hybrid_inverter import capabilities, ev_charger as ev
from sungrow_modbus.hybrid_inverter.capabilities import Capability, probe, resolve
from sungrow_modbus.wallbox import capability_test as wct

from .conftest import SERIAL, encode_string
from .test_wallbox_entities import WORDS, _wallbox_unit
from .test_wallbox_one_device import _inverter_entry, _set_up, _Units, _wallbox_entry

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol address of register 13250, the inverter's firmware.
INVERTER_FIRMWARE_ADDRESS = 13249
WATCHED = "SAPPHIRE-H_B001.V000.P022"
UNWATCHED = "SAPPHIRE-H_B001.V000.P023"


def _seed(
    unit: MockModbusUnit,
    *,
    firmware: str = WATCHED,
    mode: int = ev.FAST,
    charging: int = ev.ON,
) -> None:
    """Give the inverter its firmware and its EV charger block."""
    unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(firmware, 15)
    unit.holding[ev.CHARGING] = charging
    unit.holding[ev.MODE] = mode
    unit.holding[ev.USER_CURRENT] = 160
    unit.holding[ev.GRID_SURPLUS] = ev.OFF


def _rated(word: int) -> dict[str, dict[int, int]]:
    """Return the wallbox's words with its rated current set to `word`."""
    return {**WORDS, "input": {**WORDS["input"], wct.RATED_CURRENT: word}}


async def _setup(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    *,
    firmware: str = WATCHED,
    mode: int = ev.FAST,
    charging: int = ev.ON,
    wallbox_at: int | None = 3,
    rated: int = 320,
) -> MockConfigEntry:
    _seed(unit, firmware=firmware, mode=mode, charging=charging)
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    empty = MockModbusConnection().for_unit(9)
    empty.input = {}
    empty.holding = {}

    def units(_hass, _entry, _params, unit_id):
        if unit_id == 1:
            return unit
        if wallbox_at is not None and unit_id == wallbox_at:
            return _wallbox_unit(unit_id, _rated(rated))
        return empty

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
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


async def test_no_controls_where_no_wallbox_answers_on_the_bus(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A named mode is the block's factory state, not a wallbox.

    33541 reads 161 (PV surplus) with the user current at 16.0 A on houses
    that have no wallbox at all (wiki: device-wallbox), so the capability
    alone would offer four controls for nothing to drive. The entities ask
    for a wallbox on the inverter's bus besides
    (`SungrowRuntimeData.has_wallbox`).
    """
    await _setup(hass, sungrow_unit, mode=ev.PV_SURPLUS, wallbox_at=None)

    assert (
        Capability.EV_CHARGER_CONTROL
        in hass.config_entries.async_entries(DOMAIN)[0].runtime_data.capabilities
    )
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


def _reads_on_after_off(unit: MockModbusUnit):
    """Return a write that takes 33540's off and leaves the word reading on.

    What gerd's inverter did on 2026-11-20: the car stops, the word reads
    0xAA for about 10 s more.
    """
    original = unit.write_register

    async def write(address: int, value: int, *args: object, **kwargs: object) -> None:
        await original(address, value, *args, **kwargs)
        if address == ev.CHARGING and value == ev.OFF:
            unit.holding[ev.CHARGING] = ev.ON

    return write


async def _switch_charging(hass: HomeAssistant, service: str, entity_id: str) -> None:
    await hass.services.async_call(
        SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )


async def test_an_off_is_held_through_the_word_reading_on_after_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, freezer: FrozenDateTimeFactory
) -> None:
    """The read-back and the next poll read on; the switch shows the off."""
    entry = await _setup(hass, sungrow_unit)
    entity_id = _entity_id(hass, "switch", "ev_charger_charging")
    assert entity_id is not None

    with patch.object(
        sungrow_unit, "write_register", _reads_on_after_off(sungrow_unit)
    ):
        await _switch_charging(hass, SERVICE_TURN_OFF, entity_id)
    assert hass.states.get(entity_id).state == "off"

    freezer.tick(timedelta(seconds=10))
    await entry.runtime_data.coordinator_for("ev_charger").async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    # Past the hold, a word still reading on is the state: someone, or the
    # inverter, switched charging on again.
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"


async def test_a_read_of_off_ends_the_hold(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Once the word has caught up, an on read inside the window is believed."""
    entry = await _setup(hass, sungrow_unit)
    entity_id = _entity_id(hass, "switch", "ev_charger_charging")
    assert entity_id is not None
    coordinator = entry.runtime_data.coordinator_for("ev_charger")

    with patch.object(
        sungrow_unit, "write_register", _reads_on_after_off(sungrow_unit)
    ):
        await _switch_charging(hass, SERVICE_TURN_OFF, entity_id)
    sungrow_unit.holding[ev.CHARGING] = ev.OFF
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    sungrow_unit.holding[ev.CHARGING] = ev.ON
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "on"


async def test_an_on_ends_the_hold_and_shows_on(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)
    entity_id = _entity_id(hass, "switch", "ev_charger_charging")
    assert entity_id is not None

    with patch.object(
        sungrow_unit, "write_register", _reads_on_after_off(sungrow_unit)
    ):
        await _switch_charging(hass, SERVICE_TURN_OFF, entity_id)
    await _switch_charging(hass, SERVICE_TURN_ON, entity_id)
    assert hass.states.get(entity_id).state == "on"


async def test_a_failed_off_holds_nothing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A refused write leaves the switch showing what the word reads."""
    await _setup(hass, sungrow_unit)
    entity_id = _entity_id(hass, "switch", "ev_charger_charging")
    assert entity_id is not None

    async def refuse(address: int, value: int, *args: object, **kwargs: object) -> None:
        raise ServerDeviceFailureError(0x04)

    with (
        patch.object(sungrow_unit, "write_register", refuse),
        pytest.raises(HomeAssistantError),
    ):
        await _switch_charging(hass, SERVICE_TURN_OFF, entity_id)
    assert hass.states.get(entity_id).state == "on"


async def test_the_mode_select_shows_the_user_defined_window(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """33546-33549 as gerd's inverter held them: a whole day from midnight."""
    sungrow_unit.holding.update(
        {
            ev.CHARGING + 6: 36224,
            ev.CHARGING + 7: 27391,
            ev.CHARGING + 8: 57088,
            ev.CHARGING + 9: 27392,
        }
    )
    await _setup(hass, sungrow_unit)
    state = hass.states.get(_entity_id(hass, "select", "ev_charger_mode"))

    assert state.attributes["window_start"] == "00:00"
    assert state.attributes["window_end"] == "24:00"


async def test_no_window_attributes_while_the_words_hold_none(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit)
    state = hass.states.get(_entity_id(hass, "select", "ev_charger_mode"))

    assert "window_start" not in state.attributes


def test_only_the_charging_word_is_held() -> None:
    """The hold is 33540's, measured; every other switch believes its reads."""
    held = {
        d.key: d.hold_off_seconds for d in SWITCH_DESCRIPTIONS if d.hold_off_seconds
    }
    assert held == {"ev_charger_charging": 20.0}


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


async def test_the_slider_stops_at_what_this_wallbox_is_rated_for(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """An AC011E-01 reads 16.0 A at 21263, half the static 32 A ceiling.

    The inverter does not cap the write -- 33.0 A was taken on a 32 A wallbox
    at gerd's -- so the entity's maximum is the only guard there is.
    """
    await _setup(hass, sungrow_unit, mode=ev.USER_DEFINED, rated=160)
    entity_id = _entity_id(hass, "number", "ev_charger_user_current")

    assert hass.states.get(entity_id).attributes["max"] == pytest.approx(16.0)
    with pytest.raises(ServiceValidationError):
        await _set_current(hass, 20)
    assert sungrow_unit.holding[ev.USER_CURRENT] == 160

    await _set_current(hass, 15)
    assert sungrow_unit.holding[ev.USER_CURRENT] == 150


@pytest.mark.parametrize("word", [0, 50])
async def test_a_rating_of_zero_or_below_the_floor_leaves_the_ceiling(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, word: int
) -> None:
    """A 0 is not a rating, and 5.0 A is below the 6.0 A the inverter takes.

    One reading of 21263 answered 0 (wiki: zero means absent), and a bound
    under the entity's own minimum would offer nothing at all. Either way the
    static 32 A stands.
    """
    await _setup(hass, sungrow_unit, mode=ev.USER_DEFINED, rated=word)
    entity_id = _entity_id(hass, "number", "ev_charger_user_current")

    assert hass.states.get(entity_id).attributes["max"] == pytest.approx(32.0)

    await _set_current(hass, 32)
    assert sungrow_unit.holding[ev.USER_CURRENT] == 320


async def test_the_rating_is_reached_in_a_wallbox_entry_of_its_own(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A wallbox with its own entry is still bounded at the inverter's slider.

    The inverter entry left the wallbox to that entry and polls it no more
    (`wallbox_elsewhere`), so the rating is read across: the same register on
    the same hardware, at no session's cost.
    """
    _seed(sungrow_unit, mode=ev.USER_DEFINED)
    units = _Units(sungrow_unit)
    units.direct.input[wct.RATED_CURRENT] = 160
    wallbox = _wallbox_entry(hass)
    inverter = _inverter_entry(hass)
    await _set_up(hass, units, wallbox, inverter)
    assert inverter.runtime_data.wallbox is None
    assert inverter.runtime_data.wallbox_elsewhere is not None

    entity_id = _entity_id(hass, "number", "ev_charger_user_current")
    assert hass.states.get(entity_id).attributes["max"] == pytest.approx(16.0)
    with pytest.raises(ServiceValidationError):
        await _set_current(hass, 20)
    assert sungrow_unit.holding[ev.USER_CURRENT] == 160
