"""The SBR pack as its own device, and the two gates in front of its entities.

Its descriptions are the only hand-written ones in the integration --
`sensor_descriptions.py` is generated from the YAML package's entity map, and
the pack's registers are not in it, because they live in
`legacy/additional_sensors/`, an opt-in file a user copies in by hand. So the
guard that generation gives everything else has to be written here instead.

The two gates are the substance. A pack answers or it does not, and
*separately* its cell block answers or it does not -- measured on one SBR096
read both ways within seconds, where a WiNet-S refused the cell block with
exception 0x02 while the pack block answered identical values, and at a
second house a different dongle firmware answered that block with **zeros**.
Zeros are the dangerous one: they decode to values, and nothing ever removes
an entity.
"""

from __future__ import annotations

from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.battery_descriptions import (
    BATTERY_DESCRIPTIONS,
    CELL_DESCRIPTIONS,
    PACK_DESCRIPTIONS,
)
from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from sungrow_modbus.battery_registers import SbrBatteryCells, SbrBatteryPack

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: What one SBR096 said at unit 200 on 2026-09-09, over the inverter's own LAN
#: port -- the only path that answers the cell block at all.
PACK_WORDS = {
    10740: 2000,
    10741: 1,
    10742: 217,
    10743: 1000,
    10744: 96,
    10745: 58023,
    10746: 0,
    10747: 54276,
    10748: 0,
}
CELL_WORDS = {
    10756: 33507,
    10757: 260,
    10758: 33436,
    10759: 275,
    10760: 222,
    10761: 770,
    10762: 211,
    10763: 257,
}


#: The pack's own unique ids, which is how its entities are told from the
#: inverter's. A substring match does not work: the inverter has
#: `battery_charging` and `battery_level` of its own.
PACK_UNIQUE_IDS = frozenset(f"{SERIAL}_{d.key}" for d in BATTERY_DESCRIPTIONS)


def _pack_entities(hass: HomeAssistant, entry_id: str) -> list:
    """Return the registry entries that belong to the pack."""
    return [
        item
        for item in er.async_entries_for_config_entry(er.async_get(hass), entry_id)
        if item.unique_id in PACK_UNIQUE_IDS
    ]


def _pack(words: dict[int, int]) -> MockModbusUnit:
    """Return a mock unit answering as a pack on its own unit id."""
    unit = MockModbusConnection().for_unit(200)
    unit.input = dict(words)
    unit.holding = {}
    return unit


#: Register 5639's address, where the **inverter** reports the pack's size.
#:
#: The pack does not report its own capacity anywhere in its seventeen
#: registers -- checked, the whole 10740-10789 band was read -- so the model
#: name comes from the inverter's view of it. 960 is 9.6 kWh, an SBR096.
CAPACITY_ADDRESS = 5638


async def _setup(
    hass: HomeAssistant,
    inverter: MockModbusUnit,
    pack: MockModbusUnit | None,
    capacity: int | None = 960,
) -> MockConfigEntry:
    """Set up an entry where unit 200 answers as `pack`, or answers nothing."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    if capacity is not None:
        inverter.input[CAPACITY_ADDRESS] = capacity

    def units(_hass, _entry, _params, unit_id):
        # The real `async_get_unit` hands out a handle per unit id on one
        # shared connection, which is what makes a pack reachable without a
        # second Modbus session -- a Sungrow accepts very few at once.
        if unit_id == 1:
            return inverter
        if pack is not None and unit_id == 200:
            return pack
        return _pack({})

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize("description", BATTERY_DESCRIPTIONS, ids=lambda d: d.key)
def test_every_description_names_a_field_that_exists(description) -> None:
    """The guard generation gives the other descriptions for free.

    A typo in a hand-written `field` is an `AttributeError` at the moment
    somebody's battery is first polled, which is a long way from here.
    Properties count as well as registers: the packed position words become
    a module and a cell through properties on the component, and those are
    the values worth having.
    """
    components = {"pack": SbrBatteryPack, "cells": SbrBatteryCells}
    klass = components[description.component]
    declared = description.field in vars(klass)
    computed = isinstance(getattr(klass, description.field, None), property)
    assert declared or computed, (
        f"{description.key} reads {description.component}.{description.field}, "
        "which is neither a field nor a property"
    )


def test_no_key_collides_with_one_of_the_inverters() -> None:
    """The unique id is the inverter's serial plus the key, for both devices.

    So a key shared between the pack and the inverter would be two entities
    claiming one unique_id, and Home Assistant would drop whichever lost the
    race. Nothing prefixes them apart -- an extra `battery_` was tried and
    removed, because every key here already starts with `battery_` while the
    inverter has `battery_charging` and `battery_level` of its own, which
    left the two sets indistinguishable by prefix.
    """
    from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS

    keys = [d.key for d in BATTERY_DESCRIPTIONS]
    assert len(keys) == len(set(keys)), "a key is repeated within the pack's own"
    shared = set(keys) & {d.key for d in SENSOR_DESCRIPTIONS}
    assert not shared, f"these keys exist on both devices: {sorted(shared)}"


async def test_a_pack_that_answers_becomes_its_own_device(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Its own device, hung off the inverter rather than merged into it.

    Its own hardware, its own firmware, and its own failure: a dongle can
    lose the pack's cell block while the inverter answers everything. The
    identifier is the inverter's serial with a suffix, because an SBR reports
    no serial of its own -- the whole 10740-10789 band was read and there is
    none in it.
    """
    entry = await _setup(hass, sungrow_unit, _pack({**PACK_WORDS, **CELL_WORDS}))
    assert entry.state is ConfigEntryState.LOADED

    registry = dr.async_get(hass)
    pack = registry.async_get_device_by_identifier(
        (DOMAIN, f"{SERIAL}-battery"), entry.entry_id
    )
    assert pack is not None
    assert pack.manufacturer == "Sungrow"
    # Named from the capacity the *inverter* reports, since the pack does not
    # report its own size anywhere in its registers.
    assert pack.model == "SBR096"
    assert pack.name == "SBR096"

    inverter = registry.async_get_device_by_identifier((DOMAIN, SERIAL), entry.entry_id)
    assert inverter is not None
    assert pack.via_device_id == inverter.id, "the pack belongs under the inverter"


