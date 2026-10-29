"""The fault and alarm words, and the entities that report them.

Appendix 4 names about two hundred flags across fifteen U32s. These tests hold
the table to the shape the specification gives it, hold the decoding to the
one reading with a flag set that the surveys contain, and check that the
entities say what is set rather than a number nobody can read.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_ENTITY_IDS,
    CONF_UNIT_ID,
    DOMAIN,
    ENTITY_IDS_NEW,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus.inverter.faults import (
    BY_FIELD,
    FAULT_WORDS,
    UNAVAILABLE,
    active,
    reported,
)
from sungrow_modbus.inverter.registers import InverterFaults

from .conftest import SERIAL


def test_fifteen_adjacent_words_from_13050() -> None:
    """One read of thirty registers, and every word where the table says."""
    assert len(FAULT_WORDS) == 15
    addresses = [word.address for word in FAULT_WORDS]
    assert addresses == list(range(13049, 13079, 2))
    for word in FAULT_WORDS:
        field = getattr(InverterFaults, word.field)
        assert field.address == word.address, word.field
        assert field.word_order == "little", word.field
        assert all(0 <= bit < 32 for bit in word.bits), word.field


def test_no_reserved_bit_is_named() -> None:
    for word in FAULT_WORDS:
        assert "Reserved" not in word.bits.values(), word.field
    assert BY_FIELD["bms_fault_2"].bits == {}


def test_the_reading_with_a_flag_set_decodes_to_the_meter_alarm() -> None:
    """The slave at fwitten has no meter, and its inverter alarm says so.

    It read 0x4000 in the high word, on its cable and through its dongle.
    Low word first, that is bit 30.
    """
    assert active("inverter_alarm", 0x4000 << 16) == ("Meter Communication Alarm",)


def test_reserved_bits_set_are_not_reported() -> None:
    """The high word of BMS alarm 2 reads 0xFFFF on every cable surveyed."""
    assert active("bms_alarm_2", 0xFFFF0000) == ()
    assert reported("alarm", {"bms_alarm_2": 0xFFFF0000}) is False


def test_unavailable_and_unread_are_not_all_clear() -> None:
    assert active("grid_side_fault", UNAVAILABLE) is None
    assert active("grid_side_fault", None) is None
    assert reported("fault", {}) is None


def test_a_label_on_several_bits_is_listed_once() -> None:
    """System fault 2 bits 4-6 are all "Device Abnormality"."""
    assert active("system_fault_2", 0b1110000) == ("Device Abnormality",)


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 5020,
            CONF_UNIT_ID: 1,
            CONF_ENTITY_IDS: ENTITY_IDS_NEW,
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_a_quiet_inverter_reports_nothing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    for address in range(13049, 13079):
        sungrow_unit.input[address] = 0
    await _setup(hass, sungrow_unit)

    state = hass.states.get("sensor.sh10rt_grid_side_fault")
    assert state.state == "0"
    assert state.attributes["active"] == []
    assert hass.states.get("binary_sensor.sh10rt_fault_reported").state == "off"
    assert hass.states.get("binary_sensor.sh10rt_alarm_reported").state == "off"


async def test_a_set_flag_is_counted_named_and_reported(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    for address in range(13049, 13079):
        sungrow_unit.input[address] = 0
    # Grid-side fault bits 0 and 8, low word first: register 13052 = 0x0101.
    sungrow_unit.input[13051] = 0x0101
    await _setup(hass, sungrow_unit)

    state = hass.states.get("sensor.sh10rt_grid_side_fault")
    assert state.state == "2"
    assert state.attributes["active"] == ["Grid Overvoltage", "Grid Power Outage"]
    assert hass.states.get("binary_sensor.sh10rt_fault_reported").state == "on"
    # A fault is not an alarm.
    assert hass.states.get("binary_sensor.sh10rt_alarm_reported").state == "off"
