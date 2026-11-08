"""The device page's diagnosis controls: the buttons, and the things to watch.

These are the entities that replace the options flow's spinner. They are
deliberately ordinary Home Assistant entities rather than anything clever,
because that is what buys the things a modal dialog could not do:

- the **history** of `diagnosis_step` is the log of what was probed, in order,
  with timestamps, kept by the recorder like any other state;
- `diagnosis_progress` is a number, so it draws a bar on a dashboard, and can
  be watched by an automation on a link where a diagnosis takes a quarter of an
  hour;
- a button can be pressed by a script, so a maintainer walking somebody
  through a problem can say "run this" rather than "click through there".

Every one is `EntityCategory.DIAGNOSTIC`: they describe the integration
rather than the inverter, and they belong under the diagnostic heading of
the device page rather than among the readings. Every name starts
*Diagnosis:* (`naming.py`), because that card sorts by name.

They exist in a diagnostics-only entry, and only there: it has no other
entities at all, and these are the reason it was set up. An ordinary entry
reaches the same runs through the `run_diagnosis` and `run_capability_test`
actions, which leave no entities behind.

What runs is chosen in *Diagnosis: mode* and started by *Diagnosis: start*;
*Diagnosis: stop* ends a run, and auto repeat, early -- everything a run
changed is still put back.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import ledger

from .const import (
    DIAGNOSIS_MODE_AUTO_REPEAT,
    DIAGNOSIS_MODE_EXTENDED,
    DIAGNOSIS_MODE_READ_ONLY,
    DIAGNOSIS_MODES,
    PERMISSION_CAPABILITY_TEST,
)
from .entity import EnglishEntityId
from .services import async_authorize

if TYPE_CHECKING:
    from .coordinator import SungrowRuntimeData
    from .diagnosis import DiagnosisRunner

#: Domain and translation key of every entity in this module.
#:
#: Here rather than in the generator so that adding one cannot forget to name
#: it: `scripts/generate/descriptions.py strings` reads this, and these keys have no
#: legacy name to derive from -- they are named in `naming.OVERRIDES` like the SBR
#: pack's, which are hand-written for the same reason.
DIAGNOSIS_ENTITIES: tuple[tuple[str, str], ...] = (
    ("select", "diagnosis_mode"),
    ("button", "diagnosis_start"),
    ("button", "diagnosis_stop"),
    ("button", "clear_capability_test_history"),
    ("sensor", "diagnosis_progress"),
    ("sensor", "diagnosis_step"),
    ("sensor", "diagnosis_finished"),
    ("sensor", "diagnosis_next_start"),
    ("sensor", "diagnosis_test_runs"),
    ("sensor", "capability_test_status"),
    *(("sensor", f"diagnosis_tests_{bucket}") for bucket in ledger.BUCKETS),
    ("switch", "skip_established_capability_tests"),
)

#: The unique-id suffixes of entities this module no longer makes. Setup
#: removes them from the registry; they were diagnostic, so no history is
#: worth keeping, and a stale "unavailable" button only confuses.
RETIRED_ENTITIES: tuple[tuple[str, str], ...] = (
    ("button", "run_diagnosis"),
    ("button", "run_capability_test"),
    ("switch", "continuous_capability_test"),
)

#: What *Diagnosis: current step* starts with while auto repeat waits.
WAITING = "waiting for changed test conditions"

#: How many log lines the status sensor's attribute carries. The whole log is
#: in the ledger and in Download diagnostics; this is the tail worth a glance.
LOG_LINES = 30

#: The longest a step label may be. Home Assistant refuses to record a state
#: over 255 characters, and a probe label is nowhere near that -- but a
#: failure message inherited from the stack can be, and a diagnosis that
#: silently stopped being recorded is worse than a truncated line.
MAX_STATE = 255

#: How often the test summary rewrites its state while an extended run is in
#: flight, so the time it shows moves on between the run's own updates.
ELAPSED_TICK = timedelta(minutes=1)


def elapsed(started: datetime, now: datetime) -> str:
    """Return how long a run has taken, in whole minutes: `1 h 05 min`."""
    minutes = max(0, int((now - started).total_seconds()) // 60)
    if minutes < 1:
        return "<1 min"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d} min"


def _findings(capability_test: dict[str, Any]) -> int | None:
    """Count the decade findings in part B's block, or None if it never ran."""
    readback = capability_test.get("readback")
    if readback is None:
        return None
    return sum(1 for row in readback if "decade" in str(row.get("verdict", "")))


