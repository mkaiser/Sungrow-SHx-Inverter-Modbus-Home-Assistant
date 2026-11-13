"""A wallbox at its own address, found by the scan and set up as an entry.

Read over TLS at unit 248 and identified by **its own serial**: there is no
inverter beside it to borrow an identity from. Only the directly addressed
wallbox is looked for; the dongle's unit 3 stays the inverter entry's business.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus import wallbox_capability_test as wbt
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_KIND,
    CONF_NETWORK,
    CONF_PUBLISH_ADDRESS,
    CONF_REPORTER,
    CONF_UNIT_ID,
    CONF_WALLBOX_MAX_AMPS,
    DOMAIN,
    KIND_WALLBOX,
    WALLBOX_TLS_PORT,
    WALLBOX_TLS_UNIT,
)
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from sungrow_modbus.wallbox import capability_test as wct

from .test_capability_test_ha import InstantClock
from .test_config_flow_search import _finish_sweep
from .test_wallbox_entities import WORDS, _wallbox_unit

#: A stand-in serial, in the registers a wallbox keeps it: input 21201-21206.
WALLBOX_SERIAL = "W123456789"
HOST = "192.168.1.60"
DATA = {
    CONF_HOST: HOST,
    CONF_PORT: WALLBOX_TLS_PORT,
    CONF_UNIT_ID: WALLBOX_TLS_UNIT,
    CONF_KIND: KIND_WALLBOX,
}


def _serial_words(text: str) -> dict[int, int]:
    raw = text.encode("ascii").ljust(12, b"\x00")
    return {21201 + i: int.from_bytes(raw[2 * i : 2 * i + 2], "big") for i in range(6)}


def _wallbox() -> MockModbusUnit:
    words = {**WORDS, "input": {**WORDS["input"], **_serial_words(WALLBOX_SERIAL)}}
    return _wallbox_unit(WALLBOX_TLS_UNIT, words)


class _Unit:
    def __init__(self, unit: MockModbusUnit) -> None:
        self._unit = unit

    async def __aenter__(self) -> MockModbusUnit:
        return self._unit

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _open_the_alpha_gate(devices_mode_offered: None) -> None:
    """Open the gate on the devices path, which the alpha shuts."""


async def _scan(hass: HomeAssistant, wallbox_hosts: list[str]) -> dict:
    """Search with a sweep that finds `wallbox_hosts` on port 516 only."""

    async def sweep(network: str, *, port: int, **kwargs: object) -> list[str]:
        return wallbox_hosts if port == WALLBOX_TLS_PORT else []

    def temporary(hass, params, unit_id):
        if params.port != WALLBOX_TLS_PORT:
            raise ModbusError("not here")
        return _Unit(_wallbox())

    with (
        patch("custom_components.sungrow_modbus.config_flow.async_sweep", sweep),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_hostname",
            return_value=None,
        ),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            side_effect=temporary,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NETWORK: "192.168.1.0/24"}
        )
        return await _finish_sweep(hass, result)


async def test_the_scan_offers_a_wallbox_at_its_own_address(
    hass: HomeAssistant,
) -> None:
    result = await _scan(hass, [HOST])

    assert result["step_id"] == "pick"
    values = [
        option["value"]
        for option in result["data_schema"].schema[CONF_HOST].config["options"]
    ]
    assert f"wallbox:{HOST}" in values


async def test_picking_it_makes_an_entry_of_its_own(hass: HomeAssistant) -> None:
    result = await _scan(hass, [HOST])
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        created = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"wallbox:{HOST}"}
        )

    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["data"] == DATA
    assert created["result"].unique_id == WALLBOX_SERIAL


async def test_a_wallbox_already_set_up_follows_its_new_address(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**DATA, CONF_HOST: "192.168.1.99"},
        unique_id=WALLBOX_SERIAL,
    )
    entry.add_to_hass(hass)
    result = await _scan(hass, [HOST])
    with patch("custom_components.sungrow_modbus.async_setup_entry", return_value=True):
        done = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: f"wallbox:{HOST}"}
        )

    assert done["type"] is FlowResultType.ABORT
    assert done["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


async def test_an_address_that_is_not_a_wallbox_is_not_offered(
    hass: HomeAssistant,
) -> None:
    """Port 516 open is not a wallbox: only a name over TLS makes one."""

    def temporary(hass, params, unit_id):
        raise ModbusError("a TLS service that is not a wallbox")

    async def sweep(network: str, *, port: int, **kwargs: object) -> list[str]:
        return [HOST] if port == WALLBOX_TLS_PORT else []

    with (
        patch("custom_components.sungrow_modbus.config_flow.async_sweep", sweep),
        patch(
            "custom_components.sungrow_modbus.config_flow.async_get_temporary_unit",
            side_effect=temporary,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "setup_devices"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"next_step_id": "search"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NETWORK: "192.168.1.0/24"}
        )
        result = await _finish_sweep(hass, result)

    assert result["step_id"] == "nothing_found"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id=WALLBOX_SERIAL)
    entry.add_to_hass(hass)
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=_wallbox()
    ) as get_unit:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    # Over TLS at the wallbox's own address, never the inverter's endpoint.
    params = get_unit.call_args.args[2]
    assert (params.host, params.port) == (HOST, WALLBOX_TLS_PORT)
    assert get_unit.call_args.args[3] == WALLBOX_TLS_UNIT
    return entry


async def test_the_entry_is_the_wallbox_and_nothing_else(hass: HomeAssistant) -> None:
    entry = await _setup(hass)

    assert entry.state is ConfigEntryState.LOADED
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, f"{WALLBOX_SERIAL}-wallbox"), entry.entry_id
    )
    assert device is not None
    assert device.via_device_id is None
    assert device.serial_number == WALLBOX_SERIAL
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert entities
    readings = [
        e for e in entities if e.unique_id.startswith(f"{WALLBOX_SERIAL}_wallbox_")
    ]
    assert readings
    assert all(e.unique_id.startswith(f"{WALLBOX_SERIAL}_") for e in entities)
    assert {e.domain for e in readings} <= {"sensor", "binary_sensor"}
    # Beside the readings, the diagnosis and its capability test; no control.
    diagnosis = {e.unique_id.removeprefix(f"{WALLBOX_SERIAL}_") for e in entities}
    assert {
        "diagnosis_start",
        "diagnosis_stop",
        "diagnosis_progress",
        "diagnosis_mode",
        "capability_test_status",
        "clear_capability_test_history",
        "skip_established_capability_tests",
    } <= diagnosis
    controls = [e for e in entities if e.domain in ("number", "switch", "select")]
    assert {e.unique_id for e in controls} == {
        f"{WALLBOX_SERIAL}_diagnosis_mode",
        f"{WALLBOX_SERIAL}_skip_established_capability_tests",
    }


async def test_a_wallbox_with_no_readable_serial_is_not_ready(
    hass: HomeAssistant,
) -> None:
    unit = MockModbusConnection().for_unit(WALLBOX_TLS_UNIT)
    unit.input = {k: v for k, v in WORDS["input"].items() if not 21201 <= k <= 21206}
    unit.holding = dict(WORDS["holding"])
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id=WALLBOX_SERIAL)
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert not await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_its_options_are_the_capability_tests_leave_and_the_report(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "wallbox"
    done = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "capability_test": {
                CONF_CAPABILITY_TEST_WALLBOX: True,
                CONF_WALLBOX_MAX_AMPS: 16,
            },
            "diagnosis": {CONF_REPORTER: "someone", CONF_PUBLISH_ADDRESS: False},
        },
    )
    await hass.async_block_till_done()

    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_CAPABILITY_TEST_WALLBOX] is True
    assert entry.options[CONF_WALLBOX_MAX_AMPS] == 16
    assert entry.options[CONF_REPORTER] == "someone"

    # An empty cap is a cap taken back; the leave can be given back too.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "capability_test": {CONF_CAPABILITY_TEST_WALLBOX: False},
            "diagnosis": {CONF_PUBLISH_ADDRESS: False},
        },
    )
    await hass.async_block_till_done()
    assert CONF_WALLBOX_MAX_AMPS not in entry.options
    assert entry.options[CONF_CAPABILITY_TEST_WALLBOX] is False


async def test_reconfigure_still_has_nothing_to_change(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    result = await entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wallbox_entry"


async def test_its_diagnosis_reads_it_and_publishes_only_a_stand_in(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass)
    runner = entry.runtime_data.diagnosis
    with patch(
        "custom_components.sungrow_modbus.wallbox_diagnosis.persistent_notification"
    ) as notification:
        assert runner.async_start()
        await hass.async_block_till_done()

    state = runner.state
    assert state.error is None, state.error
    document = state.document
    assert document["document"] == "wallbox"
    section = document["wallbox"]
    assert section["path"] == "tls"
    assert section["readings"]["model_name"]["value"] == "AC22E-01"
    assert section["serial_anonymized_hashed"].startswith("anon-")
    # Dumped where TLS answers: a read starts only on a data point's first word.
    from sungrow_modbus.dump import WALLBOX_TLS_BANDS

    dumped = {
        (space, int(address))
        for space, values in section["register_dump"].items()
        if isinstance(values, dict)
        for address in values
    }
    assert dumped == {
        (space, address)
        for space, start, count, _why in WALLBOX_TLS_BANDS
        for address in range(start, start + count)
    }
    # The serial's words are masked; the real one appears nowhere.
    assert WALLBOX_SERIAL not in json.dumps(document)
    assert notification.async_create.called

    from custom_components.sungrow_modbus.download import _filename

    assert _filename(document).startswith("ac22e01-")


# -- its own capability test ---------------------------------------------------


@pytest.fixture
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass every wait of the wallbox procedure at once."""
    monkeypatch.setattr(wct, "RealClock", InstantClock)


