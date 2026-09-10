"""A wallbox as its own device, from the words one actually answered.

Its descriptions are hand-written -- the third module that has to be, because
`sensor_descriptions.py` is generated from the YAML package's entity map and
the package never covered a wallbox at all. So this file gives them the guard
generation gives everything else.

The fixture is the raw dump in the committed fingerprint, which is the only
wallbox reading this project has. Nothing here is invented: every number came
off an AC22E-01 through a WiNet-S at unit 3.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import CONF_UNIT_ID, DOMAIN
from custom_components.sungrow_modbus.wallbox_descriptions import (
    WALLBOX_BINARY_DESCRIPTIONS,
    WALLBOX_DESCRIPTIONS,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from sungrow_modbus.wallbox_registers import COMPONENTS

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

REPO = Path(__file__).resolve().parent.parent
FINGERPRINT = next((REPO / "doc" / "device-fingerprints").glob("*wallbox*.json"))


def _words() -> dict[str, dict[int, int]]:
    """Return what the AC22E-01 answered, by register space."""
    dump = json.loads(FINGERPRINT.read_text(encoding="utf-8"))["wallbox"][
        "register_dump"
    ]
    return {
        space: {int(a): v for a, v in values.items() if v is not None}
        for space, values in dump.items()
    }


WORDS = _words()

#: The wallbox's own unique ids. A substring match will not do: the inverter
#: has `battery_charging` and the pack has `battery_pack_voltage`, and both
#: would match a looser filter.
WALLBOX_UNIQUE_IDS = frozenset(
    f"{SERIAL}_{d.key}" for d in (*WALLBOX_DESCRIPTIONS, *WALLBOX_BINARY_DESCRIPTIONS)
)


def _wallbox_unit(unit_id: int, words: dict | None = None) -> MockModbusUnit:
    """Return a mock wallbox answering on its unit."""
    unit = MockModbusConnection().for_unit(unit_id)
    source = WORDS if words is None else words
    unit.input = dict(source.get("input", {}))
    unit.holding = dict(source.get("holding", {}))
    return unit


def _entities(hass: HomeAssistant, entry_id: str) -> list:
    """Return the registry entries that belong to the wallbox."""
    return [
        item
        for item in er.async_entries_for_config_entry(er.async_get(hass), entry_id)
        if item.unique_id in WALLBOX_UNIQUE_IDS
    ]


async def _setup(
    hass: HomeAssistant,
    inverter: MockModbusUnit,
    wallbox_at: int | None = 3,
    words: dict | None = None,
) -> MockConfigEntry:
    """Set up an entry where a wallbox answers at `wallbox_at`, or nowhere."""
    entry = MockConfigEntry(
        domain=DOMAIN, data=ENTRY_DATA, unique_id=SERIAL, title="SH10RT"
    )
    entry.add_to_hass(hass)
    empty = MockModbusConnection().for_unit(9)
    empty.input = {}
    empty.holding = {}

    def units(_hass, _entry, _params, unit_id):
        if unit_id == 1:
            return inverter
        if wallbox_at is not None and unit_id == wallbox_at:
            return _wallbox_unit(unit_id, words)
        return empty

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.mark.parametrize(
    "description",
    (*WALLBOX_DESCRIPTIONS, *WALLBOX_BINARY_DESCRIPTIONS),
    ids=lambda d: d.key,
)
def test_every_description_names_something_that_exists(description) -> None:
    """The guard generation gives the other description modules for free.

    A typo in a hand-written `field` is an `AttributeError` at the moment
    somebody's wallbox is first polled, a long way from here. Properties
    count as well as registers: a status *code* is the register and the word
    is the property, and the word is what an entity shows.
    """
    klass = COMPONENTS[description.component]
    declared = description.field in vars(klass)
    computed = isinstance(getattr(klass, description.field, None), property)
    assert declared or computed, (
        f"{description.key} reads {description.component}.{description.field}, "
        "which is neither a field nor a property"
    )


def test_no_raw_code_and_no_unnamed_register_becomes_an_entity() -> None:
    """Three kinds of register are read and deliberately not published.

    The `_raw` codes, whose decoded properties are the entities. Register
    21313, which nobody in any of the four sources can name. And the two
    session timestamps, which hold the wallbox's *local* time in an
    epoch-shaped number -- a `timestamp` entity needs a real instant and this
    project does not know the device's zone.
    """
    fields = {d.field for d in (*WALLBOX_DESCRIPTIONS, *WALLBOX_BINARY_DESCRIPTIONS)}

    assert not {field for field in fields if field.endswith("_raw")}, (
        "a raw code has a decoded property; the property is the entity"
    )
    assert "unnamed_register_21313" not in fields
    assert not {"charging_started", "charging_ended"} & fields
    # But the library still reads all of them, so the survey carries them.
    read = {name for klass in COMPONENTS.values() for name in klass.declared_fields}
    assert "unnamed_register_21313" in read
    assert {"charging_started", "charging_ended"} <= read


async def test_a_wallbox_that_answers_becomes_its_own_device(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Named from its own type code, and hung off the inverter.

    `via_device` is not decoration here: a wallbox is reachable *only*
    through the endpoint the inverter is on -- measured, a full sweep of a /24
    found it on no address of its own -- so the inverter really is how you
    get to it.
    """
    entry = await _setup(hass, sungrow_unit)
    assert entry.state is ConfigEntryState.LOADED

    registry = dr.async_get(hass)
    wallbox = registry.async_get_device_by_identifier(
        (DOMAIN, f"{SERIAL}-wallbox"), entry.entry_id
    )
    assert wallbox is not None
    assert wallbox.manufacturer == "Sungrow"
    assert wallbox.model == "AC22E-01"
    assert wallbox.name == "AC22E-01"

    inverter = registry.async_get_device_by_identifier((DOMAIN, SERIAL), entry.entry_id)
    assert inverter is not None
    assert wallbox.via_device_id == inverter.id


