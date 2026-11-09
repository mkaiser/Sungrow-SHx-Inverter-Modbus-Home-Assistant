"""Part B on a device page: the button, the action, and the promises around it.

The measurement itself is tested in `test_capability_test.py`, against stubs and
without Home Assistant. What is tested here is the four things that only exist
because this runs inside Home Assistant, and each of them is a promise rather
than a feature:

* a run writes only when somebody asked for a run that writes -- so the diagnosis
  button, the diagnosis action and the diagnostics download cannot acquire that
  power by inheriting a default;
* the two halves share one progress bar, and it never goes backwards;
* the inverter is started again if Home Assistant shuts down while it is
  stopped, which is a guarantee about *ordering* and therefore worth a test
  that fails loudly if the ordering is ever reversed;
* what a run could not put back becomes a repair rather than a log line.
"""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_EXPORT,
    CONF_CAPABILITY_TEST_PV_CUT,
    CONF_CAPABILITY_TEST_RESTART,
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DIAGNOSTICS,
)
from custom_components.sungrow_modbus.diagnosis import PART_A, PART_B
from custom_components.sungrow_modbus.diagnosis_entities import elapsed
from homeassistant.components import persistent_notification
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import ledger

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: The modes *Diagnosis: start* runs, chosen in *Diagnosis: mode*; `_press`
#: takes one of these as well as a button's entity id.
DIAGNOSIS_BUTTON = "read_only"
CONTROL_BUTTON = "extended"
MODE = "select.sh10rt_diagnosis_mode"
START = "button.sh10rt_diagnosis_start"
STOP = "button.sh10rt_diagnosis_stop"
STEP = "sensor.sh10rt_diagnosis_current_step"


class InstantClock:
    """A clock whose every wait passes at once, still yielding to the loop."""

    def __init__(self) -> None:
        """Start at an arbitrary origin."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the fake time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Advance instead of waiting, and let Home Assistant run meanwhile."""
        self.now += seconds
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every wait in the procedure pass at once, without changing a path.

    A real run spends its ten minutes almost entirely asleep: settling after a
    write, sampling for twenty seconds at a time so a median means something,
    waiting out a restart. None of that is what these tests are about -- they
    are about ordering, wiring and what gets written -- so time is faked and
    the same code runs, deadlines included.

    Patched where the runner picks its default clock, so the integration keeps
    building its runner exactly as it does in a house.
    """
    from sungrow_modbus.capability_test import base

    monkeypatch.setattr(base, "RealClock", InstantClock)


@pytest.fixture
def ready_unit(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an inverter that is running, generating, and states its limits."""
    sungrow_unit.input[12999] = 0x0000  # running -- and note that zero means running
    sungrow_unit.input[5621] = 0
    sungrow_unit.input[5622] = 1000
    sungrow_unit.input[5627] = 50
    return sungrow_unit


#: The capability test's permissions, each switched off.
REFUSED: dict[str, bool] = {
    CONF_CAPABILITY_TEST_RESTART: False,
    CONF_CAPABILITY_TEST_EXPORT: False,
    CONF_CAPABILITY_TEST_PV_CUT: False,
}


async def _setup(
    hass: HomeAssistant, unit: MockModbusUnit, **options: Any
) -> MockConfigEntry:
    # Every permission refused unless the test grants it: they default to on,
    # and a restart nobody asked for costs a test its whole deadline.
    options = {**REFUSED, **options}
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


async def _choose(hass: HomeAssistant, mode: str) -> None:
    """Choose what *Diagnosis: start* runs."""
    await hass.services.async_call(
        "select", "select_option", {"entity_id": MODE, "option": mode}, blocking=True
    )


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    """Press a button and wait for the run it starts to finish.

    The run is a background task on purpose -- that is what lets somebody
    navigate away from the device page while it works -- and
    `async_block_till_done` does not wait for those. So the task is awaited
    directly, which is also what keeps a half-finished run from leaking into
    the next test.
    """
    entry = next(iter(hass.config_entries.async_entries(DOMAIN)))
    if "." not in entity_id:
        await _choose(hass, entity_id)
        entity_id = START
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )
    task = entry.runtime_data.diagnosis._task
    if task is not None:
        await task
    await hass.async_block_till_done()


# -- who may write ----------------------------------------------------------


