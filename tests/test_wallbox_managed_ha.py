"""A wallbox an inverter entry here manages is tested at that inverter.

The wallbox's own entry finds the inverter entry that left the wallbox to it
(`wallbox_elsewhere`), writes that entry's EV charger block, reads its own
wallbox for what the car does, and holds both entries' polling off. Nothing is
written to the wallbox itself. A wallbox with no such inverter entry awaits
nothing, so auto repeat does not wait for a run that could not write.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_WALLBOX_MAX_AMPS,
    DOMAIN,
)
from custom_components.sungrow_modbus.entry_migration import MINOR_VERSION
from homeassistant.core import HomeAssistant
from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.wallbox import capability_test as wct, managed_test as mt

from .conftest import InstantClock
from .test_wallbox_entry import DATA, WALLBOX_SERIAL
from .test_wallbox_one_device import _inverter_entry, _set_up, _Units

#: The inverter's block as gerd's read: charging on, fast charge, 16 A.
BLOCK = [ev.ON, ev.FAST, 0, 0, 0, 160, 0, 0, 0, 0, ev.OFF]


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass every wait at once."""
    monkeypatch.setattr(mt, "RealClock", InstantClock)
    monkeypatch.setattr(wct, "RealClock", InstantClock)


def _wallbox_entry(hass: HomeAssistant, **options: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=DATA,
        options=options,
        unique_id=WALLBOX_SERIAL,
        title="AC22E-01",
        minor_version=MINOR_VERSION,
    )
    entry.add_to_hass(hass)
    return entry


def _house(sungrow_unit: MockModbusUnit) -> _Units:
    """Return the inverter with its EV charger block, and a car charging at 10 A."""
    units = _Units(sungrow_unit)
    for offset, word in enumerate(BLOCK):
        sungrow_unit.holding[ev.CHARGING + offset] = word
    units.direct.input[wct.RATED_CURRENT] = 320
    units.direct.input[wct.CHARGING_STATUS_ADDRESS] = 3
    for address in (wct.PHASE_A_CURRENT, wct.PHASE_B_CURRENT, wct.PHASE_C_CURRENT):
        units.direct.input[address] = 100
    return units


async def _both(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, **options: Any
) -> tuple[_Units, MockConfigEntry, MockConfigEntry]:
    units = _house(sungrow_unit)
    wallbox = _wallbox_entry(hass, **options)
    inverter = _inverter_entry(hass)
    await _set_up(hass, units, wallbox, inverter)
    assert inverter.runtime_data.wallbox_elsewhere == WALLBOX_SERIAL
    return units, wallbox, inverter


async def _run(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    runner = entry.runtime_data.diagnosis
    assert runner.async_start_wallbox()
    assert runner._task is not None
    await runner._task
    await hass.async_block_till_done()


async def test_the_inverter_entry_that_left_the_wallbox_is_its_manager(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    _units, wallbox, inverter = await _both(
        hass, sungrow_unit, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )

    assert wbt.managing_entry(hass, wallbox) is inverter
    options = wbt.check_options(wallbox, hass)
    assert options["managed"] and options["start_stop"]
    assert not options["standalone"] and not options["enable"]
    names = {name for name, _need in wallbox.runtime_data.diagnosis.wallbox_awaited()}
    assert names == {"user current", "floor", "start/stop"}


async def test_a_run_writes_the_inverter_not_the_wallbox_and_puts_it_back(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    units, wallbox, inverter = await _both(
        hass,
        sungrow_unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    inverter_writes: list[tuple[int, int, bool, bool]] = []
    wallbox_writes: list[tuple[int, int]] = []
    real_inverter = units.inverter.write_register
    real_wallbox = units.direct.write_register

    async def on_inverter(address: int, value: int) -> Any:
        inverter_writes.append(
            (
                address,
                value,
                inverter.runtime_data.polling_paused,
                wallbox.runtime_data.polling_paused,
            )
        )
        return await real_inverter(address, value)

    async def on_wallbox(address: int, value: int) -> Any:
        wallbox_writes.append((address, value))
        return await real_wallbox(address, value)

    with (
        patch.object(units.inverter, "write_register", on_inverter),
        patch.object(units.direct, "write_register", on_wallbox),
    ):
        await _run(hass, wallbox)

    assert wallbox_writes == []
    assert inverter_writes[0][:2] == (ev.MODE, ev.USER_DEFINED)
    assert all(
        paused_inverter and paused_wallbox
        for *_w, paused_inverter, paused_wallbox in inverter_writes
    )
    assert {address for address, *_rest in inverter_writes} <= {
        ev.CHARGING,
        ev.MODE,
        ev.USER_CURRENT,
    }
    assert [units.inverter.holding[ev.CHARGING + i] for i in range(11)] == BLOCK
    assert not inverter.runtime_data.polling_paused
    assert not wallbox.runtime_data.polling_paused
    assert await wbt.async_leftover(hass, wallbox) is None

    runs = await wbt.async_ledger_runs(
        hass, wallbox, wbt.firmware_of(wallbox.runtime_data.wallbox.device)
    )
    assert runs[-1]["transport"] == "inverter"
    checks = wallbox.runtime_data.diagnosis._wallbox_folded["checks"]
    assert checks["user current"]["verdict"] == mt.CONFIRMED  # 10 A, the car's draw
    assert "output current" not in checks


async def test_without_leave_nothing_is_written(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    units, wallbox, _inverter = await _both(hass, sungrow_unit)

    assert not wbt.check_options(wallbox, hass)["managed"]
    assert not wallbox.runtime_data.diagnosis.async_start_wallbox()
    assert [units.inverter.holding[ev.CHARGING + i] for i in range(11)] == BLOCK


async def test_a_wallbox_no_inverter_entry_manages_awaits_nothing(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    units = _house(sungrow_unit)
    wallbox = _wallbox_entry(hass, **{CONF_CAPABILITY_TEST_WALLBOX: True})
    await _set_up(hass, units, wallbox)

    assert wbt.managing_entry(hass, wallbox) is None
    assert not any(wbt.check_options(wallbox, hass).values())
    assert wallbox.runtime_data.diagnosis.wallbox_awaited() == []


async def test_a_managed_leftover_is_put_back_through_the_inverter_first(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    units, wallbox, _inverter = await _both(
        hass, sungrow_unit, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    # A run that died in user-defined mode at 6 A.
    units.inverter.holding[ev.MODE] = ev.USER_DEFINED
    units.inverter.holding[ev.USER_CURRENT] = 60
    await wbt.snapshot_store(hass, wallbox).async_save(
        {
            "raw": {
                str(ev.CHARGING): ev.ON,
                str(ev.MODE): ev.FAST,
                str(ev.USER_CURRENT): 160,
            },
            "touched": [ev.MODE, ev.USER_CURRENT],
            "managed": True,
            "charging_at_start": True,
        }
    )
    writes: list[tuple[int, int]] = []
    real = units.inverter.write_register

    async def watching(address: int, value: int) -> Any:
        writes.append((address, value))
        return await real(address, value)

    with patch.object(units.inverter, "write_register", watching):
        await _run(hass, wallbox)

    assert writes[:2] == [(ev.USER_CURRENT, 160), (ev.MODE, ev.FAST)]
    assert [units.inverter.holding[ev.CHARGING + i] for i in range(11)] == BLOCK
