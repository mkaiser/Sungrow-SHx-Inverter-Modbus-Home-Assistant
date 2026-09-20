"""Part B on a device page: the button, the action, and the promises around it.

The measurement itself is tested in `test_control_test.py`, against stubs and
without Home Assistant. What is tested here is the four things that only exist
because this runs inside Home Assistant, and each of them is a promise rather
than a feature:

* a run writes only when somebody asked for a run that writes -- so the survey
  button, the survey action and the diagnostics download cannot acquire that
  power by inheriting a default;
* the two halves share one progress bar, and it never goes backwards;
* the inverter is started again if Home Assistant shuts down while it is
  stopped, which is a guarantee about *ordering* and therefore worth a test
  that fails loudly if the ordering is ever reversed;
* what a run could not put back becomes a repair rather than a log line.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_CONTROL_TEST_RESTART,
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.survey import PART_A, PART_B
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

SURVEY_BUTTON = "button.sh10rt_run_capability_survey"
CONTROL_BUTTON = "button.sh10rt_run_control_write_test"


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Collapse every wait in the procedure, without changing a code path.

    A real run spends its ten minutes almost entirely asleep: settling after a
    write, and sampling for twenty seconds at a time so a median means
    something. None of that waiting is what these tests are about -- they are
    about ordering, wiring and what gets written -- so the durations go to zero
    and the same code runs.

    Patched on the library module rather than passed in, so the integration
    keeps building its runner exactly as it does in a house.
    """
    from sungrow_modbus import control_test as engine

    monkeypatch.setattr(engine, "WINDOW", 0.0)
    monkeypatch.setattr(engine, "SETTLE", 0.0)
    monkeypatch.setattr(engine, "SAMPLE_INTERVAL", 0.0)
    monkeypatch.setattr(engine, "RESTORE_PAUSE", 0.0)
    monkeypatch.setattr(engine, "RESTART_DWELL", 0.0)
    monkeypatch.setattr(engine, "RESTART_POLL", 0.0)
    monkeypatch.setattr(engine.ControlTest, "WRITE_SETTLE", 0.0)


