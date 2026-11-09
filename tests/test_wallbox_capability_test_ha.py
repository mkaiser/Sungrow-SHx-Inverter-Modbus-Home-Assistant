"""The wallbox capability test in Home Assistant: leave, snapshot, ledger, repeat.

The procedure is tested in `test_wallbox_capability_test.py` against a wallbox
that behaves. This tests what only exists because it runs here: that nothing
is written without the owner's leave, that polling is held off and the
snapshot is on disk first, that a leftover snapshot is put back before
anything else, that a finished run is kept and counted with the inverter's, and
that auto repeat starts a wallbox run only when a car is charging, in a slot of
its own. The mock wallbox is static, so what it does with an offer is not
judged: only that every register is back where it was.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, ClassVar
from unittest.mock import patch

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_UNIT_ID,
    CONF_WALLBOX_MAX_AMPS,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from sungrow_modbus.wallbox import capability_test as wct, ledger

from .conftest import SERIAL
from .test_capability_test_ha import InstantClock
from .test_wallbox_entities import WORDS

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass every wait at once, in the library's own default clock."""
    monkeypatch.setattr(wct, "RealClock", InstantClock)


def _wallbox(*, charging: bool, setting: int = 160) -> MockModbusUnit:
    """Return a mock wallbox, with a car on it or without."""
    unit = MockModbusConnection().for_unit(3)
    unit.input = dict(WORDS["input"])
    unit.holding = dict(WORDS["holding"])
    unit.input[wct.RATED_CURRENT] = 320
    unit.input[wct.CHARGING_STATUS_ADDRESS] = 3 if charging else 1
    for address in (wct.PHASE_A_CURRENT, wct.PHASE_B_CURRENT, wct.PHASE_C_CURRENT):
        unit.input[address] = 100 if charging else 0
    unit.input[wct.AVAILABLE_CURRENT] = setting
    unit.holding[wct.OUTPUT_CURRENT] = setting if charging else 0
    unit.holding[wct.START_STOP] = 0
    unit.holding[wct.ENABLED] = 1
    unit.holding[wct.PHASE_SETPOINT] = 0
    unit.holding[wct.MILEAGE] = 70
    return unit


