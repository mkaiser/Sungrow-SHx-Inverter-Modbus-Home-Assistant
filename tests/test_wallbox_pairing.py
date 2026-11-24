"""The owner names the inverter that manages a wallbox entry.

An inverter entry on its own LAN cable never sees the wallbox on its bus -- a
wallbox answers at unit 3 only behind a WiNet-S -- so nothing it reads can tie
it to the wallbox's own entry. gerd's is exactly that: the inverter on its
cable, the AC22E-01 over TLS at its own address. The wallbox entry's
**Configure** asks which inverter manages it (`CONF_WALLBOX_MANAGED_BY`), and
the named inverter entry treats the wallbox as left to its own entry, the way
the dongle path does (`wallbox_elsewhere`). Everything that hangs off that --
`managing_entry`, `has_wallbox`, the EV charger controls -- then follows.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_ENTITY_IDS,
    CONF_UNIT_ID,
    CONF_WALLBOX_MANAGED_BY,
    CONF_WALLBOX_STANDALONE,
    DOMAIN,
    ENTITY_IDS_NEW,
    WALLBOX_TLS_PORT,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from sungrow_modbus.wallbox import management
from sungrow_modbus.wallbox.plausibility import LOAD_INCLUDES

from .conftest import SERIAL, encode_string
from .test_wallbox_entry import DATA, WALLBOX_SERIAL, _wallbox

INVERTER = {CONF_HOST: "127.0.0.1", CONF_PORT: 502, CONF_UNIT_ID: 1}
OTHER_SERIAL = "B987654321"


@pytest.fixture(autouse=True)
def _units(sungrow_unit: MockModbusUnit):
    """Over TLS the wallbox; to each inverter entry its own inverter.

    An inverter answers nothing at unit 3, as one on its own cable never shows
    a wallbox.
    """
    wallbox = _wallbox()
    other = MockModbusConnection().for_unit(1)
    other.input = {**sungrow_unit.input, 4989: encode_string(OTHER_SERIAL, 10)}
    other.holding = dict(sungrow_unit.holding)
    inverters = {SERIAL: sungrow_unit, OTHER_SERIAL: other}

    def unit_for(_hass, entry, params, _unit_id):
        # By port, not by unit: an inverter entry also asks its own endpoint
        # for unit 248, the wallbox's id over TLS.
        if params.port == WALLBOX_TLS_PORT:
            return wallbox
        return inverters[entry.unique_id]

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=unit_for):
        yield


async def _set_up(
    hass: HomeAssistant, *serials: str
) -> tuple[list[MockConfigEntry], MockConfigEntry]:
    """Set up inverter entries on their cable, then the wallbox's own entry."""
    inverters = []
    for serial in serials:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={**INVERTER, CONF_ENTITY_IDS: ENTITY_IDS_NEW},
            unique_id=serial,
            title=f"SH10RT {serial[-3:]}",
        )
        entry.add_to_hass(hass)
        inverters.append(entry)
    wallbox_entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id=WALLBOX_SERIAL)
    wallbox_entry.add_to_hass(hass)
    for entry in (*inverters, wallbox_entry):
        # The first setup loads the integration, and with it every entry.
        if entry.state is not ConfigEntryState.LOADED:
            assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert all(e.state is ConfigEntryState.LOADED for e in (*inverters, wallbox_entry))
    return inverters, wallbox_entry


async def _answer(
    hass: HomeAssistant, wallbox_entry: MockConfigEntry, **answers: object
) -> dict:
    result = await hass.config_entries.options.async_init(wallbox_entry.entry_id)
    assert result["step_id"] == "wallbox"
    done = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "capability_test": {CONF_CAPABILITY_TEST_WALLBOX: True, **answers},
            "diagnosis": {"publish_address": False},
        },
    )
    await hass.async_block_till_done()
    return done


def _offered(result: dict) -> list[str]:
    schema = result["data_schema"].schema["capability_test"].schema.schema
    for key, selector in schema.items():
        if key == CONF_WALLBOX_MANAGED_BY:
            return [option["value"] for option in selector.config["options"]]
    raise AssertionError("the question is not asked")


async def test_the_question_offers_the_inverter_entries_and_nothing_else(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    _, wallbox_entry = await _set_up(hass, SERIAL, OTHER_SERIAL)

    result = await hass.config_entries.options.async_init(wallbox_entry.entry_id)

    # Both inverters; never the wallbox itself.
    assert sorted(_offered(result)) == sorted([SERIAL, OTHER_SERIAL])


async def test_an_inverter_on_its_cable_manages_nothing_until_it_is_named(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)

    assert inverter.runtime_data.wallbox_elsewhere is None
    assert not inverter.runtime_data.has_wallbox
    assert wbt.managing_entry(hass, wallbox_entry) is None


async def test_naming_the_inverter_pairs_the_two_entries(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)

    done = await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})

    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert wallbox_entry.options[CONF_WALLBOX_MANAGED_BY] == SERIAL
    # The inverter was set up anew and now holds the wallbox as left to its
    # own entry, which is what the managed test and the controls look for.
    assert inverter.runtime_data.wallbox_elsewhere == WALLBOX_SERIAL
    assert inverter.runtime_data.has_wallbox
    assert wbt.managing_entry(hass, wallbox_entry) is inverter
    assert wbt.check_options(wallbox_entry, hass)["managed"]