async def test_the_diagnosis_button_never_writes(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Part A reads. That is the whole promise of the button beside this one.

    Asserted on the registers rather than on a flag: a diagnosis that wrote one
    word would be a diagnosis that wrote, whatever the code said it was doing.
    """
    entry = await _setup(hass, ready_unit)
    before = dict(ready_unit.holding)

    await _press(hass, DIAGNOSIS_BUTTON)

    assert ready_unit.holding == before
    assert entry.runtime_data.diagnosis.state.document is not None
    assert "capability_test" not in entry.runtime_data.diagnosis.state.document


async def test_the_capability_test_button_writes_and_puts_everything_back(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """And the document it leaves carries both halves, in one file."""
    entry = await _setup(hass, ready_unit)

    await _press(hass, CONTROL_BUTTON)

    document = entry.runtime_data.diagnosis.state.document
    assert document is not None
    block = document["capability_test"]
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
    assert "capability_test" not in report["diagnosis"]


async def test_the_action_refuses_a_second_run(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Two runs writing at once would restore each other's probe values."""
    from homeassistant.exceptions import HomeAssistantError

    entry = await _setup(hass, ready_unit)
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    entry.runtime_data.diagnosis.async_start(capability_test=True)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "run_capability_test", {"device_id": device.id}, blocking=True
        )
    await hass.async_block_till_done()


# -- the progress bar -------------------------------------------------------


async def test_one_bar_covers_both_parts_and_never_goes_backwards(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Both halves state their step count before either starts.

    That is what makes a single honest bar possible. A bar that reset between
    the parts, or a total that grew halfway through, would be worse than no bar
    -- the lesson `diagnosis_document.async_build` already carries in a comment.
    """
    entry = await _setup(hass, ready_unit)
    seen: list[float] = []
    parts: set[str] = set()

    runner = entry.runtime_data.diagnosis
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
    await _setup(hass, ready_unit, **{CONF_CAPABILITY_TEST_RESTART: True})

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
    from custom_components.sungrow_modbus.capability_test import _store
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
    from custom_components.sungrow_modbus.capability_test import async_leftover
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
    from custom_components.sungrow_modbus.capability_test import _store

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
    from custom_components.sungrow_modbus.capability_test import CapabilityTestRunner

    entry = await _setup(hass, ready_unit)
    # An entry whose options were never saved: what a new install runs with.
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        hass.config_entries.async_update_entry(entry, options={})
        await hass.async_block_till_done()
    options = CapabilityTestRunner(hass, entry)._options()

    assert options.allow_dark is True
    # The others are the owner's to refuse: granted until switched off.
    assert options.restart is True
    assert options.enable_export_limit is True
    assert options.cut_pv is True


async def test_a_permission_switched_off_stays_off(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """The opt-out: a switch the owner turned off is what the run gets."""
    from custom_components.sungrow_modbus.capability_test import CapabilityTestRunner

    entry = await _setup(
        hass,
        ready_unit,
        **{
            CONF_CAPABILITY_TEST_RESTART: False,
            CONF_CAPABILITY_TEST_EXPORT: False,
            CONF_CAPABILITY_TEST_PV_CUT: False,
        },
    )
    options = CapabilityTestRunner(hass, entry)._options()

    assert options.restart is False
    assert options.enable_export_limit is False
    assert options.cut_pv is False


async def test_the_action_can_ask_for_forced_startup_alone(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """`forced_startup` reaches part B's options, and nothing else asks for it."""
    from custom_components.sungrow_modbus.capability_test import CapabilityTestRunner

    entry = await _setup(hass, ready_unit)
    assert CapabilityTestRunner(hass, entry)._options().forced_startup is False
    assert (
        CapabilityTestRunner(hass, entry, forced_startup=True)._options().forced_startup
        is True
    )

    runner = entry.runtime_data.diagnosis
    device = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)[0]
    with patch.object(runner, "async_start", return_value=True) as start:
        await hass.services.async_call(
            DOMAIN,
            "run_capability_test",
            {"device_id": device.id, "forced_startup": True},
            blocking=True,
        )
    start.assert_called_once_with(capability_test=True, forced_startup=True)


# -- runs kept over a day ---------------------------------------------------

