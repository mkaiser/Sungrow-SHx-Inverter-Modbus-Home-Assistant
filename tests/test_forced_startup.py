"""Register 13017 as a switch, and register 31213 as an on/off sensor.

13017 is a switch, watched on P023 (bar12) and P020 (the maintainer's):
0xAA wakes an inverter in low-SoC standby and keeps it running, 0x55 sends
it back, and every other
word is refused -- the factory 0 included, which reads as off. The switch is
created only on firmware where a start was watched. 31213 holds a setting
both ways round in the diagnoses, so it is decoded, and its number stays only
for legacy history.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sungrow_modbus import SungrowInverter
from sungrow_modbus.hybrid_inverter import capabilities
from sungrow_modbus.hybrid_inverter.capabilities import Capability, resolve

from .conftest import SERIAL, encode_string

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses, one below the register numbers 13017 and 31213.
FORCED_STARTUP_ADDRESS = 13016
APL_SHUTDOWN_ADDRESS = 31212
INVERTER_FIRMWARE_ADDRESS = 13249
FIRMWARE = "SAPPHIRE-H_B001.V000.P023"


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
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


# -- 13017 ------------------------------------------------------------------


KEY = "forced_startup_under_low_soc"
UNCONFIRMED = "SAPPHIRE-H_B001.V000.P022"


def test_p020_and_p023_are_confirmed_to_start_on_13017() -> None:
    assert capabilities.CONFIRMED_ON_FIRMWARE[Capability.FORCED_STARTUP_CONTROL] == (
        frozenset({"SAPPHIRE-H_B001.V000.P020", FIRMWARE})
    )


def test_a_confirmed_firmware_grants_the_switch_only_where_13017_answers() -> None:
    answered = resolve(0x0E03, 1, frozenset({Capability.FORCED_STARTUP}), FIRMWARE)
    silent = resolve(0x0E03, 1, frozenset(), FIRMWARE)
    other = resolve(0x0E03, 1, frozenset({Capability.FORCED_STARTUP}), UNCONFIRMED)

    assert Capability.FORCED_STARTUP_CONTROL in answered
    assert Capability.FORCED_STARTUP_CONTROL not in silent
    assert Capability.FORCED_STARTUP_CONTROL not in other


async def test_no_switch_and_no_raw_sensor_on_unconfirmed_firmware(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(UNCONFIRMED, 15)
    await _setup(hass, sungrow_unit)

    assert _entity_id(hass, "switch", KEY) is None
    assert _entity_id(hass, "sensor", "forced_startup_under_low_soc_raw") is None


@pytest.mark.parametrize(
    ("word", "expected"), [(0, "off"), (0x55, "off"), (0xAA, "on")]
)
async def test_the_switch_reads_the_factory_0_as_off(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, word: int, expected: str
) -> None:
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(FIRMWARE, 15)
    sungrow_unit.holding[FORCED_STARTUP_ADDRESS] = word
    await _setup(hass, sungrow_unit)
    switch_id = _entity_id(hass, "switch", KEY)
    assert switch_id is not None

    assert hass.states.get(switch_id).state == expected


async def test_no_switch_where_13017_reads_unavailable(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(FIRMWARE, 15)
    sungrow_unit.holding[FORCED_STARTUP_ADDRESS] = 0xFFFF
    await _setup(hass, sungrow_unit)

    assert _entity_id(hass, "switch", KEY) is None


async def test_on_writes_0xaa_and_off_writes_0x55(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(FIRMWARE, 15)
    sungrow_unit.holding[FORCED_STARTUP_ADDRESS] = 0
    written: list[Any] = []
    sungrow_unit.on_write(
        lambda event: (
            written.extend(event.values)
            if event.address == FORCED_STARTUP_ADDRESS
            else None
        )
    )
    await _setup(hass, sungrow_unit)
    switch_id = _entity_id(hass, "switch", KEY)
    assert switch_id is not None

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_id}, blocking=True
    )
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": switch_id}, blocking=True
    )

    assert written == [0xAA, 0x55]
    assert all(word != 0 for word in written)


# -- 31213 ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("word", "expected"), [(0xAA, True), (0x55, False), (0, None), (0xFFFF, None)]
)
async def test_31213_decodes_to_a_flag(
    sungrow_unit: MockModbusUnit, word: int, expected: bool | None
) -> None:
    sungrow_unit.holding[APL_SHUTDOWN_ADDRESS] = word
    inverter = SungrowInverter(sungrow_unit)
    await inverter.async_update()

    assert inverter.derived.apl_shutdown_at_zero is expected


async def test_31213_is_an_on_off_sensor_and_its_number_is_legacy_only(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding[APL_SHUTDOWN_ADDRESS] = 0xAA
    await _setup(hass, sungrow_unit)
    flag = _entity_id(hass, "binary_sensor", "apl_shutdown_at_zero")

    assert flag is not None
    assert hass.states.get(flag).state == "on"
    assert _entity_id(hass, "sensor", "apl_shutdown_at_zero_raw") is None
