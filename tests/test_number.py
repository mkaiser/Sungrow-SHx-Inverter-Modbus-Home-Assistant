"""Writing a setting, and seeing the result.

The YAML package needed three pieces for one setting: a `template number`, a
`modbus.write_register` action, and a `homeassistant.update_entity` call
afterwards -- because YAML Modbus has no write-then-read, so without the last
step the user set a value and the interface showed the old one until the next
poll. These assert the integration does it in one, and that the arithmetic the
templates got to do by hand is now the library's job.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

MIN_SOC = "number.sh10rt_battery_min_soc"


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    """Set up the integration against the mock inverter."""
    # 10.0 % and 90.0 %, at the register's 0.1 % per count.
    sungrow_unit.holding[13058] = 100
    sungrow_unit.holding[13057] = 900
    sungrow_unit.holding[13099] = 15

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


async def _set(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


async def test_the_settings_exist_with_the_bounds_from_the_specification(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    state = hass.states.get(MIN_SOC)
    assert state is not None
    assert float(state.state) == 10.0
    # Spec reg 13059: 0.0~50.0. A minimum SoC above 50 is not a thing the
    # inverter accepts, so the interface must not offer it.
    assert state.attributes["min"] == 0
    assert state.attributes["max"] == 50
    assert state.attributes["step"] == 1
    assert state.attributes["unit_of_measurement"] == "%"

    maximum = hass.states.get("number.sh10rt_battery_max_soc")
    assert float(maximum.state) == 90.0
    assert maximum.attributes["min"] == 50
    assert maximum.attributes["max"] == 100


async def test_writing_applies_the_register_scale(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """20 % must reach the wire as 200, and the library must be what knows it.

    The YAML template wrote `{{ value | int * 10 }}`, which is the scale
    spelled out by hand in a place nothing checks it. Here the field carries
    its own scale.
    """
    await _set(hass, MIN_SOC, 20)

    assert sungrow_unit.holding[13058] == 200
    # And a half-percent still lands correctly, which an integer template
    # would have truncated.
    await _set(hass, MIN_SOC, 12.5)
    assert sungrow_unit.holding[13058] == 125


async def test_a_whole_percent_register_is_written_unscaled(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Reserved SoC is whole percent, not tenths -- getting this wrong is 10x."""
    await _set(hass, "number.sh10rt_battery_reserved_soc_for_backup", 30)
    assert sungrow_unit.holding[13099] == 30


async def test_the_new_value_is_visible_without_waiting_for_the_next_poll(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The whole reason the YAML's readback automations are deleted, not ported."""
    assert float(hass.states.get(MIN_SOC).state) == 10.0

    await _set(hass, MIN_SOC, 25)

    # No time has passed and no poll has fired; the entity refreshed itself.
    assert float(hass.states.get(MIN_SOC).state) == 25.0


async def test_a_value_the_inverter_clamps_is_shown_as_clamped(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """Showing what was asked for rather than what was accepted is the bug.

    An inverter may take a value and store something else. The refresh is how
    the user finds that out.
    """

    async def clamp(address: int, value: int) -> None:
        sungrow_unit.holding[address] = min(value, 300)

    # A single 16-bit register is written with function code 6.
    with patch.object(type(sungrow_unit), "write_register", side_effect=clamp):
        await _set(hass, MIN_SOC, 45)

    assert sungrow_unit.holding[13058] == 300
    assert float(hass.states.get(MIN_SOC).state) == 30.0


async def test_a_value_outside_the_bounds_is_refused_before_it_is_sent(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    before = sungrow_unit.holding[13058]
    with pytest.raises(ServiceValidationError):
        await _set(hass, MIN_SOC, 80)
    assert sungrow_unit.holding[13058] == before


async def test_a_failed_write_is_reported_rather_than_swallowed(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    """A setting that silently did not apply is worse than an error."""
    with (
        patch.object(
            type(sungrow_unit),
            "write_register",
            side_effect=ModbusError("device rejected the write"),
        ),
        pytest.raises(HomeAssistantError, match="Could not write"),
    ):
        await _set(hass, MIN_SOC, 20)


async def test_the_settings_are_configuration_not_measurements(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    written = registry.async_get(MIN_SOC)
    assert written.entity_category is er.EntityCategory.CONFIG


async def test_a_second_change_inside_the_debounce_window_is_still_shown(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Same reason as the switches: the debouncer's cooldown is ten seconds.

    A setting changed twice in quick succession would otherwise show its
    previous value for up to ten seconds -- the readback problem the YAML
    package needed a whole extra action to work around.
    """
    for value in (20, 30, 15):
        await _set(hass, MIN_SOC, value)
        assert float(hass.states.get(MIN_SOC).state) == float(value)