@pytest.fixture
def ready_unit(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an inverter that is running, generating, and states its limits."""
    sungrow_unit.input[12999] = 0x0000  # running -- and note that zero means running
    sungrow_unit.input[5621] = 0
    sungrow_unit.input[5622] = 1000
    sungrow_unit.input[5627] = 50
    return sungrow_unit


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, **options: Any
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={**ENTRY_DATA, CONF_MODE: MODE_DIAGNOSTICS},
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    """Press a button and wait for the run it starts to finish.

    The run is a background task on purpose -- that is what lets somebody
    navigate away from the device page while it works -- and
    `async_block_till_done` does not wait for those. So the task is awaited
    directly, which is also what keeps a half-finished run from leaking into
    the next test.
    """
    entry = next(iter(hass.config_entries.async_entries(DOMAIN)))
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    task = entry.runtime_data.survey._task
    if task is not None:
        await task
    await hass.async_block_till_done()


# -- who may write ----------------------------------------------------------


async def test_the_survey_button_never_writes(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Part A reads. That is the whole promise of the button beside this one.

    Asserted on the registers rather than on a flag: a survey that wrote one
    word would be a survey that wrote, whatever the code said it was doing.
    """
    entry = await _setup(hass, ready_unit)
    before = dict(ready_unit.holding)

    await _press(hass, SURVEY_BUTTON)

    assert ready_unit.holding == before
    assert entry.runtime_data.survey.state.document is not None
    assert "control_test" not in entry.runtime_data.survey.state.document


async def test_the_control_test_button_writes_and_puts_everything_back(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """And the document it leaves carries both halves, in one file."""
    entry = await _setup(hass, ready_unit)

    await _press(hass, CONTROL_BUTTON)

    document = entry.runtime_data.survey.state.document
    assert document is not None
    block = document["control_test"]
    assert block["readback"]
    assert not [row for row in block["restored"] if not row["restored"]]


async def test_the_diagnostics_download_never_runs_part_b(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The same document, from the same code, without the power to write.

    `allow_dump` already establishes this shape -- the caller decides what it
    can afford -- and part B extends it from "can afford five minutes" to "may
    change this house".
    """
    from custom_components.sungrow_modbus.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    entry = await _setup(hass, ready_unit)
    before = dict(ready_unit.holding)

    report = await async_get_config_entry_diagnostics(hass, entry)

    assert ready_unit.holding == before
    assert "control_test" not in report["fingerprint"]


async def test_the_action_refuses_a_second_run(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Two runs writing at once would restore each other's probe values."""
    from homeassistant.exceptions import HomeAssistantError

    entry = await _setup(hass, ready_unit)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    entry.runtime_data.survey.async_start(control_test=True)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "run_control_test", {"device_id": device.id}, blocking=True
        )
    await hass.async_block_till_done()


# -- the progress bar -------------------------------------------------------


async def test_one_bar_covers_both_parts_and_never_goes_backwards(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Both halves state their step count before either starts.

    That is what makes a single honest bar possible. A bar that reset between
    the parts, or a total that grew halfway through, would be worse than no bar
    -- the lesson `fingerprint.async_build` already carries in a comment.
    """
    entry = await _setup(hass, ready_unit)
    seen: list[float] = []
    parts: set[str] = set()

    runner = entry.runtime_data.survey
    original = runner._on_progress

    def record(fraction: float, label: str) -> None:
        seen.append(fraction)
        if runner.state.part:
            parts.add(runner.state.part)
        original(fraction, label)

    runner._on_progress = record  # type: ignore[method-assign]
    await _press(hass, CONTROL_BUTTON)

    assert seen == sorted(seen), "the bar went backwards"
    assert max(seen) <= 1.0
    assert parts == {PART_A, PART_B}


# -- never left stopped -----------------------------------------------------


async def test_a_shutdown_hook_is_armed_before_the_stop_and_removed_after(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The ordering *is* the guarantee, so this test exists to fail if it flips.

    A shutdown job is awaited before `EVENT_HOMEASSISTANT_STOP`, and background
    tasks are cancelled after that. So a hook registered before 0xCE runs while
    the connection is still alive; one registered after it would be a hook for a
    window that had already closed.
    """

    def obey(event: Any) -> None:
        if event.address == 12999:
            ready_unit.input[12999] = 0x0008 if event.values[0] == 0xCE else 0x0000

    ready_unit.on_write(obey)
    await _setup(hass, ready_unit, **{CONF_CONTROL_TEST_RESTART: True})

    armed_at: list[str] = []
    real_add = hass.async_add_shutdown_job

    def watch(job: Any, *args: Any) -> Any:
        # Nothing has been written to the stop register yet at this point.
        armed_at.append("before" if 12999 not in ready_unit.holding else "after")
        return real_add(job, *args)

    with patch.object(hass, "async_add_shutdown_job", watch):
        await _press(hass, CONTROL_BUTTON)

    assert armed_at == ["before"]
    assert ready_unit.input[12999] == 0x0000  # and it came back


# -- what could not be put back ---------------------------------------------


async def test_an_unfinished_run_becomes_a_repair_rather_than_a_log_line(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A snapshot outliving its run is a house still carrying a test's values.

    It is raised on the next setup rather than fixed there: the integration
    does not write registers during setup, and confirming the repair is the
    explicit action that does.
    """
    from custom_components.sungrow_modbus.control_test import _store
    from custom_components.sungrow_modbus.repairs import issue_id

    entry = await _setup(hass, ready_unit)
    await _store(hass, entry).async_save(
        {
            "taken_at": 1.0,
            "values": {"battery_min_soc": 10.0},
            "raw": {"battery_min_soc": 100},
            "bounds": {},
            "unreadable": {},
            "battery_ceiling": 5000,
            "stopped_at": None,
        }
    )
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry))
    assert issue is not None
    assert issue.is_fixable
    assert "battery_min_soc" in issue.translation_placeholders["registers"]


async def test_a_finished_run_leaves_no_repair_behind(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The snapshot is removed only once everything in it has been read back."""
    from custom_components.sungrow_modbus.control_test import async_leftover
    from custom_components.sungrow_modbus.repairs import issue_id

    entry = await _setup(hass, ready_unit)

    await _press(hass, CONTROL_BUTTON)

    assert await async_leftover(hass, entry) is None
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry)) is None


async def test_removing_the_entry_takes_the_snapshot_with_it(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A `Store` is a file in `.storage/`, and nothing else would delete it.

    Home Assistant cleans up the entry and the registries on its own; it knows
    nothing about this one. Without `async_remove_entry` the snapshot would
    outlive the integration it belonged to, keyed by an entry id that will
    never exist again.

    What this deliberately does not do is restore anything. The entry is
    already going, so there is no connection left to put a register back
    through -- which is exactly why the repair is raised at *setup*, where
    somebody can still act on it, and not here.
    """
    from custom_components.sungrow_modbus.control_test import _store

    entry = await _setup(hass, ready_unit)
    store = _store(hass, entry)
    await store.async_save(
        {
            "taken_at": 1.0,
            "values": {"battery_min_soc": 10.0},
            "raw": {"battery_min_soc": 100},
            "bounds": {},
            "unreadable": {},
            "battery_ceiling": 5000,
            "stopped_at": None,
        }
    )
    assert await store.async_load() is not None

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    # A fresh handle, not the one used above: `Store` caches what it loaded,
    # so reusing it would be asking the cache rather than the filesystem.
    assert await _store(hass, entry).async_load() is None


async def test_the_button_runs_after_dark_where_the_cli_would_refuse(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The one option the button does not take from the entry, and why.

    A CLI user chose the moment and can pass `--allow-dark`. Somebody on Home
    Assistant OS has no terminal, so a run refused for want of sun is a run
    they can never make -- and in a German December that is most of the day.
    What it would cost them is the readback half, which is the half that finds
    a factor-10 error and does not care whether the sun is up.

    The behavioural half still self-skips in the dark and says so; this is not
    a claim that it runs.
    """
    from custom_components.sungrow_modbus.control_test import ControlTestRunner

    entry = await _setup(hass, ready_unit)
    options = ControlTestRunner(hass, entry)._options()

    assert options.allow_dark is True
    # The other two are still the owner's to grant, and default to no.
    assert options.restart is False
    assert options.enable_export_limit is False
