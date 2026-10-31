"""What the options page says the integration has already measured.

The survey section tells an owner which path this endpoint is, so that nobody
answers a question that has been measured. Register 6100 decides it, and it
has three answers, not two: answered is a cable, refused is a communication
module, and a busy or lost read is neither -- it is the one case the owner is
asked about, because a guess here is published in `survey_transport`.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ServerDeviceBusyError,
)
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus.addresses import DIRECT_ONLY_PROBE

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


async def _measured(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    *,
    load: bool = True,
    fields: dict[str, object] | None = None,
) -> dict[str, str]:
    """Return the options page's placeholders for one entry.

    `fields` overrides what the device reports for those names, the decoded
    values the page words; the registers behind them are tested elsewhere.
    """
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    if load:
        with patch(
            "custom_components.sungrow_modbus.async_get_unit", return_value=unit
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
    if fields:
        device = next(iter(entry.runtime_data.coordinators.values())).device
        reported = device.field

        def field(name: str) -> object:
            return fields[name] if name in fields else reported(name)

        device.field = field
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return result["description_placeholders"]


async def test_an_answered_6100_is_the_inverter_s_own_port(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    text = (await _measured(hass, sungrow_unit))["measured"]

    assert "its own LAN port" in text


@pytest.mark.parametrize(
    ("error", "says"),
    [
        # The device answering with an exception: that is the transport.
        (IllegalDataAddressError(), "through a communication module"),
        # Not answers about the register at all.
        (ServerDeviceBusyError(), "could not be measured"),
        (ModbusConnectionError("lost"), "could not be measured"),
    ],
    ids=["refused", "busy", "lost"],
)
async def test_6100_has_three_answers_not_two(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, error: Exception, says: str
) -> None:
    sungrow_unit.fail_read(
        DIRECT_ONLY_PROBE.address, error, register_type=DIRECT_ONLY_PROBE.space
    )

    text = (await _measured(hass, sungrow_unit))["measured"]

    assert says in text
    assert "its own LAN port" not in text


async def test_an_entry_that_is_not_loaded_claims_no_measurement(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    placeholders = await _measured(hass, sungrow_unit, load=False)

    assert "nothing has been measured" in placeholders["measured"]
    assert "nothing can be read" in placeholders["battery_status"]


async def test_a_fitted_module_is_named_beside_a_cable_route(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A house can have a cable and a dongle at once.

    Saying both stops a correct "its own LAN port" reading as a mistake to an
    owner who can see the dongle on the wall.
    """
    module = "WINET-SV200.001.00.P023"
    text = (
        await _measured(
            hass,
            sungrow_unit,
            fields={"communication_module_firmware_version": module},
        )
    )["measured"]

    assert "its own LAN port" in text
    assert "names itself WINET-SV200.001.00.P023" in text


@pytest.mark.parametrize(
    ("load", "says"),
    [
        (None, "has not reported a load figure"),
        (850.0, "house load of 850 W, which does not include"),
        (-850.0, "unmetered generator"),
    ],
    ids=["unread", "positive", "negative"],
)
async def test_the_load_reading_is_shown_as_the_evidence(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, load: float | None, says: str
) -> None:
    """A negative house load is the symptom the external-generator option fixes."""
    placeholders = await _measured(hass, sungrow_unit, fields={"load_power": load})

    assert says in placeholders["reported_load"]