STATUS = "sensor.sh10rt_diagnosis_test_summary"
CLEAR_BUTTON = "button.sh10rt_diagnosis_tests_clear_history"
#: The counters' entity-id endings, one per `ledger.BUCKETS` entry.
COUNTS = ("passed", "failed", "not_supported", "inconclusive", "not_run_yet")


async def test_runs_are_kept_folded_and_survive_a_reload(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Two runs at two moments are one document, and a restart keeps them.

    A situation-dependent check -- the import limit needs a charge drawn from
    the grid -- is answered by one run of several, so the runs are kept
    rather than each replacing the last.
    """
    entry = await _setup(hass, ready_unit)

    await _press(hass, CONTROL_BUTTON)
    await _press(hass, CONTROL_BUTTON)

    block = entry.runtime_data.diagnosis.state.document["capability_test"]
    assert block["schema"] == 3
    assert len(block["runs"]) == 2
    assert all(run["read_at"] for run in block["runs"])
    assert block["readback"]
    state = hass.states.get(STATUS)
    assert state is not None
    assert " · 2 runs" in state.state
    assert len(state.state) <= 255
    assert state.attributes["runs"] == 2
    assert state.attributes["log"]
    assert state.attributes["running_since"] is None
    total = state.attributes["total"]
    counted = 0
    for bucket in COUNTS:
        count = hass.states.get(f"sensor.sh10rt_diagnosis_tests_{bucket}")
        assert count is not None
        number, of = count.state.split("/")
        assert int(of) == total
        assert len(count.attributes["checks"]) == int(number)
        counted += int(number)
    assert counted == total
    notifications = persistent_notification._async_get_or_create_notifications(hass)
    assert f"{DOMAIN}_capability_ledger_{entry.entry_id}" in notifications

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    kept = entry.runtime_data.diagnosis.state.capability_test
    assert kept is not None
    assert len(kept["runs"]) == 2
    assert hass.states.get(STATUS).attributes["runs"] == 2


def test_the_elapsed_time_reads_in_minutes_and_hours() -> None:
    start = dt_util.now()
    assert elapsed(start, start + timedelta(seconds=59)) == "<1 min"
    assert elapsed(start, start + timedelta(minutes=12, seconds=30)) == "12 min"
    assert elapsed(start, start + timedelta(minutes=65)) == "1 h 05 min"
    assert elapsed(start, start - timedelta(minutes=1)) == "<1 min"


async def test_the_summary_says_how_long_an_extended_run_is_running(
    hass: HomeAssistant, ready_unit: MockModbusUnit, freezer: FrozenDateTimeFactory
) -> None:
    """Counted from the press, moved on every minute, and gone when it ends.

    A read-only run is not a test run: the summary does not time it.
    """
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis

    runner._set(running=True, extended=False, started=dt_util.now())
    await hass.async_block_till_done()
    assert not hass.states.get(STATUS).state.startswith("running")

    runner._set(running=True, extended=True, started=dt_util.now())
    await hass.async_block_till_done()
    state = hass.states.get(STATUS)
    assert state.state == "running <1 min · no runs kept"
    assert state.attributes["running_since"] == runner.state.started.isoformat()

    freezer.tick(timedelta(minutes=12))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running 12 min · no runs kept"

    runner._set(running=False)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "no runs kept"
    assert hass.states.get(STATUS).attributes["running_since"] is None
    for bucket in COUNTS:
        assert hass.states.get(f"sensor.sh10rt_diagnosis_tests_{bucket}").state == (
            "unknown"
        )


async def test_a_read_only_run_carries_the_kept_runs_forward(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A new reading does not throw away a day's writes; they are dated."""
    entry = await _setup(hass, ready_unit)
    await _press(hass, CONTROL_BUTTON)
    before = dict(ready_unit.holding)

    await _press(hass, DIAGNOSIS_BUTTON)

    assert ready_unit.holding == before
    document = entry.runtime_data.diagnosis.state.document
    assert len(document["capability_test"]["runs"]) == 1


async def test_the_clear_button_forgets_every_run(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """And a reload afterwards finds nothing to fold back in."""
    entry = await _setup(hass, ready_unit)
    await _press(hass, CONTROL_BUTTON)

    await _press(hass, CLEAR_BUTTON)

    assert entry.runtime_data.diagnosis.state.capability_test is None
    assert hass.states.get(STATUS).state == "no runs kept"
    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.runtime_data.diagnosis.state.capability_test is None


# -- auto repeat ---------------------------------------------------------------


async def _auto_repeat(hass: HomeAssistant, on: bool) -> None:
    """Start auto repeat from the mode select, or stop it."""
    entry = next(iter(hass.config_entries.async_entries(DOMAIN)))
    if on:
        await _choose(hass, "extended_auto_repeat")
    await hass.services.async_call(
        "button", "press", {"entity_id": START if on else STOP}, blocking=True
    )
    task = entry.runtime_data.diagnosis._task
    if task is not None:
        await task
    await hass.async_block_till_done()


async def test_auto_repeat_runs_at_once_then_waits_out_the_gap(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Start is the leave: a first run starts, and the next waits for the next slot."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    assert not runner.continuous.active

    await _auto_repeat(hass, True)

    assert runner.continuous.active
    assert len(runner.state.capability_test["runs"]) == 1
    assert runner.continuous.runs_started == 1
    assert hass.states.get("sensor.sh10rt_diagnosis_test_runs").state == "1"
    assert hass.states.get(START).state == STATE_UNAVAILABLE

    runner.continuous._async_tick(dt_util.utcnow())
    await hass.async_block_till_done()
    assert runner._task.done()
    assert len(runner.state.capability_test["runs"]) == 1
    assert "the next run at" in hass.states.get(STATUS).attributes["continuous_waiting"]
    # Waiting is visible where a person looks, and the clock says when.
    assert hass.states.get(STEP).state.startswith(
        "waiting for changed test conditions: "
    )
    next_start = hass.states.get("sensor.sh10rt_diagnosis_next_attempt").state
    assert next_start not in ("unknown", "unavailable")

    await _auto_repeat(hass, False)
    assert not runner.continuous.active
    assert hass.states.get("sensor.sh10rt_diagnosis_next_attempt").state == "unknown"


async def test_auto_repeat_leaves_out_what_is_established_and_the_restart(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A second auto run writes only for what is missing, and never restarts again."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    await _auto_repeat(hass, True)
    established = ledger.established(runner.state.capability_test)
    assert established

    later = dt_util.utcnow() + timedelta(minutes=30)
    with patch(
        "custom_components.sungrow_modbus.continuous.ledger.due",
        return_value=["another run"],
    ):
        runner.continuous._async_tick(later)
    await runner._task
    await hass.async_block_till_done()

    _first, second = runner.state.capability_test["runs"]
    assert set(second["conditions"]["skipped_established"]) == established
    assert not {row["field"] for row in second["readback"]} & established
    if ledger.RESTART in established:
        assert not second.get("restart")
    await _auto_repeat(hass, False)


async def test_auto_repeat_turns_skipping_completed_tests_on(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Auto repeat always skips them, and the switch shows it."""
    entry = await _setup(hass, ready_unit)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SKIP}, blocking=True
    )
    assert hass.states.get(SKIP).state == "off"

    await _auto_repeat(hass, True)
    await hass.async_block_till_done()

    assert hass.states.get(SKIP).state == "on"
    assert entry.runtime_data.diagnosis.skip_established

    # Off would show something auto repeat does not do: refused, with why.
    with pytest.raises(ServiceValidationError) as refused:
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": SKIP}, blocking=True
        )
    assert refused.value.translation_key == ("skip_completed_tests_during_auto_repeat")
    assert hass.states.get(SKIP).state == "on"
    await _auto_repeat(hass, False)


async def test_auto_repeat_is_off_after_a_reload(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A restart never resumes writing by itself; the chosen mode is kept."""
    entry = await _setup(hass, ready_unit)
    await _auto_repeat(hass, True)

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert not entry.runtime_data.diagnosis.continuous.active
    assert hass.states.get(MODE).state == "extended_auto_repeat"
    assert entry.runtime_data.diagnosis.state.running is False


async def test_auto_repeat_stops_when_nothing_is_left_to_wait_for(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Once every check a moment can answer is answered, it switches itself off."""
    entry = await _setup(hass, ready_unit)
    await _auto_repeat(hass, True)
    runner = entry.runtime_data.diagnosis

    with (
        patch(
            "custom_components.sungrow_modbus.continuous.ledger.awaited",
            return_value=[],
        ),
        patch.object(runner.plausibility, "unsettled", return_value=[]),
    ):
        runner.continuous._async_tick(dt_util.utcnow())
    await hass.async_block_till_done()

    assert not runner.continuous.active
    assert "nothing left" in hass.states.get(STATUS).attributes["continuous_waiting"]


async def test_auto_repeat_keeps_watching_the_readings(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """No run is awaited, but a plausibility check is unsettled: it stays on."""
    entry = await _setup(hass, ready_unit)
    await _auto_repeat(hass, True)
    runner = entry.runtime_data.diagnosis

    with (
        patch(
            "custom_components.sungrow_modbus.continuous.ledger.awaited",
            return_value=[],
        ),
        patch.object(runner, "async_start") as start,
    ):
        runner.continuous._async_tick(dt_util.utcnow())
    await hass.async_block_till_done()

    assert runner.continuous.active
    assert not start.called
    waiting = hass.states.get(STATUS).attributes["continuous_waiting"]
    assert waiting.startswith("watching the readings for ")


async def test_the_tick_feeds_the_readings_and_the_counters_count_them(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Each tick is an observation; its checks join the test counters."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    await _auto_repeat(hass, True)
    observed = runner.plausibility.observations
    assert observed >= 1

    runner.continuous._async_tick(dt_util.utcnow())
    await hass.async_block_till_done()
    assert runner.plausibility.observations == observed + 1

    rows = runner.plausibility.summary()
    assert rows
    view = runner.tests
    assert view is not None
    assert set(rows) <= set(view["summary"])
    # The runs' own block is not touched: a run publishes it alone.
    assert not set(rows) & set(
        (runner.state.capability_test or {}).get("summary") or {}
    )


async def test_clearing_the_history_forgets_the_readings_too(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """One button starts a collection afresh, readings included."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    await _auto_repeat(hass, True)
    assert runner.plausibility.observations
    await runner.async_clear_ledger()
    assert runner.plausibility.observations == 0


# -- stopping a run -------------------------------------------------------------


async def test_stop_during_the_capability_test_puts_everything_back(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Stop ends part B at its next check, keeps the run and restores every word."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    before = dict(ready_unit.holding)
    stopped = False

    original = runner._on_progress

    def stop_in_part_b(fraction: float, step: str) -> None:
        nonlocal stopped
        original(fraction, step)
        if (
            not stopped
            and runner._capability_runner is not None
            and ", writing " in step
        ):
            stopped = True
            runner.async_stop()

    with patch.object(runner, "_on_progress", stop_in_part_b):
        await _press(hass, CONTROL_BUTTON)

    assert stopped
    assert runner.state.stopped is True
    assert runner.state.error is None
    run = runner.state.capability_test["runs"][-1]
    assert run["conditions"].get("stopped") is True
    assert not run.get("restart")
    # An unseeded address reads 0 on the mock, so a 0 written back is the word
    # the snapshot read.
    assert {
        address: word
        for address, word in ready_unit.holding.items()
        if before.get(address, 0) != word
    } == {}, "every word is back"
    assert hass.states.get(STEP).state == "stopped"


async def test_stop_during_the_reading_part_cancels_it(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Part A only reads, so Stop simply ends it, with no document."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    holding = asyncio.Event()

    async def _slow(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        await holding.wait()
        raise AssertionError("never reached")

    with patch(
        "custom_components.sungrow_modbus.diagnosis_document.async_build", _slow
    ):
        assert runner.async_start() is True
        await hass.async_block_till_done()
        assert hass.states.get(STOP).state != STATE_UNAVAILABLE
        await hass.services.async_call(
            "button", "press", {"entity_id": STOP}, blocking=True
        )
        await asyncio.wait([runner._task])
        await hass.async_block_till_done()

    assert runner.state.running is False
    assert runner.state.stopped is True
    assert runner.state.document is None
    assert hass.states.get(STEP).state == "stopped"


async def test_start_announces_the_run_in_a_notification(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A button shows no text, so Start says what to expect where it can."""
    await _setup(hass, ready_unit)
    shown: list[str] = []
    with patch(
        "custom_components.sungrow_modbus.diagnosis.persistent_notification.async_create",
        side_effect=lambda _hass, message, **_kw: shown.append(message),
    ):
        await _press(hass, CONTROL_BUTTON)
    assert any("you can leave this page" in text for text in shown)
    assert any("do not restart Home Assistant" in text for text in shown)


# -- leaving out established checks ------------------------------------------

SKIP = "switch.sh10rt_diagnosis_skip_completed_tests"


async def test_skipping_established_checks_narrows_the_next_run(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Off, a run is the full test; on, it writes only for what is missing."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    assert hass.states.get(SKIP).state == "on"  # on by default
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SKIP}, blocking=True
    )

    await _press(hass, CONTROL_BUTTON)
    established = ledger.established(runner.state.capability_test)
    assert established

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": SKIP}, blocking=True
    )
    assert hass.states.get(SKIP).state == "on"
    await _press(hass, CONTROL_BUTTON)

    _first, second = runner.state.capability_test["runs"]
    assert set(second["conditions"]["skipped_established"]) == established
    assert not {row["field"] for row in second["readback"]} & established
    assert not {row["check"] for row in second["effects"]} & established
    # The fold keeps what the first run established.
    assert ledger.established(runner.state.capability_test) >= established


async def test_skipping_established_checks_survives_a_reload(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """It gives no leave to write, so unlike auto repeat it is kept."""
    entry = await _setup(hass, ready_unit)
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SKIP}, blocking=True
    )

    with patch(
        "custom_components.sungrow_modbus.async_get_unit", return_value=ready_unit
    ):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get(SKIP).state == "off"
    assert not entry.runtime_data.diagnosis.skip_established


async def test_next_start_is_the_next_slot_from_the_press(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Slots run every 30 minutes from the press of Start, with no daily cap."""
    from custom_components.sungrow_modbus.continuous import INTERVAL

    entry = await _setup(hass, ready_unit)
    continuous = entry.runtime_data.diagnosis.continuous
    assert continuous.next_start(dt_util.utcnow()) is None, "off"

    await _auto_repeat(hass, True)
    pressed = continuous.started_at
    assert pressed is not None
    assert continuous.next_start(pressed) == pressed + INTERVAL

    # Late in the day, many slots on: still one run per slot, never a day's cap.
    much_later = pressed + 40 * INTERVAL + timedelta(minutes=3)
    with patch(
        "custom_components.sungrow_modbus.continuous.ledger.due",
        return_value=["another run"],
    ):
        continuous._async_tick(much_later)
    await entry.runtime_data.diagnosis._task
    await hass.async_block_till_done()
    assert continuous.runs_started == 2
    assert continuous.next_start(much_later) == pressed + 41 * INTERVAL

    # A slot whose house never allows a run names no time: the house decides.
    continuous._last_slot = None
    assert continuous.next_start(much_later) is None
    await _auto_repeat(hass, False)


async def test_auto_repeat_waits_while_the_inverter_is_not_running(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """Low-SoC Standby at night starts no run, and spends no slot."""
    entry = await _setup(hass, ready_unit)
    continuous = entry.runtime_data.diagnosis.continuous
    await _auto_repeat(hass, True)
    assert continuous.started_at is not None
    later = continuous.started_at + timedelta(minutes=31)

    with (
        patch.object(continuous, "_inverter_running", return_value=False),
        patch(
            "custom_components.sungrow_modbus.continuous.ledger.due",
            return_value=["another run"],
        ),
    ):
        continuous._async_tick(later)
    await hass.async_block_till_done()

    assert continuous.runs_started == 1
    assert continuous.waiting == "waiting for the inverter to run"
    await _auto_repeat(hass, False)


async def test_auto_repeat_keeps_quiet_after_a_run(
    hass: HomeAssistant, ready_unit: MockModbusUnit
) -> None:
    """A slot that opens just as the last run ended waits for the link to settle."""
    entry = await _setup(hass, ready_unit)
    runner = entry.runtime_data.diagnosis
    continuous = runner.continuous
    await _auto_repeat(hass, True)
    assert continuous.started_at is not None
    slot = continuous.started_at + timedelta(minutes=30)
    runner.state = dataclasses.replace(
        runner.state, finished=slot - timedelta(seconds=30)
    )

    with patch(
        "custom_components.sungrow_modbus.continuous.ledger.due",
        return_value=["another run"],
    ):
        continuous._async_tick(slot)
    await hass.async_block_till_done()

    assert continuous.runs_started == 1
    assert "quiet" in continuous.waiting
    await _auto_repeat(hass, False)