class DiagnosisEntity(EnglishEntityId):
    """Common wiring: which device, which runner, and how updates arrive.

    Not a `CoordinatorEntity`: a diagnosis is not polled. It is pushed, from the
    reading loop, through one dispatcher signal per config entry -- so the
    entity updates when something actually happened rather than on a timer
    that would be wrong in both directions on a slow link.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: SungrowRuntimeData, key: str) -> None:
        """Attach to the entry's inverter device."""
        self._runner: DiagnosisRunner = runtime_data.diagnosis
        coordinator = runtime_data.inverter_coordinator
        serial = coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_translation_key = key
        self._attr_device_info: DeviceInfo = coordinator.device_info

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; nothing here is keyed on the id.

        Defining it opts this class's add hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11). Before 2026.11 the
        base class has no such method and nothing calls it.
        """
        parent = getattr(super(), "async_entity_id_changed", None)
        if parent is not None:
            parent(old_entity_id)

    async def async_added_to_hass(self) -> None:
        """Listen for diagnosis state changes for as long as this entity lives."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, self._runner.signal, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()


class DiagnosisModeSelect(DiagnosisEntity, SelectEntity, RestoreEntity):
    """What *Diagnosis: start* runs: read-only, one extended test, or auto repeat.

    Restored, because it is a choice rather than a leave: choosing a mode
    starts nothing, and after a restart auto repeat runs only once a person
    presses Start again. A string inverter has no capability test, so it is
    offered read-only alone.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Offer the modes this inverter has."""
        super().__init__(runtime_data, "diagnosis_mode")
        self._attr_options = (
            [DIAGNOSIS_MODE_READ_ONLY]
            if runtime_data.is_string_inverter
            else list(DIAGNOSIS_MODES)
        )
        self._attr_current_option = DIAGNOSIS_MODE_READ_ONLY

    async def async_added_to_hass(self) -> None:
        """Take the last choice back, then listen like every diagnosis entity."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in self.options:
            self._attr_current_option = last.state
        self._runner.mode = self.current_option or DIAGNOSIS_MODE_READ_ONLY

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place: the choice is not keyed on it.

        Declared beside the add hook above, for the reason
        `CapabilityTestStatusSensor.async_entity_id_changed` gives.
        """
        super().async_entity_id_changed(old_entity_id)

    async def async_select_option(self, option: str) -> None:
        """Remember the mode; nothing starts until Start is pressed."""
        self._attr_current_option = option
        self._runner.mode = option
        self.async_write_ha_state()


class DiagnosisStartButton(DiagnosisEntity, ButtonEntity):
    """Start what *Diagnosis: mode* names.

    Worth stating plainly, because Home Assistant gives a button no
    confirmation dialog: in an extended mode, pressing this changes settings on
    the device. It moves the state-of-charge limits, commands a charge and a
    discharge at a power derived from the battery's own rating, and -- where
    the entry's options say it may -- limits export and restarts the
    inverter. Every one of those is put back and read back before the run
    reports success, and anything that could not be put back becomes a repair
    on the next start rather than a line in a log.

    What protects it is therefore not a dialog but the guard list in
    `sungrow_modbus.capability_test`, which refuses the run outright when the
    inverter is not running, when another client is polling, or when the
    battery is at a state of charge that would make a probe value unsafe --
    and the permission below, held exactly as the `run_capability_test`
    action holds it.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what pressing it does."""
        super().__init__(runtime_data, "diagnosis_start")

    @property
    def available(self) -> bool:
        """Unavailable while a run is in flight or auto repeat is on.

        The runner refuses a second run anyway: two at once would interleave
        on one serialized connection, and their writes would restore each
        other's probe values. This is the half of that a person can see.
        """
        return not self._runner.state.running and not self._runner.continuous.active

    async def async_press(self) -> None:
        """Start the chosen mode, if the presser may write where it writes."""
        mode = self._runner.mode
        if mode != DIAGNOSIS_MODE_READ_ONLY:
            await async_authorize(
                self.hass,
                self._context,
                self._runner.entry,
                PERMISSION_CAPABILITY_TEST,
            )
        if mode == DIAGNOSIS_MODE_AUTO_REPEAT:
            self._runner.async_announce_start(mode)
            self._runner.continuous.async_turn_on()
        elif self._runner.async_start(capability_test=mode == DIAGNOSIS_MODE_EXTENDED):
            self._runner.async_announce_start(mode)
        self.async_write_ha_state()