async def test_moving_the_answer_moves_the_pairing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    (first, second), wallbox_entry = await _set_up(hass, SERIAL, OTHER_SERIAL)
    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})

    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: OTHER_SERIAL})

    # Both inverters were set up anew: the one named before lets go.
    assert first.runtime_data.wallbox_elsewhere is None
    assert second.runtime_data.wallbox_elsewhere == WALLBOX_SERIAL
    assert wbt.managing_entry(hass, wallbox_entry) is second


async def test_leaving_it_empty_takes_the_answer_back(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)
    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})

    await _answer(hass, wallbox_entry)

    assert CONF_WALLBOX_MANAGED_BY not in wallbox_entry.options
    assert inverter.runtime_data.wallbox_elsewhere is None
    assert wbt.managing_entry(hass, wallbox_entry) is None


async def test_standalone_and_managed_at_once_is_refused(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Two answers that contradict each other: neither is stored."""
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)

    result = await _answer(
        hass,
        wallbox_entry,
        **{CONF_WALLBOX_STANDALONE: True, CONF_WALLBOX_MANAGED_BY: SERIAL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "wallbox_standalone_and_managed"}
    assert CONF_WALLBOX_MANAGED_BY not in wallbox_entry.options
    assert inverter.runtime_data.wallbox_elsewhere is None


async def test_saving_the_same_answer_again_leaves_the_inverter_running(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Only a change of the answer sets an inverter up anew, not the test's cap."""
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)
    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})
    running = inverter.runtime_data

    await _answer(
        hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL, "wallbox_max_amps": 16}
    )

    assert inverter.runtime_data is running
    assert inverter.runtime_data.wallbox_elsewhere == WALLBOX_SERIAL


def _unsettled(entry: MockConfigEntry) -> list[str]:
    return [name for name, _need in entry.runtime_data.diagnosis.wallbox_unsettled()]


async def test_the_load_check_is_fed_by_the_managing_inverter(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """At gerd's it read 0 of 3 power steps after six of them (2026-11-24)."""
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)
    runner = wallbox_entry.runtime_data.diagnosis
    # No inverter here to ask: not a check to wait for, or auto repeat never ends.
    assert LOAD_INCLUDES not in _unsettled(wallbox_entry)
    assert LOAD_INCLUDES not in runner.tests["summary"]
    assert runner._house_load() is None

    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})
    runner = wallbox_entry.runtime_data.diagnosis
    assert LOAD_INCLUDES in _unsettled(wallbox_entry)
    assert LOAD_INCLUDES in runner.tests["summary"]

    device = inverter.runtime_data.inverter_coordinator.device
    read = device.field
    seen = {"load": 500.0, "power": 0.0}
    reading = wbt.readings_of(wallbox_entry.runtime_data.wallbox.device)
    at = dt_util.utcnow()
    with (
        patch.object(
            device,
            "field",
            side_effect=lambda n: seen["load"] if n == "load_power" else read(n),
        ),
        patch(
            "custom_components.sungrow_modbus.diagnosis.wallbox_readings_of",
            side_effect=lambda _d: {**reading, "charging_power": seen["power"]},
        ),
    ):
        for step in range(4):
            seen["power"] = 10000.0 * (step % 2)
            seen["load"] = 500.0 + seen["power"]
            runner.async_observe(at + timedelta(minutes=step))
    row = runner.tests["summary"][LOAD_INCLUDES]
    assert row["established"], row

    # A run holds that entry's polling: its load is not of now.
    inverter.runtime_data.write_owners.append(object())
    assert runner._house_load() is None


async def test_the_wallbox_counts_again_when_its_inverter_has_loaded(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """The wallbox entry may load first, and its inverter decides its checks."""
    (inverter,), wallbox_entry = await _set_up(hass, SERIAL)
    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})
    with patch.object(wallbox_entry.runtime_data.diagnosis, "async_notify") as notified:
        assert await hass.config_entries.async_reload(inverter.entry_id)
        await hass.async_block_till_done()
    notified.assert_called()


async def test_a_managed_wallbox_is_never_shown_as_standalone(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """In user-defined mode its setting holds still at the owner's current."""
    _, wallbox_entry = await _set_up(hass, SERIAL)
    await _answer(hass, wallbox_entry, **{CONF_WALLBOX_MANAGED_BY: SERIAL})
    runner = wallbox_entry.runtime_data.diagnosis
    for _ in range(management.STEADY_POLLS_FOR_STANDALONE):
        runner.wallbox_management.observe(16.0, charging=True)
    assert runner.wallbox_management.verdict()[0] == management.STANDALONE
    assert runner.wallbox_management_view()["management"] == management.MANAGED
