"""One wallbox, one device: its own address first, the dongle only without one.

A wallbox with a network connection of its own is an entry of its own, over
TLS at unit 248. An inverter entry that finds the same wallbox at unit 3
behind its WiNet-S leaves it to that entry, removes the sub-device it made
before, and takes it back when that entry is deleted. The wallbox address
option an inverter entry once had is gone, with no migration of its device.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_RESTART,
    CONF_UNIT_ID,
    DOMAIN,
    WALLBOX_TLS_UNIT,
)
from custom_components.sungrow_modbus.entry_migration import (
    MINOR_VERSION,
    async_migrate_entry,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import SERIAL
from .test_wallbox_entities import WORDS, _wallbox_unit
from .test_wallbox_entry import DATA, WALLBOX_SERIAL, _serial_words

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}
WALLBOX_DEVICE = (DOMAIN, f"{SERIAL}-wallbox")


@pytest.fixture(autouse=True)
def _open_the_alpha_gate(devices_mode_offered: None) -> None:
    """Open the gate on the devices path, which the alpha shuts."""


def _words() -> dict[str, dict[int, int]]:
    return {**WORDS, "input": {**WORDS["input"], **_serial_words(WALLBOX_SERIAL)}}


class _Units:
    """Stand in for `async_get_unit`: the inverter, and the wallbox two ways."""

    def __init__(self, inverter: MockModbusUnit) -> None:
        self.inverter = inverter
        self.dongle = _wallbox_unit(3, _words())
        self.direct = _wallbox_unit(WALLBOX_TLS_UNIT, _words())
        self.empty = MockModbusConnection().for_unit(9)
        self.empty.input = {}
        self.empty.holding = {}

    def __call__(self, _hass: Any, _entry: Any, params: Any, unit_id: int) -> Any:
        if type(params).__name__ == "ModbusTlsParams":
            return self.direct if unit_id == WALLBOX_TLS_UNIT else self.empty
        if unit_id == 1:
            return self.inverter
        return self.dongle if unit_id == 3 else self.empty


def _inverter_entry(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
        minor_version=MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    return entry


def _wallbox_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=DATA,
        unique_id=WALLBOX_SERIAL,
        title="AC22E-01",
        minor_version=MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    return entry


async def _set_up(hass: HomeAssistant, units: _Units, *entries: MockConfigEntry):
    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        for entry in entries:
            # The first setup loads the integration, which sets up every
            # entry already added; only the ones still waiting are asked.
            if entry.state is ConfigEntryState.NOT_LOADED:
                assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _sub_device(hass: HomeAssistant, entry: MockConfigEntry) -> bool:
    """Whether the inverter entry has its wallbox sub-device."""
    registry = dr.async_get(hass)
    return (
        registry.async_get_device_by_identifier(WALLBOX_DEVICE, entry.entry_id)
        is not None
    )


async def test_without_an_entry_of_its_own_the_dongle_carries_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    inverter = _inverter_entry(hass)
    await _set_up(hass, _Units(sungrow_unit), inverter)

    assert inverter.runtime_data.wallbox is not None
    assert inverter.runtime_data.wallbox_elsewhere is None
    assert _sub_device(hass, inverter)


async def test_an_inverter_entry_leaves_a_wallbox_to_its_own_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Both set up: the wallbox is one device, its own entry's."""
    units = _Units(sungrow_unit)
    wallbox = _wallbox_entry(hass)
    inverter = _inverter_entry(hass)
    await _set_up(hass, units, wallbox, inverter)

    assert wallbox.state is ConfigEntryState.LOADED
    assert inverter.state is ConfigEntryState.LOADED
    assert inverter.runtime_data.wallbox is None
    assert inverter.runtime_data.wallbox_elsewhere == WALLBOX_SERIAL
    assert not _sub_device(hass, inverter)
    own = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{WALLBOX_SERIAL}-wallbox"), wallbox.entry_id
    )
    assert own is not None
    assert own.config_entry_id == wallbox.entry_id


async def test_adding_the_wallbox_entry_takes_it_from_the_inverter_entry(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """No restart needed: the inverter entry reloads and gives it up."""
    units = _Units(sungrow_unit)
    inverter = _inverter_entry(hass)
    await _set_up(hass, units, inverter)
    assert _sub_device(hass, inverter)

    wallbox = _wallbox_entry(hass)
    await _set_up(hass, units, wallbox)

    assert inverter.state is ConfigEntryState.LOADED
    assert inverter.runtime_data.wallbox is None
    assert not _sub_device(hass, inverter)


async def test_deleting_the_wallbox_entry_hands_it_back_to_the_dongle(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    units = _Units(sungrow_unit)
    wallbox = _wallbox_entry(hass)
    inverter = _inverter_entry(hass)
    await _set_up(hass, units, wallbox, inverter)
    assert inverter.runtime_data.wallbox is None

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        assert await hass.config_entries.async_remove(wallbox.entry_id)
        await hass.async_block_till_done()

    assert inverter.state is ConfigEntryState.LOADED
    assert inverter.runtime_data.wallbox is not None
    assert inverter.runtime_data.wallbox_elsewhere is None


async def test_the_migration_drops_the_wallbox_options_and_their_device(
    hass: HomeAssistant,
) -> None:
    """Minor version 3: the address option, the leave and the cap go."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        unique_id=SERIAL,
        data=ENTRY_DATA,
        options={
            "wallbox_host": "192.0.2.23",
            "capability_test_wallbox": True,
            "wallbox_max_amps": 16,
            CONF_CAPABILITY_TEST_RESTART: False,
        },
    )
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={WALLBOX_DEVICE}
    )

    assert await async_migrate_entry(hass, entry)

    assert entry.minor_version == MINOR_VERSION
    assert entry.options == {CONF_CAPABILITY_TEST_RESTART: False}
    assert not _sub_device(hass, entry)


async def test_the_migration_keeps_a_dongle_wallbox_and_a_wallbox_entry(
    hass: HomeAssistant,
) -> None:
    """No address option, no device removed; a wallbox entry keeps its leave."""
    inverter = MockConfigEntry(
        domain=DOMAIN, version=1, minor_version=2, unique_id=SERIAL, data=ENTRY_DATA
    )
    inverter.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=inverter.entry_id, identifiers={WALLBOX_DEVICE}
    )
    wallbox = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=2,
        unique_id=WALLBOX_SERIAL,
        data=DATA,
        options={"capability_test_wallbox": True, "wallbox_max_amps": 16},
    )
    wallbox.add_to_hass(hass)

    assert await async_migrate_entry(hass, inverter)
    assert await async_migrate_entry(hass, wallbox)

    assert _sub_device(hass, inverter)
    assert wallbox.options == {
        "capability_test_wallbox": True,
        "wallbox_max_amps": 16,
    }
    assert wallbox.minor_version == MINOR_VERSION


async def test_an_inverter_entry_offers_no_wallbox_fields(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    inverter = _inverter_entry(hass)
    await _set_up(hass, _Units(sungrow_unit), inverter)

    result = await hass.config_entries.options.async_init(inverter.entry_id)

    fields = {
        str(key)
        for section in result["data_schema"].schema.values()
        for key in getattr(getattr(section, "schema", None), "schema", {})
    }
    assert fields
    assert not fields & {"wallbox_host", "capability_test_wallbox", "wallbox_max_amps"}