class DiagnosisStopButton(DiagnosisEntity, ButtonEntity):
    """End the run in flight, and auto repeat, putting everything back.

    No permission: stopping writes is never something to be refused.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what pressing it does."""
        super().__init__(runtime_data, "diagnosis_stop")

    @property
    def available(self) -> bool:
        """Available while there is something to stop."""
        return self._runner.state.running or self._runner.continuous.active

    async def async_press(self) -> None:
        """Ask the runner to stop."""
        self._runner.async_stop()


class DiagnosisProgressSensor(DiagnosisEntity, SensorEntity):
    """How far through the current diagnosis is, in percent.

    **No `state_class`, deliberately.** A measurement state class makes the
    recorder keep long-term statistics, and those are the one thing here that
    would outlive the integration: deleting the config entry takes the
    entities, the device and their states with it -- measured -- but
    statistics rows survive their entity and turn into an "entity no longer
    exists" repair for somebody who uninstalled weeks ago. Hourly averages of
    a progress bar are meaningless anyway; what is worth keeping is the
    *step* sensor's plain history, which the recorder purges on its ordinary
    schedule.
    """

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the fraction it reports."""
        super().__init__(runtime_data, "diagnosis_progress")

    @property
    def native_value(self) -> int | None:
        """Percent complete, or None before the first run."""
        return self._runner.state.percent


class DiagnosisStepSensor(DiagnosisEntity, SensorEntity):
    """What the diagnosis is reading right now.

    Its recorded history is the point of it: 19 probes in the order they
    happened, which is what tells a maintainer *where* a slow link stalls
    rather than that it did.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the step it reports."""
        super().__init__(runtime_data, "diagnosis_step")

    @property
    def native_value(self) -> str | None:
        """The current step, what auto repeat waits for, the last failure, or idle."""
        state = self._runner.state
        if state.running:
            return (state.step or f"starting the {state.part or 'diagnosis'}")[
                :MAX_STATE
            ]
        continuous = self._runner.continuous
        if continuous.active:
            return f"{WAITING}: {continuous.waiting}"[:MAX_STATE]
        if state.stopped:
            return "stopped"
        if state.error:
            return f"failed: {state.error}"[:MAX_STATE]
        if state.finished:
            return "finished"
        return "never run"


class DiagnosisResultSensor(DiagnosisEntity, SensorEntity):
    """When the last diagnosis finished, with what it found beside it."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the run it describes."""
        super().__init__(runtime_data, "diagnosis_finished")

    @property
    def native_value(self) -> Any:
        """When the last run ended, or None if none has."""
        return self._runner.state.finished

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The numbers a summary line needs, without a second entity each."""
        state = self._runner.state
        capability_test = state.capability_test or {}
        return {
            "fields_read": state.fields_read,
            "error": state.error,
            "has_document": state.document is not None,
            # None rather than 0 when part B did not run, so a reader cannot
            # mistake "this run only read" for "the write test found nothing".
            "capability_test_outcome": capability_test.get("outcome_means"),
            "capability_test_findings": _findings(capability_test),
        }


class DiagnosisNextStartSensor(DiagnosisEntity, SensorEntity):
    """When auto repeat may start its next run, where the clock decides it.

    Unknown while it is off, while a run is in flight, and while what decides
    is the house rather than the clock -- `waiting_for` then says what for,
    as *Diagnosis: current step* does.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the start it reports."""
        super().__init__(runtime_data, "diagnosis_next_start")

    @property
    def native_value(self) -> datetime | None:
        """The earliest next start, or None."""
        return self._runner.continuous.next_start(dt_util.utcnow())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """What auto repeat waits for."""
        continuous = self._runner.continuous
        return {"waiting_for": continuous.waiting if continuous.active else None}


class DiagnosisTestRunsSensor(DiagnosisEntity, SensorEntity):
    """How many capability test runs are kept, with how many started today.

    No `state_class`, for the reason `DiagnosisProgressSensor` gives.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the runs it counts."""
        super().__init__(runtime_data, "diagnosis_test_runs")

    @property
    def native_value(self) -> int:
        """The number of kept runs."""
        folded = self._runner.state.capability_test or {}
        return len(folded.get("runs") or [])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Runs auto repeat started today."""
        return {"runs_today": self._runner.continuous.runs_today}