async def _setup(
    hass: HomeAssistant,
    inverter: MockModbusUnit,
    wallbox: MockModbusUnit,
    **options: Any,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    empty = MockModbusConnection().for_unit(9)

    def units(_hass: Any, _entry: Any, _params: Any, unit_id: int) -> MockModbusUnit:
        if unit_id == 1:
            return inverter
        return wallbox if unit_id == 3 else empty

    with patch("custom_components.sungrow_modbus.async_get_unit", side_effect=units):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _run(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    runner = entry.runtime_data.diagnosis
    assert runner.async_start_wallbox()
    assert runner._task is not None
    await runner._task
    await hass.async_block_till_done()


async def test_without_the_owners_leave_a_wallbox_run_is_refused(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(hass, sungrow_unit, box)
    before = dict(box.holding)

    assert not entry.runtime_data.diagnosis.async_start_wallbox()
    assert entry.runtime_data.diagnosis.wallbox_awaited() == []
    assert box.holding == before


async def test_a_run_writes_with_polling_held_off_and_puts_everything_back(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass,
        sungrow_unit,
        box,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    original = dict(box.holding)
    paused: list[bool] = []
    real_write = box.write_register

    async def watching(address: int, value: int) -> Any:
        paused.append(entry.runtime_data.polling_paused)
        return await real_write(address, value)

    with patch.object(box, "write_register", watching):
        await _run(hass, entry)

    assert paused and all(paused)
    assert not entry.runtime_data.polling_paused
    assert {k: box.holding[k] for k in original} == original
    # The snapshot was cleared once everything was back.
    assert await wbt.async_leftover(hass, entry) is None
    runner = entry.runtime_data.diagnosis
    assert runner.state.error is None
    assert runner._wallbox_folded is not None
    assert runner._wallbox_folded["runs"] == 1
    # A static wallbox cannot be judged, but the ledger knows what ran.
    assert "output current" in runner._wallbox_folded["checks"]


async def test_the_snapshot_is_on_disk_before_the_first_write(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    seen: list[Any] = []
    real_write = box.write_register

    async def watching(address: int, value: int) -> Any:
        if not seen:
            seen.append(await wbt.async_leftover(hass, entry))
        return await real_write(address, value)

    with patch.object(box, "write_register", watching):
        await _run(hass, entry)

    assert seen[0] is not None
    assert wct.OUTPUT_CURRENT in seen[0]["touched"]
    assert seen[0]["raw"][wct.OUTPUT_CURRENT] == 160


async def test_a_leftover_snapshot_is_put_back_before_a_new_run_takes_its_own(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    # A run that died: the register holds its 6 A, the snapshot holds the house's.
    box.holding[wct.OUTPUT_CURRENT] = 60
    await wbt.snapshot_store(hass, entry).async_save(
        {"raw": {str(wct.OUTPUT_CURRENT): 160}, "touched": [wct.OUTPUT_CURRENT]}
    )
    writes: list[tuple[int, int]] = []
    real_write = box.write_register

    async def watching(address: int, value: int) -> Any:
        writes.append((address, value))
        return await real_write(address, value)

    with patch.object(box, "write_register", watching):
        await _run(hass, entry)

    assert writes[0] == (wct.OUTPUT_CURRENT, 160)
    assert box.holding[wct.OUTPUT_CURRENT] == 160


async def test_the_cap_is_never_above_the_rating_and_a_default_is_not_consent(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    options = wbt.run_options(entry)

    assert options.leave
    assert options.max_amps == wbt.DEFAULT_WALLBOX_MAX_AMPS
    assert not options.cap_explicit

    await _run(hass, entry)
    checks = entry.runtime_data.diagnosis._wallbox_folded["checks"]
    for name in ("below minimum", "above rating", "fallback"):
        assert checks[name]["verdict"] == wct.SKIPPED


async def test_established_checks_are_left_out_of_the_next_run(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )

    options = wbt.run_options(entry, frozenset({"output current", "mileage"}))
    assert not options.current
    assert not options.mileage
    assert options.start_stop


async def test_the_counters_count_the_wallbox_with_the_inverters_checks(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    runner = entry.runtime_data.diagnosis
    await _run(hass, entry)

    rows = runner.tests["summary"]
    assert any(name.startswith("wallbox ") for name in rows)


async def test_auto_repeat_starts_a_wallbox_run_only_while_a_car_charges(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=False)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    runner = entry.runtime_data.diagnosis
    from homeassistant.util import dt as dt_util

    with patch(
        "custom_components.sungrow_modbus.continuous.ledger.awaited", return_value=[]
    ):
        runner.continuous.async_turn_on()
        await hass.async_block_till_done()
        assert runner.continuous.runs_started == 0
        assert "waiting for the wallbox" in runner.continuous.waiting

        # A car plugs in and starts to charge.
        box.input[wct.CHARGING_STATUS_ADDRESS] = 3
        for address in (wct.PHASE_A_CURRENT, wct.PHASE_B_CURRENT, wct.PHASE_C_CURRENT):
            box.input[address] = 100
        await runner.entry.runtime_data.wallbox.async_refresh()
        runner.continuous._async_tick(dt_util.utcnow() + timedelta(minutes=3))
        assert runner._task is not None
        await runner._task
        await hass.async_block_till_done()

    assert runner.continuous.runs_started == 1
    assert runner._wallbox_folded is not None
    # The wallbox's slot is its own: the same slot starts no second run.
    assert runner.continuous._last_wallbox_slot == 0
    assert runner.continuous._last_slot is None


async def test_a_wallbox_run_and_an_inverter_run_never_overlap(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    runner = entry.runtime_data.diagnosis

    assert runner.async_start_wallbox()
    assert not runner.async_start_wallbox()
    assert not runner.async_start(capability_test=True)
    await runner._task
    await hass.async_block_till_done()


async def test_clearing_the_history_forgets_the_wallbox_runs(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    box = _wallbox(charging=True)
    entry = await _setup(
        hass, sungrow_unit, box, **{CONF_CAPABILITY_TEST_WALLBOX: True}
    )
    runner = entry.runtime_data.diagnosis
    await _run(hass, entry)
    firmware = wbt.firmware_of(runner._wallbox_device())
    assert await wbt.async_ledger_runs(hass, entry, firmware)

    await runner.async_clear_ledger()

    assert runner._wallbox_folded is None
    assert not await wbt.async_ledger_runs(hass, entry, firmware)


def test_a_path_is_named_by_where_the_wallbox_is_read() -> None:
    class Entry:
        options: ClassVar[dict[str, Any]] = {}

    assert wbt.transport_of(Entry()) == "dongle"  # type: ignore[arg-type]
    Entry.options = {"wallbox_host": "wallbox.local"}
    assert wbt.transport_of(Entry()) == "tls"  # type: ignore[arg-type]


def test_a_dongle_gets_no_fresh_session() -> None:
    assert not wbt.EntryWallboxPort(object()).fresh
    assert ledger.fold_key({"transport": "dongle", "fresh_session": False}) == (
        "dongle",
        False,
    )