def _testable(*, charging: bool, setting: int = 160) -> MockModbusUnit:
    """Return the wallbox with the registers its capability test reads."""
    unit = _wallbox()
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


async def _setup_with(
    hass: HomeAssistant, unit: MockModbusUnit, **options: object
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=DATA, options=options, unique_id=WALLBOX_SERIAL
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _extended(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    runner = entry.runtime_data.diagnosis
    with patch(
        "custom_components.sungrow_modbus.wallbox_diagnosis.persistent_notification"
    ):
        assert runner.async_start(capability_test=True)
        assert runner._task is not None
        await runner._task
        await hass.async_block_till_done()


async def test_without_leave_an_extended_run_reads_and_writes_nothing(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=True)
    entry = await _setup_with(hass, unit)
    before = dict(unit.holding)
    writes: list[tuple[int, int]] = []
    real = unit.write_register

    async def watching(address: int, value: int) -> object:
        writes.append((address, value))
        return await real(address, value)

    with patch.object(unit, "write_register", watching):
        await _extended(hass, entry)

    runner = entry.runtime_data.diagnosis
    assert runner.state.error is None, runner.state.error
    assert writes == []
    assert unit.holding == before
    assert runner.state.document["document"] == "wallbox"
    assert "wallbox_capability_test" not in runner.state.document
    assert "switch it on" in runner._summary(runner.state.document)


async def test_with_leave_an_extended_run_tests_keeps_and_puts_back(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=True)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    original = dict(unit.holding)
    paused: list[bool] = []
    real = unit.write_register

    async def watching(address: int, value: int) -> object:
        paused.append(entry.runtime_data.polling_paused)
        return await real(address, value)

    with patch.object(unit, "write_register", watching):
        await _extended(hass, entry)

    runner = entry.runtime_data.diagnosis
    assert runner.state.error is None, runner.state.error
    # It wrote, only with polling held off, and every register is back.
    assert paused and all(paused)
    assert not entry.runtime_data.polling_paused
    assert {k: unit.holding[k] for k in original} == original
    assert await wbt.async_leftover(hass, entry) is None
    # The run is kept, in the document and on the counters.
    block = runner.state.document["wallbox_capability_test"]
    assert block["runs"] == 1
    assert runner._wallbox_folded is not None
    assert runner._wallbox_folded["runs"] == 1
    tests = runner.tests
    assert tests is not None
    assert any("output current" in name for name in tests["summary"])
    # Counted on the status sensor, as an inverter entry's runs are.
    assert len(tests["runs"]) == 1
    assert tests["runs"][0]["read_at"]
    # Its path is the wallbox's own address, never the dongle.
    runs = await wbt.async_ledger_runs(hass, entry, wbt.firmware_of(_device(entry)))
    assert runs and runs[-1]["transport"] == "tls"
    # And it never published the serial.
    assert WALLBOX_SERIAL not in json.dumps(runner.state.document)


def _device(entry: MockConfigEntry) -> object:
    return entry.runtime_data.wallbox.device


async def test_the_kept_runs_survive_a_reload(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=True)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    await _extended(hass, entry)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    runner = entry.runtime_data.diagnosis
    assert runner._wallbox_folded is not None
    assert runner._wallbox_folded["runs"] == 1


async def test_clearing_the_history_forgets_the_wallbox_runs(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=True)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    await _extended(hass, entry)
    runner = entry.runtime_data.diagnosis
    await runner.async_clear_ledger()

    assert runner._wallbox_folded is None
    assert (
        await wbt.async_ledger_runs(hass, entry, wbt.firmware_of(_device(entry))) == []
    )


async def test_auto_repeat_starts_a_wallbox_run_with_no_inverter_to_ask(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=True)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    runner = entry.runtime_data.diagnosis
    assert runner.wallbox_due()
    with patch("custom_components.sungrow_modbus.diagnosis.persistent_notification"):
        runner.continuous.async_turn_on()
        assert runner.state.running
        assert runner._task is not None
        await runner._task
        await hass.async_block_till_done()

    assert runner.state.error is None, runner.state.error
    assert runner.continuous.runs_started == 1
    assert runner._wallbox_folded is not None
    runner.continuous.async_turn_off("test over")


async def test_auto_repeat_waits_while_no_car_charges(
    hass: HomeAssistant, no_waiting: None
) -> None:
    unit = _testable(charging=False)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    runner = entry.runtime_data.diagnosis
    before = dict(unit.holding)
    runner.continuous.async_turn_on()
    await hass.async_block_till_done()

    # Idle, the output current reads 0 and the procedure refuses to write, so
    # nothing is due: auto repeat waits and says for what.
    assert runner.wallbox_due() == []
    assert not runner.state.running
    assert "wallbox" in runner.continuous.waiting
    assert unit.holding == before
    runner.continuous.async_turn_off("test over")


async def test_auto_repeat_spaces_wallbox_runs_by_its_own_shorter_slot(
    hass: HomeAssistant, no_waiting: None
) -> None:
    from custom_components.sungrow_modbus import continuous

    unit = _testable(charging=True)
    entry = await _setup_with(
        hass,
        unit,
        **{CONF_CAPABILITY_TEST_WALLBOX: True, CONF_WALLBOX_MAX_AMPS: 10},
    )
    runner = entry.runtime_data.diagnosis
    assert runner.wallbox_interval == continuous.WALLBOX_ALONE_INTERVAL
    assert continuous.WALLBOX_ALONE_INTERVAL < continuous.INTERVAL
    scheduler = runner.continuous
    with patch("custom_components.sungrow_modbus.diagnosis.persistent_notification"):
        scheduler.async_turn_on()
        assert runner._task is not None
        await runner._task
        await hass.async_block_till_done()
    assert scheduler.runs_started == 1
    started = scheduler.started_at
    assert started is not None

    # The next run waits for the next 15-minute slot, not the next half hour.
    assert scheduler.next_start(started) == started + continuous.WALLBOX_ALONE_INTERVAL
    later = started + continuous.WALLBOX_ALONE_INTERVAL + continuous.QUIET
    assert scheduler._wallbox_slot(later) == 1
    scheduler.async_turn_off("test over")


def test_an_inverter_entry_keeps_the_half_hour() -> None:
    from custom_components.sungrow_modbus import continuous
    from custom_components.sungrow_modbus.diagnosis import DiagnosisRunner

    assert DiagnosisRunner.wallbox_interval == continuous.INTERVAL
