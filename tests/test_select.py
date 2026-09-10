"""Enumerations, and the fallback the YAML gets wrong.

The YAML package's selects fall back to a default option when the register
holds something their map does not know. That shows the user a mode the
inverter is not in, and hides the one case worth noticing: Sungrow adding a
value nobody has written down yet.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

EMS = "select.sh10rt_ems_mode"
EMS_ADDRESS = 13049
FORCED = "select.sh10rt_battery_forced_charge_discharge"
FORCED_ADDRESS = 13050


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    sungrow_unit.holding[EMS_ADDRESS] = 0  # self-consumption
    sungrow_unit.holding[FORCED_ADDRESS] = 0xCC  # stop
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


async def _select(hass: HomeAssistant, entity_id: str, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: option},
        blocking=True,
    )


async def test_the_register_value_maps_to_the_option_shown(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert hass.states.get(EMS).state == "self_consumption"
    assert hass.states.get(FORCED).state == "stop"


async def test_choosing_an_option_writes_the_value_the_specification_gives(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Spec reg 13050: 0 self-consumption, 2 compulsory, 3 external EMS, 4 VPP."""
    await _select(hass, EMS, "external_ems")
    assert sungrow_unit.holding[EMS_ADDRESS] == 3
    assert hass.states.get(EMS).state == "external_ems"

    await _select(hass, EMS, "vpp")
    assert sungrow_unit.holding[EMS_ADDRESS] == 4

    # And the non-contiguous one, which a range check would have got wrong.
    await _select(hass, EMS, "forced")
    assert sungrow_unit.holding[EMS_ADDRESS] == 2


async def test_the_forced_charge_codes_are_not_sequential_and_are_not_treated_as_such(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Spec reg 13051: 0xAA charge, 0xBB discharge, 0xCC stop."""
    for option, value in (("charge", 0xAA), ("discharge", 0xBB), ("stop", 0xCC)):
        await _select(hass, FORCED, option)
        assert sungrow_unit.holding[FORCED_ADDRESS] == value, option
        assert hass.states.get(FORCED).state == option


async def test_a_value_the_table_does_not_know_is_unknown_not_the_default(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """The bug this avoids, and the signal it preserves.

    The YAML falls back to its default option, which tells the user the
    inverter is in self-consumption mode when it is in something else -- and
    hides that Sungrow has added a value this table has not got.
    """
    sungrow_unit.holding[EMS_ADDRESS] = 7
    await entry.runtime_data.coordinator_for("fast_holding").async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(EMS).state == STATE_UNKNOWN


async def test_an_unavailable_register_is_unknown_too(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding[EMS_ADDRESS] = 0xFFFF
    await entry.runtime_data.coordinator_for("fast_holding").async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(EMS).state == STATE_UNKNOWN


async def test_an_option_that_is_not_offered_is_refused(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    before = sungrow_unit.holding[EMS_ADDRESS]
    with pytest.raises(ServiceValidationError):
        await _select(hass, EMS, "microgrid")
    assert sungrow_unit.holding[EMS_ADDRESS] == before


async def test_a_second_change_inside_the_debounce_window_is_still_shown(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Same ten-second cooldown as the numbers and switches."""
    for option in ("external_ems", "self_consumption", "vpp"):
        await _select(hass, EMS, option)
        assert hass.states.get(EMS).state == option


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
        await _select(hass, EMS, "vpp")


async def test_every_option_is_translatable_and_every_label_exists(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """An option with no label shows the user its slug."""
    import json
    from pathlib import Path

    from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS

    strings = json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "custom_components"
            / "sungrow_modbus"
            / "strings.json"
        ).read_text(encoding="utf-8")
    )["entity"]["select"]

    for description in SELECT_DESCRIPTIONS:
        labels = strings[description.key]["state"]
        assert set(labels) == set(description.options), description.key
        assert set(description.values) == set(description.options), description.key
