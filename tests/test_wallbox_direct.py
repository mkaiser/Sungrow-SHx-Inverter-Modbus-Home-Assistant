"""The wallbox's own address, as an option on the inverter's entry.

Measured on an AC22E-01: Modbus TCP inside TLS on port 516, unit 248, at the
wallbox's own LAN address. The option is checked when it is saved, so an
address that answers nothing is refused in the dialog rather than found out
at the next poll.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

from modbus_connection import ModbusConnectionError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus import config_flow
from custom_components.sungrow_modbus.const import (
    CONF_UNIT_ID,
    CONF_WALLBOX_HOST,
    DOMAIN,
    SECTION_ADVANCED,
    SECTION_CONTROL_TEST,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
    SECTION_SURVEY,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: The AC22E-01's model name as it answers it, input 21216.
MODEL_WORDS = {21215: 0x4143, 21216: 0x3232, 21217: 0x452D, 21218: 0x3031, 21219: 0}


def _submission(**advanced) -> dict:
    """Return a full options submission with only the advanced section set."""
    return {
        SECTION_POLLING: {"realtime": 5, "fast": 10, "medium": 60, "slowest": 600},
        SECTION_PERMISSIONS: {},
        SECTION_EXTERNAL: {},
        SECTION_ADVANCED: advanced,
        SECTION_SURVEY: {},
        SECTION_CONTROL_TEST: {},
    }


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _configure(hass, entry, unit, answers: bool, **advanced):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    with (
        patch.object(config_flow, "_async_wallbox_answers", return_value=answers),
        patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], _submission(**advanced)
        )
        await hass.async_block_till_done()
    return result


async def test_an_address_where_a_wallbox_answers_is_saved(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)

    result = await _configure(
        hass, entry, sungrow_unit, True, **{CONF_WALLBOX_HOST: " 192.0.2.23 "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WALLBOX_HOST] == "192.0.2.23"


async def test_an_address_where_nothing_answers_is_refused(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit)

    result = await _configure(
        hass, entry, sungrow_unit, False, **{CONF_WALLBOX_HOST: "192.0.2.99"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wallbox_not_found"}
    assert CONF_WALLBOX_HOST not in entry.options


async def test_clearing_the_address_is_never_probed(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Empty means "through the dongle again", and needs no wallbox to answer."""
    entry = await _setup(hass, sungrow_unit)

    result = await _configure(
        hass, entry, sungrow_unit, False, **{CONF_WALLBOX_HOST: ""}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WALLBOX_HOST] == ""


def _temporary(unit_or_error):
    """Stand in for `async_get_temporary_unit`, recording what it was asked."""
    asked: list = []

    @asynccontextmanager
    async def temporary(_hass, params, unit_id):
        asked.append((type(params).__name__, params.port, params.verify, unit_id))
        if isinstance(unit_or_error, Exception):
            raise unit_or_error
        yield unit_or_error

    return temporary, asked


async def test_the_check_reads_the_model_name_over_tls_at_unit_248(
    hass: HomeAssistant,
) -> None:
    wallbox = MockModbusConnection().for_unit(248)
    wallbox.input = dict(MODEL_WORDS)
    temporary, asked = _temporary(wallbox)

    with patch.object(config_flow, "async_get_temporary_unit", temporary):
        assert await config_flow._async_wallbox_answers(hass, "192.0.2.23")

    assert asked == [("ModbusTlsParams", 516, False, 248)]


async def test_a_link_that_fails_is_not_a_wallbox(hass: HomeAssistant) -> None:
    temporary, _asked = _temporary(ModbusConnectionError("refused"))

    with patch.object(config_flow, "async_get_temporary_unit", temporary):
        assert not await config_flow._async_wallbox_answers(hass, "192.0.2.23")
