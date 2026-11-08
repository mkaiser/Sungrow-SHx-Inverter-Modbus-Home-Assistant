"""Register 32998, the site import limit, as a number on watched firmware.

Outside Sungrow's document (#546, #785). Watched on P020, P022 and P023: a
cap on grid import that holds a charge from the grid and leaves the house
load, PV and export alone (wiki: register-32998). The number is in W, the
field in kW, and where the number exists the read-only sensor does not.
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
from sungrow_modbus.hybrid_inverter import capabilities
from sungrow_modbus.hybrid_inverter.capabilities import Capability, resolve

from .conftest import SERIAL, encode_string

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses, one below the register numbers 32998 and 13250.
IMPORT_LIMIT_ADDRESS = 32997
INVERTER_FIRMWARE_ADDRESS = 13249
CONFIRMED = (
    "SAPPHIRE-H_B001.V000.P020",
    "SAPPHIRE-H_B001.V000.P022",
    "SAPPHIRE-H_B001.V000.P023",
)
UNCONFIRMED = "SAPPHIRE-H_01011.95.03"
KEY = "site_import_power_limit"


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, firmware: str, word: int
) -> MockConfigEntry:
    unit.input[INVERTER_FIRMWARE_ADDRESS] = encode_string(firmware, 15)
    unit.holding[IMPORT_LIMIT_ADDRESS] = word
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity_id(hass: HomeAssistant, domain: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{KEY}")


def test_the_three_watched_firmwares_are_confirmed() -> None:
    assert capabilities.CONFIRMED_ON_FIRMWARE[
        Capability.SITE_IMPORT_LIMIT_CONTROL
    ] == frozenset(CONFIRMED)


def test_control_is_granted_only_where_32998_answers() -> None:
    answered = frozenset({Capability.SITE_IMPORT_LIMIT})
    assert Capability.SITE_IMPORT_LIMIT_CONTROL in resolve(
        0x0E03, 1, answered, CONFIRMED[0]
    )
    assert Capability.SITE_IMPORT_LIMIT_CONTROL not in resolve(
        0x0E03, 1, frozenset(), CONFIRMED[0]
    )
    assert Capability.SITE_IMPORT_LIMIT_CONTROL not in resolve(
        0x0E03, 1, answered, UNCONFIRMED
    )


def test_a_zero_is_not_an_import_limit() -> None:
    """32998 refuses 0, so a 0 is a dongle answering for nothing."""
    assert Capability.SITE_IMPORT_LIMIT in capabilities.ZERO_MEANS_ABSENT


@pytest.mark.parametrize("firmware", CONFIRMED)
async def test_confirmed_firmware_gets_the_number_in_watts_and_no_sensor(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, firmware: str
) -> None:
    await _setup(hass, sungrow_unit, firmware, 2000)

    number_id = _entity_id(hass, "number")
    assert number_id is not None
    assert _entity_id(hass, "sensor") is None
    state = hass.states.get(number_id)
    assert float(state.state) == 20000.0
    assert state.attributes["unit_of_measurement"] == "W"
    assert state.attributes["min"] == 10
    assert state.attributes["max"] == 50000
    assert state.attributes["step"] == 10


async def test_unconfirmed_firmware_keeps_the_read_only_sensor(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    await _setup(hass, sungrow_unit, UNCONFIRMED, 2000)

    assert _entity_id(hass, "number") is None
    sensor_id = _entity_id(hass, "sensor")
    assert sensor_id is not None
    assert float(hass.states.get(sensor_id).state) == 20.0


@pytest.mark.parametrize("word", [0, 0xFFFF])
async def test_no_entity_where_32998_does_not_answer(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, word: int
) -> None:
    await _setup(hass, sungrow_unit, CONFIRMED[0], word)

    assert _entity_id(hass, "number") is None
    assert _entity_id(hass, "sensor") is None


async def test_a_value_in_watts_is_written_as_counts_of_ten_watts(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    written: list[Any] = []
    sungrow_unit.on_write(
        lambda event: (
            written.extend(event.values)
            if event.address == IMPORT_LIMIT_ADDRESS
            else None
        )
    )
    await _setup(hass, sungrow_unit, CONFIRMED[0], 2000)
    number_id = _entity_id(hass, "number")
    assert number_id is not None

    for watts in (500, 10, 50000):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": number_id, "value": watts},
            blocking=True,
        )

    assert written == [50, 1, 5000]