async def test_the_wallbox_reports_what_it_read(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The values, end to end, from register words to entity states."""
    entry = await _setup(hass, sungrow_unit)
    # Keyed by the description's own key, not by a fragment of the entity id.
    # `charging_power` is a substring of `maximum_charging_power` and
    # `minimum_charging_power`, so a substring match compared whichever came
    # first -- and would have passed had the numbers been closer.
    readings = {
        item.unique_id.removeprefix(f"{SERIAL}_"): state.state
        for item in _entities(hass, entry.entry_id)
        if (state := hass.states.get(item.entity_id))
    }
    assert readings, "no wallbox entities were created"

    def one(key: str) -> str:
        assert key in readings, (key, sorted(readings))
        return readings[key]

    # The session had finished when this was read, which is why the power is
    # zero and the status is not idle -- the distinction only a source with
    # the whole code table can make.
    assert one("wallbox_charging_status") == "completed"
    assert float(one("wallbox_charging_power")) == 0
    assert float(one("wallbox_session_energy")) == 105
    assert float(one("wallbox_lifetime_energy")) == 280557
    assert float(one("wallbox_available_current")) == pytest.approx(16.1)
    assert float(one("wallbox_control_pilot_voltage")) == pytest.approx(9.04)
    assert one("wallbox_firmware_version") == "LE-01.1E1.001."
    assert float(one("wallbox_output_current_setting")) == pytest.approx(15.1)
    # 22080 W is 32 A on three phases at 230 V, which is the 22 in AC22E-01.
    assert float(one("wallbox_maximum_charging_power")) == 22080


def _charging_state(hass: HomeAssistant, entry_id: str) -> str | None:
    """Return the state of the wallbox's `charging` binary sensor."""
    for item in _entities(hass, entry_id):
        if item.unique_id == f"{SERIAL}_wallbox_charging":
            state = hass.states.get(item.entity_id)
            return state.state if state else None
    return None


async def test_a_completed_session_is_not_charging(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """What the one real reading holds: status 6, *completed*.

    Off, and the power is zero too -- so a power-derived sensor would agree
    here by luck. The next test is the one that separates them.
    """
    entry = await _setup(hass, sungrow_unit)
    assert WORDS["input"][21316] == 6, "the reading this project actually has"
    assert _charging_state(hass, entry.entry_id) == "off"


async def test_charging_is_read_from_the_status_and_not_from_the_power(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """A vehicle that has stopped drawing still counts as charging.

    Status 3 with the power left at 0, which is a real state: a car that has
    paused mid-session draws nothing and the charge point still considers the
    session live. A sensor derived from `charging_power` would report off
    here, and the difference matters to anybody automating on it.
    """
    words = {space: dict(values) for space, values in WORDS.items()}
    words["input"][21316] = 3
    assert words["input"][21307] == 0, "power stays zero, which is the point"

    entry = await _setup(hass, sungrow_unit, words=words)
    assert _charging_state(hass, entry.entry_id) == "on"


async def test_no_wallbox_means_no_wallbox_entities(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The common case, and it must not fail the entry.

    Most installations have no Sungrow wallbox. Nothing about the inverter
    changes either way.
    """
    entry = await _setup(hass, sungrow_unit, wallbox_at=None)

    assert entry.state is ConfigEntryState.LOADED
    assert _entities(hass, entry.entry_id) == []
    assert (
        dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, f"{SERIAL}-wallbox"), entry.entry_id
        )
        is None
    )


async def test_a_device_answering_zeros_is_not_taken_for_a_wallbox(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The failure mode that sits between us and the hardware.

    A WiNet-S answers 0 for a measuring point it does not forward, and a
    model name of five zero words decodes to an empty string. Taking that as
    a wallbox would create twenty-one entities reporting nothing for the life
    of the install, which is what `ZERO_MEANS_ABSENT` exists to prevent one
    layer up.
    """
    zeros = {"input": dict.fromkeys(range(21215, 21340), 0), "holding": {}}
    entry = await _setup(hass, sungrow_unit, words=zeros)

    assert entry.state is ConfigEntryState.LOADED
    assert _entities(hass, entry.entry_id) == []
