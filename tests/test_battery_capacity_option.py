"""A battery capacity the owner enters, beside the one the inverter reports.

Register 5639 is where the inverter reports its pack's size, and a Pylontech
Force H1 leaves it at 0. Nothing on Modbus can set it (5639 is an input
register, and the protocol has no writable capacity), so the options form
shows the reading, read-only, and takes an override beside it. The override
feeds the three battery charge sensors and nothing else.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_CAPACITY_REPORTED,
    CONF_UNIT_ID,
    DOMAIN,
    SECTION_ADVANCED,
    SECTION_CAPABILITY_TEST,
    SECTION_DIAGNOSIS,
    SECTION_EXTERNAL,
    SECTION_PERMISSIONS,
    SECTION_POLLING,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Register 5639's address: the inverter's report of the pack's size, x0.01 kWh.
CAPACITY_ADDRESS = 5638


async def _setup(
    hass: HomeAssistant,
    unit: MockModbusUnit,
    capacity: int,
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    unit.input[CAPACITY_ADDRESS] = capacity
    # Max and min SoC, 90 % and 10 %: unseeded, every charge would be 0.
    unit.holding.update({13057: 900, 13058: 100})
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options or {},
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _battery_section(result: Any) -> dict[str, Any]:
    """Return the Battery section's fields as {key: suggested value}."""
    for marker, value in result["data_schema"].schema.items():
        if str(marker) == SECTION_ADVANCED:
            return {
                str(field): (field.description or {}).get("suggested_value")
                for field in value.schema.schema
            }
    raise AssertionError("no Battery section")


async def _submit(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MockModbusUnit,
    battery: dict[str, Any],
) -> dict[str, Any]:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                SECTION_POLLING: {},
                SECTION_PERMISSIONS: {},
                SECTION_EXTERNAL: {},
                SECTION_ADVANCED: battery,
                SECTION_DIAGNOSIS: {},
                SECTION_CAPABILITY_TEST: {},
            },
        )
        await hass.async_block_till_done()
    return result


def _state(hass: HomeAssistant, key: str) -> str:
    registry = er.async_get(hass)
    entity_id = next(
        entry.entity_id
        for entry in registry.entities.values()
        if entry.platform == DOMAIN and entry.unique_id == f"{SERIAL}_{key}"
    )
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def test_the_form_shows_what_the_inverter_reports(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit, capacity=960)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    fields = _battery_section(result)
    assert fields[CONF_BATTERY_CAPACITY_REPORTED] == 9.6
    assert fields[CONF_BATTERY_CAPACITY] is None


async def test_a_pack_that_reports_nothing_shows_an_empty_box(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit, capacity=0)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert _battery_section(result)[CONF_BATTERY_CAPACITY_REPORTED] is None
    # And the sensors say unknown rather than a 0.0 kWh pack.
    assert _state(hass, "battery_capacity_high_precision") == "unknown"
    assert _state(hass, "battery_charge") == "unknown"


async def test_the_reading_is_never_saved(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The form sends the read-only field back; a stored copy would freeze it."""
    entry = await _setup(hass, sungrow_unit, capacity=960)

    result = await _submit(
        hass, entry, sungrow_unit, {CONF_BATTERY_CAPACITY_REPORTED: 9.6}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_BATTERY_CAPACITY_REPORTED not in entry.options
    assert CONF_BATTERY_CAPACITY not in entry.options


async def test_the_override_feeds_the_charge_sensors(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(hass, sungrow_unit, capacity=0)

    await _submit(hass, entry, sungrow_unit, {CONF_BATTERY_CAPACITY: 14.4})

    assert entry.options[CONF_BATTERY_CAPACITY] == 14.4
    inverter = entry.runtime_data.inverter_coordinator.device
    assert inverter.derived.capacity_override_kwh == 14.4
    expected = inverter.derived.battery_charge
    assert expected is not None and expected > 0
    assert float(_state(hass, "battery_charge")) == expected
    # The register's own sensor still says what the register says.
    assert _state(hass, "battery_capacity_high_precision") == "unknown"


async def test_emptying_the_override_goes_back_to_the_register(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    entry = await _setup(
        hass, sungrow_unit, capacity=960, options={CONF_BATTERY_CAPACITY: 14.4}
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _battery_section(result)[CONF_BATTERY_CAPACITY] == 14.4
    hass.config_entries.options.async_abort(result["flow_id"])

    await _submit(hass, entry, sungrow_unit, {})

    assert CONF_BATTERY_CAPACITY not in entry.options
    derived = entry.runtime_data.inverter_coordinator.device.derived
    assert derived.capacity_override_kwh is None
