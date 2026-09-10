"""Starting and stopping the inverter, and why it is not a button.

Register 13000 is the one register in the map that turns the inverter off.
The YAML package puts it on two dashboard buttons behind a danger-mode
toggle; this integration exposes actions instead, because Home Assistant has
no confirmation dialog for a button press and an entity that stops an
inverter would appear in every dashboard picker offering exactly that.

These tests hold both halves: that the actions do write the codes the
specification gives, and that the guards a button could not have are actually
there.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import ATTR_DEVICE_ID, CONF_HOST, CONF_PORT
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
)
from homeassistant.helpers import device_registry as dr

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Register 13000, V1.1.11: 0xCF boots, 0xCE shuts down.
ADDRESS = 12999
START = 0xCF
STOP = 0xCE


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
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


def _device_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, SERIAL), entry.entry_id
    )
    assert device is not None
    return device.id


async def test_neither_start_nor_stop_is_an_entity(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The point of the whole design.

    A button entity appears in every dashboard picker and every automation
    editor, and a press has no confirmation. There must be nothing to pick.
    """
    assert [state for state in hass.states.async_all("button")] == []


async def test_the_actions_exist(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert hass.services.has_service(DOMAIN, "start_inverter")
    assert hass.services.has_service(DOMAIN, "stop_inverter")


async def test_stopping_writes_the_shutdown_code(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "stop_inverter",
        {ATTR_DEVICE_ID: _device_id(hass, entry)},
        blocking=True,
    )
    assert sungrow_unit.holding[ADDRESS] == STOP


async def test_starting_writes_the_boot_code(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "start_inverter",
        {ATTR_DEVICE_ID: _device_id(hass, entry)},
        blocking=True,
    )
    assert sungrow_unit.holding[ADDRESS] == START


async def test_a_non_admin_cannot_stop_the_inverter(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    sungrow_unit: MockModbusUnit,
    hass_read_only_user,
) -> None:
    """The guard a button could not have had.

    Registered as an admin action, so a household member with a non-admin
    login cannot call it at all -- where a button would have been pressable by
    anybody who could see the dashboard.
    """
    before = sungrow_unit.holding.get(ADDRESS)

    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
            context=Context(user_id=hass_read_only_user.id),
        )

    assert sungrow_unit.holding.get(ADDRESS) == before


async def test_a_stale_device_id_says_so(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The likeliest mistake: a script that outlived a remove-and-re-add."""
    with pytest.raises(ServiceValidationError, match="No device with ID"):
        await hass.services.async_call(
            DOMAIN, "stop_inverter", {ATTR_DEVICE_ID: "nope"}, blocking=True
        )


async def test_a_device_from_another_integration_is_refused(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    other = MockConfigEntry(domain="other", title="Something else")
    other.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, identifiers={("other", "1")}, name="Kettle"
    )

    with pytest.raises(ServiceValidationError, match="not a Sungrow Modbus device"):
        await hass.services.async_call(
            DOMAIN, "stop_inverter", {ATTR_DEVICE_ID: device.id}, blocking=True
        )


async def test_a_failed_write_is_reported_rather_than_swallowed(
    hass: HomeAssistant, entry: MockConfigEntry, sungrow_unit: MockModbusUnit
) -> None:
    with (
        patch.object(
            type(sungrow_unit),
            "write_register",
            side_effect=ModbusError("device rejected the write"),
        ),
        pytest.raises(HomeAssistantError, match="Could not stop"),
    ):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
        )


async def test_a_shutdown_is_logged_where_somebody_will_find_it(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """It is logged at warning level, so it is findable.

    Somebody working out why their inverter stopped overnight should not have
    to enable debug logging first and wait for it to happen again.
    """
    import logging

    with caplog.at_level(logging.WARNING):
        await hass.services.async_call(
            DOMAIN,
            "stop_inverter",
            {ATTR_DEVICE_ID: _device_id(hass, entry)},
            blocking=True,
        )

    assert "stop requested" in caplog.text
    assert "SH10RT" in caplog.text