class ClearCapabilityTestHistoryButton(DiagnosisEntity, ButtonEntity):
    """Forget every kept capability test run, to start a collection afresh.

    Writes nothing to the inverter; it empties this entry's ledger. Held to
    the capability test's permission all the same, because what it removes is
    evidence somebody may have spent a day collecting.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what pressing it does."""
        super().__init__(runtime_data, "clear_capability_test_history")

    @property
    def available(self) -> bool:
        """Unavailable while a run is in flight; it is about to add to it."""
        return not self._runner.state.running

    async def async_press(self) -> None:
        """Empty the ledger."""
        await async_authorize(
            self.hass, self._context, self._runner.entry, PERMISSION_CAPABILITY_TEST
        )
        await self._runner.async_clear_ledger()


class CapabilityTestStatusSensor(DiagnosisEntity, SensorEntity):
    """How far a collection of capability test runs has got, and what it awaits.

    The state is one line -- `running 12 min · 14/49 established · 5 runs ·
    waiting for: site import limit, PV generation cut` -- because a state
    stops at 255 characters. The time is counted from the press of an
    extended run, and rewritten every minute while it lasts. The tail of the
    log and each missing check's reason are attributes, kept out of the
    recorder: they grow with every run, and the recorded history of the
    state is already the log over time. The long form is the notification
    the runner rewrites after every run.
    """

    _unrecorded_attributes = frozenset({"still_missing", "log"})

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for the collection it reports."""
        super().__init__(runtime_data, "capability_test_status")
        self._tick: CALLBACK_TYPE | None = None

    def _timing(self) -> bool:
        """Whether an extended run is in flight, which is when time is shown."""
        state = self._runner.state
        return state.running and state.extended and state.started is not None

    async def async_added_to_hass(self) -> None:
        """Listen, start the clock if a run is already going, stop it at removal."""
        await super().async_added_to_hass()
        self.async_on_remove(self._stop_tick)
        self._sync_tick()

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place: the minute clock is not keyed on it.

        Declared here, beside the add hook above, because Home Assistant
        (2026.11 to 2027.11) re-adds a class whose own add hook no
        `async_entity_id_changed` of the same class or a subclass covers.
        """
        super().async_entity_id_changed(old_entity_id)

    @callback
    def _handle_update(self) -> None:
        self._sync_tick()
        super()._handle_update()

    @callback
    def _sync_tick(self) -> None:
        """Run the minute clock exactly while an extended run is in flight."""
        if self._timing():
            if self._tick is None:
                self._tick = async_track_time_interval(
                    self.hass, self._async_minute, ELAPSED_TICK
                )
        else:
            self._stop_tick()

    @callback
    def _stop_tick(self) -> None:
        if self._tick is not None:
            self._tick()
            self._tick = None

    @callback
    def _async_minute(self, _now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """The one-line progress, or that nothing has been kept."""
        state = self._runner.state
        folded = state.capability_test
        if self._timing():
            assert state.started is not None
            prefix = f"running {elapsed(state.started, dt_util.now())} · "
        elif self._runner.continuous.active:
            prefix = f"{WAITING} · "
        else:
            prefix = ""
        if not folded or "summary" not in folded:
            return f"{prefix}no runs kept"
        return prefix + ledger.status_line(folded, limit=MAX_STATE - len(prefix))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The counts, what is missing and why, and the tail of the log."""
        state = self._runner.state
        folded = state.capability_test or {}
        running_since = (
            state.started.isoformat()
            if self._timing() and state.started is not None
            else None
        )
        if "summary" not in folded:
            return {
                **self._runner.continuous.attributes(),
                "running_since": running_since,
                "established": None,
                "total": None,
                "runs": 0,
            }
        established, total = ledger.progress(folded)
        runs = folded.get("runs") or []
        return {
            **self._runner.continuous.attributes(),
            "running_since": running_since,
            "established": established,
            "total": total,
            "runs": len(runs),
            "last_run_at": runs[-1].get("read_at") if runs else None,
            "contradictions": [
                item["name"] for item in folded.get("contradictions") or []
            ],
            "still_missing": folded.get("still_missing") or [],
            "log": ledger.run_lines(folded)[-LOG_LINES:],
        }


class CapabilityTestCountSensor(DiagnosisEntity, SensorEntity):
    """How many of the kept runs' checks ended one way: `17/58`.

    One per bucket of `ledger.BUCKETS`; the five add up to the total. Text
    rather than a number, because the total belongs beside the count and
    differs by model and firmware. The checks themselves are an attribute,
    unrecorded, so the count can be read without opening the summary.
    """

    _unrecorded_attributes = frozenset({"checks"})

    def __init__(self, runtime_data: SungrowRuntimeData, bucket: str) -> None:
        """Name it for the bucket it counts."""
        super().__init__(runtime_data, f"diagnosis_tests_{bucket}")
        self._bucket = bucket

    @property
    def native_value(self) -> str | None:
        """`count/total`, or None while no run is kept."""
        folded = self._runner.state.capability_test or {}
        if "summary" not in folded:
            return None
        _, total = ledger.progress(folded)
        return f"{ledger.counts(folded)[self._bucket]}/{total}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The checks in this bucket, by name."""
        summary = (self._runner.state.capability_test or {}).get("summary") or {}
        return {
            "checks": sorted(
                name
                for name, row in summary.items()
                if ledger.bucket(row.get("verdict")) == self._bucket
            )
        }


class SkipEstablishedCapabilityTestsSwitch(
    DiagnosisEntity, SwitchEntity, RestoreEntity
):
    """Whether a capability test leaves out what earlier runs established.

    On, a single extended run and the action write only for the checks the
    ledger still misses (`ledger.established`), the restart included, so a
    run started at night for the import limit does not write every control
    again. Auto repeat always does, whatever this says. Off, a single run is
    the full test, which is also what can turn up a contradiction between two
    runs. A check two runs disagree on is never left
    out.

    Restored, unlike the continuous switch: it gives no leave to write, it
    only narrows what a run that has leave writes. No permission either way,
    for the same reason.
    """

    def __init__(self, runtime_data: SungrowRuntimeData) -> None:
        """Name it for what a run leaves out."""
        super().__init__(runtime_data, "skip_established_capability_tests")

    async def async_added_to_hass(self) -> None:
        """Take the last state back, then listen like every diagnosis entity."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._runner.skip_established = last.state == "on"

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place: the setting is not keyed on it.

        Declared beside the add hook above, for the reason
        `CapabilityTestStatusSensor.async_entity_id_changed` gives.
        """
        super().async_entity_id_changed(old_entity_id)

    @property
    def is_on(self) -> bool:
        """Whether runs leave out established checks."""
        return self._runner.skip_established

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Leave established checks out of the next runs."""
        self._runner.skip_established = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Run the full test again."""
        self._runner.skip_established = False
        self.async_write_ha_state()