async def test_the_pack_reports_what_it_read(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The values, end to end, from register words to entity states."""
    await _setup(hass, sungrow_unit, _pack({**PACK_WORDS, **CELL_WORDS}))

    entry = next(iter(hass.config_entries.async_entries(DOMAIN)))
    readings = {
        item.entity_id: state.state
        for item in _pack_entities(hass, entry.entry_id)
        if (state := hass.states.get(item.entity_id))
    }
    assert readings, "no battery entities were created"

    def one(fragment: str) -> str:
        matches = [v for k, v in readings.items() if fragment in k]
        assert len(matches) == 1, (fragment, sorted(readings))
        return matches[0]

    assert float(one("pack_voltage")) == pytest.approx(200.0)
    assert float(one("pack_level")) == pytest.approx(100.0)
    assert float(one("pack_state_of_health")) == pytest.approx(96)
    assert float(one("highest_cell_voltage")) == pytest.approx(3.3507)
    # The unpacked halves: 260 is 0x0104, so module 1 and cell 4 -- and the
    # reading that proves the encoding is in `SbrBatteryCells`.
    assert int(float(one("highest_cell_module"))) == 1
    assert int(float(one("highest_cell_number"))) == 4


async def test_no_pack_means_no_battery_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The common case, and it must not fail the entry.

    Most installations have no Sungrow pack. The inverter's own battery
    entities are unaffected either way -- those read the inverter's view of a
    battery, which is a different set of registers on a different unit.
    """
    entry = await _setup(hass, sungrow_unit, None)

    assert entry.state is ConfigEntryState.LOADED
    assert _pack_entities(hass, entry.entry_id) == []
    # And no orphan device.
    assert (
        dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, f"{SERIAL}-battery"), entry.entry_id
        )
        is None
    )


async def test_a_cell_block_of_zeros_creates_no_cell_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Measured at bar12: one dongle firmware answers this block with zeros.

    The read succeeds, so a gate on "did it answer" would pass, and every
    cell entity would then report 0 V and module 0 for the life of the
    install -- with no recovery, because nothing ever removes an entity. The
    pack summary must still be created, because it read true.
    """
    entry = await _setup(
        hass,
        sungrow_unit,
        _pack({**PACK_WORDS, **dict.fromkeys(CELL_WORDS, 0)}),
    )
    assert entry.state is ConfigEntryState.LOADED

    created = {
        item.unique_id.removeprefix(f"{SERIAL}_")
        for item in _pack_entities(hass, entry.entry_id)
    }
    assert created == {d.key for d in PACK_DESCRIPTIONS}, (
        "the pack summary read true and must exist"
    )
    assert not created & {d.key for d in CELL_DESCRIPTIONS}, (
        "a block of zeros is not evidence of cell data"
    )


async def test_a_pack_whose_size_the_inverter_does_not_report_is_still_a_device(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """It is called "Battery", and its entities exist all the same.

    The model name comes from register 5639 on the *inverter*, so a pack is
    nameable only where that reads a capacity matching the datasheet table --
    and a third-party pack reports 0 there, which is how `battery-thirdparty`
    is told from `battery-sbr096` in a fingerprint's filename. What must not
    happen is the readings being withheld because the name could not be
    derived: these are the pack's own registers, and they read the same
    whatever the table says.
    """
    entry = await _setup(
        hass,
        sungrow_unit,
        _pack({**PACK_WORDS, **CELL_WORDS}),
        capacity=None,
    )
    assert entry.state is ConfigEntryState.LOADED

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{SERIAL}-battery"), entry.entry_id
    )
    assert device is not None
    assert device.model == "Battery"
    assert len(_pack_entities(hass, entry.entry_id)) == len(BATTERY_DESCRIPTIONS)
