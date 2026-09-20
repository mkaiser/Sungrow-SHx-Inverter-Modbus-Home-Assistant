"""Holding this entry's polling off while a survey or control test runs.

Everything on one config entry shares one serialized connection to one
endpoint, and a Sungrow grants very few sessions. So a survey taken while the
tiers keep firing measures the inverter *and* the contention it is causing --
which every document published from a device page before 2026-09-18 admitted,
in a field that said `coordinators_paused: false` because it was hardcoded.

What these pin is mostly about giving it back. A pause that leaks is an entry
that has silently stopped polling, which looks exactly like the integration
having died, and would be a far worse bug than the one it fixes.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


@pytest.fixture
async def entry(hass: HomeAssistant, sungrow_unit: MockModbusUnit) -> MockConfigEntry:
    """Set up the integration against the mock inverter."""
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


async def test_a_paused_coordinator_reads_no_register(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The whole point: while paused, nothing here touches the wire."""
    runtime = entry.runtime_data
    coordinator = next(iter(runtime.coordinators.values()))

    # The poll is replaced by something that fails loudly if it is reached, so
    # this asserts the absence of a read rather than counting them.
    with patch.object(
        coordinator, "_poll", side_effect=AssertionError("polled while paused")
    ):
        async with runtime.async_paused():
            await coordinator.async_refresh()
        assert coordinator.last_update_success

        # And the guard really does fire once the pause is over, which is what
        # makes the assertion above mean anything.
        await coordinator.async_refresh()
    assert not coordinator.last_update_success


async def test_a_paused_coordinator_keeps_its_values(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Entities hold what they had rather than going unavailable.

    A pause is "these readings are a little old", not "this inverter is gone".
    Reporting `UpdateFailed` instead would blank every sensor on the device
    page for the length of a run, which is minutes.
    """
    runtime = entry.runtime_data
    coordinator = next(iter(runtime.coordinators.values()))
    before = coordinator.data

    async with runtime.async_paused():
        await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data is before


async def test_polling_resumes_when_the_run_raises(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The failure mode that would be worse than the problem.

    A survey that raises must not leave the entry permanently quiet, so the
    flag is cleared in a `finally` rather than after the body.
    """
    runtime = entry.runtime_data

    with pytest.raises(RuntimeError):
        async with runtime.async_paused():
            assert runtime.polling_paused
            raise RuntimeError("the survey fell over")

    assert not runtime.polling_paused


async def test_polling_resumes_when_the_run_is_cancelled(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Home Assistant cancels a background task on unload and on shutdown."""
    import asyncio

    runtime = entry.runtime_data

    with pytest.raises(asyncio.CancelledError):
        async with runtime.async_paused():
            raise asyncio.CancelledError

    assert not runtime.polling_paused


async def test_every_coordinator_on_the_entry_is_covered(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Pausing only the inverter's tiers would not be a pause.

    The battery pack and the wallbox are separate coordinator classes on
    separate unit ids, but the same host, port and serialized connection --
    and they are the two most likely to be on a slow path behind a dongle.
    """
    from custom_components.sungrow_modbus.coordinator import (
        PausableCoordinator,
        SungrowBatteryCoordinator,
        SungrowDataUpdateCoordinator,
        SungrowWallboxCoordinator,
    )

    for cls in (
        SungrowDataUpdateCoordinator,
        SungrowBatteryCoordinator,
        SungrowWallboxCoordinator,
    ):
        assert issubclass(cls, PausableCoordinator), cls.__name__


async def test_the_document_says_whether_it_was_paused(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """And it is read from the entry rather than asserted as a constant.

    The field existed before the pause did, saying `false`, which was true.
    A reader of an old document must still be able to trust it.
    """
    from custom_components.sungrow_modbus.fingerprint import async_build

    runtime = entry.runtime_data

    async with runtime.async_paused():
        document = await async_build(hass, entry)
    assert document["contention"]["coordinators_paused"] is True

    document = await async_build(hass, entry)
    assert document["contention"]["coordinators_paused"] is False
