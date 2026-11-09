"""Running a capability diagnosis from the device page, and saying where it is.

Not in a config flow, because a flow is wrong in three ways a contributor
feels: a modal dialog cannot be left while it works, an indeterminate spinner
says nothing about how long a slow link will take, and a flow has nowhere to
put a *download* button.

So it lives here, as state a device page can render. One runner per config
entry, holding what the last run did and what the current one is doing, and
telling the entities when either changes.

Three things this buys that a flow could not:

- **It survives navigation.** Press the button, go and look at something
  else, come back. The run is a task on the event loop, not a dialog.
- **The step is a state**, so the recorder keeps it. The history of the
  "current step" sensor *is* the log of what was probed and in what order --
  which is the thing a maintainer asks for when a diagnosis stalls on one
  house's link and nowhere else.
- **A document can be downloaded**, because a signed URL can be put in a
  notification. See `download.py`.

**A run has two parts.** Part A is the capability diagnosis and reads only. Part
B is the capability test, which **writes** to each control and puts it back, and
runs only when a caller asks for it by name -- the capability test button and its
action, and nothing else. One runner owns both because they share one
serialized connection, and a Sungrow grants very few sessions: two runs at once
would interleave, and with writes in the picture that means restoring each
other's probe values.

Nothing here talks Modbus. `diagnosis_document.async_build` does the reading,
`capability_test.CapabilityTestRunner` does the writing, and both call back with a
fraction and a label; this turns those into state and splits one progress bar
between them.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from sungrow_modbus import block_test, string_inverter
from sungrow_modbus.capability_test import (
    Options as ControlOptions,
    ledger,
    planned_steps as capability_test_steps,
)
from sungrow_modbus.capability_test.plausibility import FIELDS, Plausibility
from sungrow_modbus.wallbox import (
    ledger as wallbox_ledger,
    plausibility as wallbox_plausibility,
)

from .const import (
    CAPABILITY_TEST_PERMISSION_DEFAULT,
    CONF_CAPABILITY_TEST_CHARGE_WINDOW,
    CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
    CONF_CAPABILITY_TEST_EXPORT,
    CONF_CAPABILITY_TEST_IMPORT_LIMIT,
    CONF_CAPABILITY_TEST_PV_CUT,
    CONF_CAPABILITY_TEST_RESTART,
    CONF_DIAGNOSIS_DUMP,
    DEFAULT_DIAGNOSIS_DUMP,
    DIAGNOSIS_ISSUE_URL,
    DIAGNOSIS_MODE_AUTO_REPEAT,
    DIAGNOSIS_MODE_EXTENDED,
    DIAGNOSIS_MODE_READ_ONLY,
    DOMAIN,
    LINK_VALID,
)
from .continuous import ContinuousCapabilityTest
from .wallbox_capability_test import (
    PLAUSIBILITY_SAVE_DELAY as WALLBOX_PLAUSIBILITY_SAVE_DELAY,
    WallboxTestRunner,
    async_ledger_add as async_wallbox_ledger_add,
    async_ledger_clear as async_wallbox_ledger_clear,
    async_ledger_runs as async_wallbox_ledger_runs,
    async_plausibility_load as async_wallbox_plausibility_load,
    check_options as wallbox_check_options,
    consented as wallbox_consented,
    firmware_of as wallbox_firmware_of,
    live_of as wallbox_live_of,
    plausibility_store as wallbox_plausibility_store,
    readings_of as wallbox_readings_of,
)

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)

#: Dispatcher signal, per entry, fired whenever the state below changes.
#: Entities subscribe to it rather than polling the runner.
SIGNAL_DIAGNOSIS = "sungrow_modbus_diagnosis_{}"

#: The two halves of a full run. Part A asks what is here and answers it
#: entirely by reading; part B asks whether writing to it works, which cannot
#: be answered without writing. One runner owns both because they share one
#: serialized connection, and a Sungrow grants very few sessions.
PART_A = "diagnosis"
PART_B = "capability test"

#: A run of the wallbox's own checks: after part B in an extended run, or alone
#: when auto repeat finds one due. Never at the same time as either.
PART_WALLBOX = "wallbox capability test"


@dataclass(frozen=True)
class DiagnosisState:
    """What the diagnosis is doing, or last did.

    Frozen, and replaced rather than mutated, so an entity reading it while a
    probe updates it can never see half of one state -- the callback runs on
    the event loop between awaits, which is exactly where a mutable version
    would tear.
    """

    running: bool = False
    """True from the moment the button is pressed until the task ends."""

    fraction: float | None = None
    """Progress from 0.0 to 1.0, or None when nothing has run yet.

    Derived from a count of reads, not from time: a diagnosis over a VPN takes
    twenty times as long as one over a cable, and the count is the only part
    of that which is knowable in advance.
    """

    step: str | None = None
    """What is being read right now, in the words the document uses."""

    started: datetime | None = None
    finished: datetime | None = None

    extended: bool = False
    """Whether the run started (or last started) includes part B.

    Set at the start rather than read from `part`, because part A runs first
    in an extended run too, and the test summary counts its time from the
    press, not from the first write.
    """

    fields_read: int | None = None
    """Decoded fields in the finished document, for the summary line."""

    error: str | None = None
    """Why the last run failed, or None. Kept until the next run starts."""

    part: str | None = None
    """Which half is running: `PART_A` reads, `PART_B` writes.

    Recorded as state rather than inferred from the step label, because the
    distinction is the one a person most needs while it is happening -- part A
    only looks at their inverter and part B changes its settings, and somebody
    deciding whether to interrupt a run deserves to know which is in front of
    them without reading the label carefully.
    """

    stopped: bool = False
    """Whether the last run was ended early by its owner (`async_stop`)."""

    capability_test: dict[str, Any] | None = field(default=None, repr=False)
    """Part B's result, or None when the last run only read."""

    document: dict[str, Any] | None = field(default=None, repr=False)
    """The last document, held in memory for the download view to serve.

    Not written to disk. It carries a stand-in serial rather than a real one,
    but it is still somebody's installation, and a file in `www/` is served
    to anyone who can reach Home Assistant.
    """

    @property
    def percent(self) -> int | None:
        """The fraction as whole percent, which is what a sensor shows."""
        if self.fraction is None:
            return None
        return round(self.fraction * 100)


class DiagnosisRunner:
    """Owns one entry's diagnosis: starts it, tracks it, announces it."""

    def __init__(self, hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
        """Prepare a runner. Nothing runs until `async_start`."""
        self.hass = hass
        self.entry = entry
        self.state = DiagnosisState()
        self._task: asyncio.Task[None] | None = None
        #: Whether this run's part B is the forced startup check alone.
        self._forced_startup = False
        self._lapsed: CALLBACK_TYPE | None = None
        #: Every kept capability test run, folded into one block, or None.
        #: Survives a read-only run and a restart (`capability_test.LEDGER_KEY`).
        self._folded: dict[str, Any] | None = None
        #: Runs started on their own while a person has switched it on.
        self.continuous = ContinuousCapabilityTest(hass, entry, self)
        #: Whether a capability test leaves out the checks earlier runs
        #: established, for single runs and the action. Set by its switch,
        #: which restores it; on until someone turns it off. Auto-repeat runs
        #: always leave them out.
        self.skip_established = True
        #: What *Diagnosis: start* runs; set by the mode select.
        self.mode = DIAGNOSIS_MODE_READ_ONLY
        #: Whether the owner asked the run in flight to end (`async_stop`).
        self._stop_requested = False
        #: Part B's runner while it is in flight, so a stop can reach it.
        self._capability_runner: Any = None
        #: The readings checked against each other, fed by auto repeat's
        #: tick and kept per firmware (`capability_test.PLAUSIBILITY_KEY`).
        self.plausibility = Plausibility()
        self._plausibility_firmware: str | None = None
        #: The wallbox's kept runs, folded (`sungrow_modbus.wallbox.ledger`).
        self._wallbox_folded: dict[str, Any] | None = None
        #: The wallbox's readings checked against each other, kept per firmware.
        self.wallbox_plausibility = wallbox_plausibility.WallboxPlausibility()
        self._wallbox_firmware: str | None = None

    @property
    def tests(self) -> dict[str, Any] | None:
        """The kept runs, folded, with the readings' checks counted in.

        What the counters, the test summary and the notification show. The
        document a run publishes carries the two apart: `capability_test` is
        the runs, `plausibility` the readings.
        """
        return ledger.with_plausibility(
            self.state.capability_test,
            {**self.plausibility.summary(), **self._wallbox_rows()},
        )

    @property
    def wallbox_present(self) -> bool:
        """Whether this endpoint has a wallbox the tests can reach."""
        return self.entry.runtime_data.wallbox is not None

    def _wallbox_device(self) -> Any:
        coordinator = self.entry.runtime_data.wallbox
        assert coordinator is not None
        return coordinator.device

    def _wallbox_rows(self) -> dict[str, dict[str, Any]]:
        """Return the wallbox's checks as summary rows, to count with the rest."""
        if not self.wallbox_present:
            return {}
        rows = self.wallbox_plausibility.summary()
        if wallbox_consented(self.entry):
            rows = {
                **wallbox_ledger.summary_rows(
                    self._wallbox_folded, wallbox_check_options(self.entry)
                ),
                **rows,
            }
        return rows

    def wallbox_awaited(self) -> list[tuple[str, str]]:
        """Return the wallbox checks still unanswered, empty without leave."""
        if not self.wallbox_present or not wallbox_consented(self.entry):
            return []
        return wallbox_ledger.awaited(
            self._wallbox_folded, wallbox_check_options(self.entry)
        )

    def wallbox_due(self) -> list[str]:
        """Return the unanswered checks the wallbox's state allows right now."""
        if not self.wallbox_awaited():
            return []
        return wallbox_ledger.due(
            self._wallbox_folded,
            wallbox_live_of(self._wallbox_device()),
            wallbox_check_options(self.entry),
        )

    def _wallbox_established(self) -> frozenset[str]:
        rows = (self._wallbox_folded or {}).get("checks") or {}
        return frozenset(name for name, row in rows.items() if row["established"])

    @callback
    def async_observe(self, now: datetime) -> None:
        """Feed the last polled readings to the plausibility checks.

        Only between runs: a run holds polling off, and the readings it
        leaves behind are minutes old.
        """
        if self.state.running:
            return
        if not self.entry.runtime_data.is_string_inverter:
            self._async_observe_inverter(now)
        if self.wallbox_present:
            self._async_observe_wallbox(now)

    @callback
    def _async_observe_wallbox(self, now: datetime) -> None:
        """Feed the wallbox's polled readings, and the inverter's load beside them."""
        reading = wallbox_readings_of(self._wallbox_device())
        if all(value is None for value in reading.values()):
            return
        load: float | None = None
        if not self.entry.runtime_data.is_string_inverter:
            try:
                found = self._device().field("load_power")
            except AttributeError:
                found = None
            load = None if found is None else float(found)
        self.wallbox_plausibility.observe(
            wallbox_plausibility.values(reading, load), dt_util.as_local(now)
        )
        firmware = self._wallbox_firmware
        collection = self.wallbox_plausibility
        wallbox_plausibility_store(self.hass, self.entry).async_delay_save(
            lambda: {"firmware": firmware, "state": collection.as_dict()},
            WALLBOX_PLAUSIBILITY_SAVE_DELAY,
        )

    @callback
    def _async_observe_inverter(self, now: datetime) -> None:
        """Feed the inverter's polled readings."""
        device = self._device()
        values: dict[str, float | None] = {}
        for name in FIELDS:
            try:
                value = device.field(name)
            except AttributeError:
                value = None
            values[name] = None if value is None else float(value)
        if all(value is None for value in values.values()):
            return
        self.plausibility.observe(values, dt_util.as_local(now))
        self._async_save_plausibility()

    @callback
    def _async_save_plausibility(self) -> None:
        """Save the plausibility state, lazily."""
        from .capability_test import PLAUSIBILITY_SAVE_DELAY, plausibility_store

        firmware = self._plausibility_firmware
        collection = self.plausibility
        plausibility_store(self.hass, self.entry).async_delay_save(
            lambda: {"firmware": firmware, "state": collection.as_dict()},
            PLAUSIBILITY_SAVE_DELAY,
        )

    @property
    def signal(self) -> str:
        """The dispatcher signal this runner's entities listen on."""
        return SIGNAL_DIAGNOSIS.format(self.entry.entry_id)

    @callback
    def async_notify(self) -> None:
        """Tell the entities something changed that is not in the state."""
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def _set(self, **changes: Any) -> None:
        """Replace the state and tell the entities, in that order."""
        self.state = replace(self.state, **changes)
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def async_start(
        self, *, capability_test: bool = False, forced_startup: bool = False
    ) -> bool:
        """Begin a run. Returns False when one is already running.

        `capability_test` adds part B, which **writes** to every control the
        integration can write to and puts each one back. It is off unless a
        caller asks for it, and the only caller that asks is the capability test
        button and its matching action -- so the diagnosis button, the options
        flow and the diagnostics download cannot acquire the power to write by
        inheriting a default.

        Refusing rather than queueing: two runs at once would interleave on one
        serialized connection, and a Sungrow grants few sessions. With part B
        in the picture that stops being a politeness -- interleaved *writes*
        are how two runs would restore each other's probe values.

        `forced_startup` makes part B the forced startup check alone, which
        runs only on an inverter in low-SoC standby.
        """
        if self._task is not None and not self._task.done():
            _LOGGER.debug("Diagnosis already running for %s", self.entry.title)
            return False
        if capability_test and self.entry.runtime_data.is_string_inverter:
            # Nothing here writes to an SG: its holding registers are not the
            # hybrid's, and no write to one has been watched.
            _LOGGER.warning(
                "%s is a string inverter; the capability test writes only to a "
                "hybrid, so it was not started",
                self.entry.title,
            )
            return False

        # A run already announced has a timer waiting to mark its link
        # lapsed. Left alone it would fire later and overwrite *this* run's
        # notification -- same `notification_id` -- with the words "the link
        # has expired", on a link that is minutes old.
        self._async_cancel_lapse()
        self._forced_startup = capability_test and forced_startup
        self._stop_requested = False

        self._set(
            running=True,
            fraction=0.0,
            step=None,
            started=dt_util.now(),
            finished=None,
            extended=capability_test,
            error=None,
            fields_read=None,
            part=PART_A,
            stopped=False,
            capability_test=self._folded,
        )
        self._task = self.entry.async_create_background_task(
            self.hass,
            self._async_run_stoppable(capability_test),
            name=f"sungrow diagnosis {self.entry.entry_id}",
        )
        return True

    @callback
    def async_start_wallbox(self) -> bool:
        """Begin a run of the wallbox's own checks, and nothing else.

        For auto repeat, which finds one due. Refused while another run is in
        flight and without the owner's leave: the wallbox and the inverter share
        one connection, and only one run writes at a time.
        """
        if self._task is not None and not self._task.done():
            return False
        if not self.wallbox_present or not wallbox_consented(self.entry):
            return False
        self._async_cancel_lapse()
        self._stop_requested = False
        self._set(
            running=True,
            fraction=0.0,
            step=None,
            started=dt_util.now(),
            finished=None,
            extended=True,
            error=None,
            fields_read=None,
            part=PART_WALLBOX,
            stopped=False,
            capability_test=self._folded,
        )
        self._task = self.entry.async_create_background_task(
            self.hass,
            self._async_run_wallbox(),
            name=f"sungrow wallbox test {self.entry.entry_id}",
        )
        return True

    async def _async_run_wallbox(self) -> None:
        """Run the wallbox's checks under paused polling, and end in a state."""
        try:
            async with self.entry.runtime_data.async_paused():
                await self._async_wallbox_test()
        except Exception as err:  # a background run must not be able to crash the loop
            _LOGGER.exception("Wallbox capability test failed for %s", self.entry.title)
            self._set(
                running=False,
                step=None,
                fraction=None,
                finished=dt_util.now(),
                error=f"{type(err).__name__}: {err}",
                part=None,
            )
            return
        coordinator = self.entry.runtime_data.wallbox
        if coordinator is not None:
            await coordinator.async_refresh()
        self._set(
            running=False,
            fraction=1.0,
            step=None,
            finished=dt_util.now(),
            error=None,
            part=None,
            stopped=self._stop_requested,
        )

    async def _async_wallbox_test(self) -> dict[str, Any]:
        """Run the wallbox's checks, keep the run and fold it with the rest.

        What earlier runs established is left out, as for the inverter: a run
        every half hour must not stop a car for answers already kept.
        """
        self._set(part=PART_WALLBOX, step=f"starting the {PART_WALLBOX}")
        skip = (
            self._wallbox_established()
            if self.skip_established or self.continuous.active
            else frozenset()
        )
        runner = WallboxTestRunner(self.hass, self.entry, skip=skip)
        block = await runner.async_run(
            on_progress=lambda label: self._on_progress(
                self.state.fraction or 0.0, f"{PART_WALLBOX}: {label}"
            )
        )
        runs = await async_wallbox_ledger_add(
            self.hass,
            self.entry,
            wallbox_firmware_of(self._wallbox_device()),
            block,
        )
        self._wallbox_folded = wallbox_ledger.fold(runs)
        try:
            persistent_notification.async_create(
                self.hass,
                wallbox_ledger.markdown(
                    self._wallbox_folded, wallbox_check_options(self.entry)
                ),
                title=f"Wallbox capability tests so far: {self.entry.title}",
                notification_id=f"{DOMAIN}_wallbox_ledger_{self.entry.entry_id}",
            )
        except Exception:  # the run succeeded; losing its summary must not fail it
            _LOGGER.exception(
                "%s: the wallbox test history could not be announced", self.entry.title
            )
        self.async_notify()
        return block

    def _shares(
        self, options: dict[str, Any], capability_test: bool, block_reads: int
    ) -> tuple[float, int]:
        """Split one progress bar between the two parts, before either starts.

        Both halves can say how many steps they will report without being run,
        which is what makes a single honest bar possible. The split is by step
        count rather than by time, and that is a known approximation: part B
        spends most of its minutes *waiting* inside a sampling window rather
        than reading, so its share of the bar advances more slowly than part
        A's. The alternative -- a bar that resets, or a second bar -- is worse
        for the person watching, and the step label names the part throughout.
        """
        from .diagnosis_document import (
            planned_steps as diagnosis_steps,
            wallbox_is_direct,
        )

        dumping = bool(options.get(CONF_DIAGNOSIS_DUMP, DEFAULT_DIAGNOSIS_DUMP))
        a_steps = diagnosis_steps(
            dumping,
            block_reads,
            wallbox=self.entry.runtime_data.wallbox is not None,
            wallbox_direct=self.entry.runtime_data.wallbox is not None
            and wallbox_is_direct(self.entry.runtime_data.wallbox),
        )
        if not capability_test:
            return 1.0, a_steps
        b_steps = capability_test_steps(self._control_options())
        return a_steps / (a_steps + b_steps), a_steps

    def _device(self) -> Any:
        """Return the inverter this entry's coordinators share."""
        return self.entry.runtime_data.inverter_coordinator.device

    async def _async_capability_test(self, share: float) -> dict[str, Any]:
        """Run part B, reporting into the tail of the same progress bar.

        The runner is built here rather than held, because it owns a shutdown
        hook for the window in which the inverter may be stopped and that hook
        should not outlive the run that armed it.
        """
        from .capability_test import CapabilityTestRunner

        self._set(part=PART_B, step="starting the capability test")
        runner = CapabilityTestRunner(
            self.hass,
            self.entry,
            forced_startup=self._forced_startup,
            # Auto repeat always leaves out what is established, the restart
            # included: a run every half hour must not stop the inverter or
            # write every control again for answers already kept.
            skip=(
                ledger.established(
                    self._folded,
                    moment=ledger.live_moment(self.continuous.live()),
                )
                if self.skip_established or self.continuous.active
                else frozenset()
            ),
        )
        self._capability_runner = runner
        try:
            return await runner.async_run(
                on_progress=lambda fraction, label: self._on_progress(
                    share + fraction * (1.0 - share), f"{PART_B}: {label}"
                )
            )
        finally:
            self._capability_runner = None

    @callback
    def async_stop(self) -> None:
        """End auto repeat, and the run in flight, putting everything back.

        Part A only reads, so it is simply cancelled. Part B is asked to end
        at its next check: what it measured so far is kept, every check left
        is recorded as stopped, the restore runs in full as always, and no
        restart is started. A cancel would skip the restart's own recovery.
        """
        self.continuous.async_turn_off("stopped by the owner")
        if not self.state.running:
            return
        self._stop_requested = True
        if self._capability_runner is not None:
            self._capability_runner.request_stop()
            self._set(step=f"{PART_B}: stopping, putting everything back")
        elif self._task is not None and not self._task.done():
            # The task starts eagerly, so it is only missing here while its
            # first synchronous stretch runs -- which part A cannot be in when
            # a person presses a button.
            self._task.cancel()

    def _control_options(self) -> ControlOptions:
        """Return what part B has leave to do, from this entry's options."""
        return ControlOptions(
            forced_startup=self._forced_startup,
            restart=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_RESTART, CAPABILITY_TEST_PERMISSION_DEFAULT
                )
            ),
            enable_export_limit=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_EXPORT, CAPABILITY_TEST_PERMISSION_DEFAULT
                )
            ),
            cut_pv=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_PV_CUT, CAPABILITY_TEST_PERMISSION_DEFAULT
                )
            ),
            charge_window=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_CHARGE_WINDOW,
                    CAPABILITY_TEST_PERMISSION_DEFAULT,
                )
            ),
            discharge_window=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
                    CAPABILITY_TEST_PERMISSION_DEFAULT,
                )
            ),
            import_limit=bool(
                self.entry.options.get(
                    CONF_CAPABILITY_TEST_IMPORT_LIMIT,
                    CAPABILITY_TEST_PERMISSION_DEFAULT,
                )
            ),
        )

    async def _async_run_stoppable(self, capability_test: bool) -> None:
        """Run, and end in the stopped state when the owner cancelled part A.

        Any other cancellation -- an unload, a shutdown -- propagates as
        before; part B's restore is shielded against it either way.
        """
        try:
            await self._async_run(capability_test)
        except asyncio.CancelledError:
            if not self._stop_requested:
                raise
            # Stopped in part A, which only reads: nothing to put back and
            # no document worth offering.
            self._set(
                running=False,
                step=None,
                fraction=None,
                finished=dt_util.now(),
                error=None,
                part=None,
                stopped=True,
            )

    async def _async_run(self, capability_test: bool = False) -> None:
        """Build the document, and end in a state either way.

        A failure is kept and shown rather than raised. Somebody who pressed
        a button offering to help is owed the reason, and a link that fails
        here is worth reporting in its own right -- the four states a probe
        can end in exist precisely because "it did not work" is not one
        answer but several.

        Part B runs **after** part A and only if part A succeeded. Not for
        tidiness: part A is what establishes that this device answers, what it
        is and what it has, and writing to a device none of that is known about
        is exactly the thing the capability test's own guards exist to refuse.
        """
        # Imported here rather than at module level: `diagnosis_document` imports
        # the library, and this module is imported by the platforms.
        from .diagnosis_document import async_build, attach_capability_test

        share, _a_steps = (
            (1.0, 0)
            if self.entry.runtime_data.is_string_inverter
            else self._shares(
                dict(self.entry.options),
                capability_test,
                block_test.planned_steps(await block_test.inverter_blocks()),
            )
        )
        try:
            # Both parts run with this entry's own polling held off. They read
            # and write the same endpoint the coordinators do, over the same
            # serialized connection, so without this a diagnosis measures the
            # inverter *and* the contention it is causing -- and part B's power
            # sampling competes with tier polls for the whole of every window.
            async with self.entry.runtime_data.async_paused():
                document = await async_build(
                    self.hass,
                    self.entry,
                    on_progress=lambda fraction, label: self._on_progress(
                        fraction * share, label
                    ),
                    # Only here. This is the one caller that can spend five
                    # minutes: a background task, with a progress bar somebody
                    # can watch and a notification at the end. The diagnostics
                    # download builds the same document and leaves it off,
                    # because nothing there survives a wait like that.
                    allow_dump=True,
                    # Likewise only here, and not an option: the measurement
                    # `src/sungrow_modbus/hybrid_inverter/layout.py` is changed from.
                    allow_block_test=True,
                )
                if capability_test:
                    block = await self._async_capability_test(share)
                    # Checked through the door on its own first, then kept
                    # and folded with the runs before it.
                    attach_capability_test(document, block, self._device())
                    self._folded = await self._async_record(block, document)
                    if wallbox_consented(self.entry) and self.wallbox_present:
                        # After the inverter's part B, never beside it: one
                        # connection, one writer.
                        await self._async_wallbox_test()
                if self._folded is not None:
                    attach_capability_test(document, self._folded, self._device())
                if self._wallbox_folded is not None:
                    document["wallbox_capability_test"] = wallbox_ledger.document(
                        self._wallbox_folded, wallbox_check_options(self.entry)
                    )
                if self.plausibility.observations:
                    document["plausibility"] = self.plausibility.document()
                if self.wallbox_plausibility.observations:
                    document["wallbox_plausibility"] = (
                        self.wallbox_plausibility.document()
                    )
        except Exception as err:  # a button press must not be able to crash the loop
            # `exception`, not `warning`: this catches everything, so the type
            # alone is often useless -- a bare `KeyError: 'realtime'` says
            # nothing about which of a dozen lookups it was. The person who
            # hits this is usually a contributor who will paste the log into
            # an issue, and a traceback is the difference between a fix and a
            # conversation. The *state* keeps the short form, because that one
            # is read in a dialog.
            _LOGGER.exception("Diagnosis failed for %s", self.entry.title)
            self._set(
                running=False,
                step=None,
                fraction=None,
                finished=dt_util.now(),
                error=f"{type(err).__name__}: {err}",
                part=None,
            )
            return

        # `values` is the decoded map, and its size is the number worth
        # showing: "95 of 104 fields" is how every summary in this project
        # reports a diagnosis, and the other 9 are named beside it.
        readings = document.get("readings", {})
        decoded = (
            document["string_inverter"]["readings"]
            if document.get("document") == string_inverter.DOCUMENT
            else readings.get("values", {})
        )
        self._set(
            running=False,
            fraction=1.0,
            step=None,
            finished=dt_util.now(),
            fields_read=len(decoded),
            error=None,
            document=document,
            part=None,
            stopped=self._stop_requested,
            capability_test=document.get("capability_test"),
        )
        try:
            self._async_offer_the_document(document)
        # Deliberately broad, and logged rather than raised: the diagnosis
        # succeeded and its state already says so. Losing the announcement
        # is bad; losing it *silently* -- a bare asyncio traceback and a
        # device page claiming success -- is worse.
        except Exception:
            _LOGGER.exception(
                "The diagnosis for %s finished but could not be announced. "
                "The document is still on the device page, under Download "
                "diagnostics",
                self.entry.title,
            )

    async def async_load_ledger(self) -> None:
        """Fold the runs kept from before a restart, for this firmware."""
        from .capability_test import (
            async_ledger_runs,
            async_plausibility_load,
            firmware_of,
        )

        firmware = firmware_of(self._device())
        runs = await async_ledger_runs(self.hass, self.entry, firmware)
        self._folded = self._fold(runs)
        self._plausibility_firmware = firmware
        self.plausibility = Plausibility.from_dict(
            await async_plausibility_load(self.hass, self.entry, firmware)
        )
        if self.wallbox_present:
            wallbox_firmware = wallbox_firmware_of(self._wallbox_device())
            wallbox_runs = await async_wallbox_ledger_runs(
                self.hass, self.entry, wallbox_firmware
            )
            self._wallbox_folded = (
                wallbox_ledger.fold(wallbox_runs) if wallbox_runs else None
            )
            self._wallbox_firmware = wallbox_firmware
            self.wallbox_plausibility = (
                wallbox_plausibility.WallboxPlausibility.from_dict(
                    await async_wallbox_plausibility_load(
                        self.hass, self.entry, wallbox_firmware
                    )
                )
            )
            await self._async_warn_wallbox_leftover()
        self._set(capability_test=self._folded)

    async def _async_warn_wallbox_leftover(self) -> None:
        """Say a wallbox run did not finish. Nothing is written at setup."""
        from .wallbox_capability_test import async_leftover as wallbox_leftover

        if await wallbox_leftover(self.hass, self.entry) is not None:
            _LOGGER.warning(
                "%s: a wallbox capability test did not finish putting things back. "
                "The next run puts them back first; nothing is written at setup.",
                self.entry.title,
            )

    async def async_clear_ledger(self) -> None:
        """Forget every kept run, and the notification that showed them."""
        from .capability_test import async_ledger_clear, plausibility_store

        await async_ledger_clear(self.hass, self.entry)
        await plausibility_store(self.hass, self.entry).async_remove()
        self.plausibility = Plausibility()
        self._folded = None
        if self.wallbox_present:
            await async_wallbox_ledger_clear(self.hass, self.entry)
            await wallbox_plausibility_store(self.hass, self.entry).async_remove()
            self.wallbox_plausibility = wallbox_plausibility.WallboxPlausibility()
            self._wallbox_folded = None
        self._set(capability_test=None)
        persistent_notification.async_dismiss(self.hass, self._ledger_notification_id)

    @staticmethod
    def _fold(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Fold kept runs, or None when there are none."""
        if not runs:
            return None
        return ledger.fold(runs, readings=runs[-1].get("readings"))

    async def _async_record(
        self, block: dict[str, Any], document: dict[str, Any]
    ) -> dict[str, Any]:
        """Keep this run's block and return every kept run, folded."""
        from .capability_test import async_ledger_add, firmware_of

        run = {
            "read_at": dt_util.utcnow().isoformat(),
            "block": block,
            "readings": dict((document.get("readings") or {}).get("values") or {}),
        }
        runs = await async_ledger_add(
            self.hass, self.entry, firmware_of(self._device()), run
        )
        folded = self._fold(runs)
        assert folded is not None
        try:
            self._async_announce_ledger(folded)
        except Exception:  # the run succeeded; losing its summary must not fail it
            _LOGGER.exception(
                "%s: the capability test history could not be announced",
                self.entry.title,
            )
        return folded

    @property
    def _ledger_notification_id(self) -> str:
        """One id per entry, so each run rewrites the summary in place."""
        return f"{DOMAIN}_capability_ledger_{self.entry.entry_id}"

    @callback
    def _async_announce_ledger(self, folded: dict[str, Any]) -> None:
        """Show every kept run in one notification, rewritten after each run.

        A notification because a sensor state stops at 255 characters, and
        what an owner collecting runs over a day needs is the list of checks
        still waiting and for what. English for now, like the document.
        """
        shown = ledger.with_plausibility(folded, self.plausibility.summary())
        assert shown is not None
        persistent_notification.async_create(
            self.hass,
            ledger.markdown(shown)
            + "\n\n**Download diagnostics** on the device page carries every "
            "run in one document.",
            title=f"Capability tests so far: {self.entry.title}",
            notification_id=self._ledger_notification_id,
        )

    @callback
    def _async_offer_the_document(self, document: dict[str, Any]) -> None:
        """Put the finished document in front of the person who asked for it.

        A notification rather than anything in the entity: this is the one
        moment the integration has something to *give* somebody, and a
        sensor's attributes are not a place you can click. The link is signed
        and short-lived; `download.py` says why.

        Three things are said, each because a contributor needs it:

        - **where the notification is.** A persistent notification is a badge
          in the sidebar, and somebody watching the device page for a progress
          bar does not see it appear. So the button's own sensors say a run
          finished, and this says where the file is.
        - **that the link lapses, and when.** The notification outlives its
          signature by design -- an hour later it is still sitting there with
          a URL that now 401s, which reads as the integration being broken.
          The time is named here, and `_async_mark_lapsed` rewrites this
          message when it arrives.
        - **that a markdown link does not work at all.** Measured, after a
          contributor clicked one and nothing happened while the endpoint
          answered 200 to the same URL from curl. The frontend routes
          same-origin anchors internally; see the comment on the anchor
          below.

        And the route that never expires is named beside the one that does:
        the device page's own **Download diagnostics** builds the same
        document, from the same code, with the same testimony.
        """
        # Imported late for the same reason as `async_build`: this module is
        # imported by the platforms, and `download` imports the HTTP stack.
        from .diagnosis_document import summarise
        from .download import async_download_url

        url = async_download_url(self.hass, self.entry)
        lapses = dt_util.now() + LINK_VALID

        persistent_notification.async_create(
            self.hass,
            (
                # Rendered from the document rather than from the run, so a
                # summary cannot promise something the file does not carry.
                f"{summarise(document)}\n\n"
                # Raw HTML with `target`, not `[text](url)`. A markdown link
                # renders as a bare same-origin anchor, and the frontend's
                # global click handler swallows exactly those: it takes any
                # anchor with no `target`, no `download` and no `rel=external`
                # whose origin matches the page, calls preventDefault(), and
                # hands the path to the client-side router. `/api/...` is not
                # a panel, so the router does nothing at all -- the link looks
                # dead while the endpoint is answering 200. `target` is also
                # the only one of those three escapes that survives Home
                # Assistant's markdown sanitiser, whose whitelist for an
                # anchor is exactly ("target", "href", "title").
                f'<a href="{url}" target="_blank">Download the document</a>'
                " — this link stops working at "
                f"{lapses.strftime('%H:%M')}. After that, press "
                "**Diagnosis: start** again for a fresh one, or use "
                "**Download diagnostics** on the device page, which carries "
                "the same document and never expires.\n\n"
                "It carries a stand-in serial rather than the real one, and "
                "your address only if you allowed it. Send it to "
                f"[the diagnosis issue]({DIAGNOSIS_ISSUE_URL}) — what varies between "
                "installations is the thing no specification has told this "
                "project reliably."
            ),
            title=(
                f"Diagnosis {'stopped' if self.state.stopped else 'finished'}: "
                f"{self.entry.title}"
            ),
            notification_id=self._notification_id,
        )
        self._lapsed = async_call_later(self.hass, LINK_VALID, self._async_mark_lapsed)

    @callback
    def async_announce_start(self, mode: str) -> None:
        """Say what was started and what to expect, until the result replaces it.

        Under the finished notice's id, so the document's notice takes its
        place rather than stacking. A button shows no text of its own, so this
        is where somebody who pressed Start learns that they may leave.
        """
        what = {
            DIAGNOSIS_MODE_READ_ONLY: (
                "A read-only diagnosis is running. It only reads; nothing on "
                "the inverter changes."
            ),
            DIAGNOSIS_MODE_EXTENDED: (
                "An extended test is running: the diagnosis, then one "
                "capability test. It writes each setting, reads it back and "
                "puts your original value back, checked by reading it again."
            ),
            DIAGNOSIS_MODE_AUTO_REPEAT: (
                "The extended test repeats on its own: whenever the house can "
                "answer a check still missing, a capability test starts, at "
                "most every 30 minutes, and leaves out what earlier runs "
                "established. Each writes its settings and puts your original "
                "values back. **Diagnosis: current step** shows what it waits "
                "for; **Diagnosis: stop** ends it, and so does a restart."
            ),
        }[mode]
        persistent_notification.async_create(
            self.hass,
            f"{what}\n\n"
            "It runs in the background: you can leave this page. A "
            "notification tells you when it has finished. **Please do not "
            "restart Home Assistant meanwhile** — the test would still put "
            "everything back, but the run is lost. **Diagnosis: stop** ends a "
            "run early; every value it changed is still put back.",
            title=f"Diagnosis started: {self.entry.title}",
            notification_id=self._notification_id,
        )

    @property
    def _notification_id(self) -> str:
        """One id per entry, so a second run replaces rather than stacks."""
        return f"{DOMAIN}_diagnosis_{self.entry.entry_id}"

    @callback
    def async_shutdown(self) -> None:
        """Drop the pending timer when the entry unloads.

        An hour-long timer outliving its config entry would fire against a
        runner nobody can see and a notification nobody asked for, and it is
        what Home Assistant's own test harness calls a lingering timer.
        """
        self._async_cancel_lapse()
        self.continuous.async_turn_off("the entry was unloaded")

    @callback
    def _async_cancel_lapse(self) -> None:
        """Forget a pending "the link has expired" rewrite."""
        if self._lapsed is not None:
            self._lapsed()
            self._lapsed = None

    @callback
    def _async_mark_lapsed(self, _now: datetime) -> None:
        """Say the link died, rather than leaving one that silently 401s.

        Replacing the notification rather than dismissing it: the summary is
        the part worth keeping -- somebody may not have read it yet -- and a
        notification that vanishes on its own looks like something went
        wrong. What changes is the promise, which is no longer true.
        """
        self._lapsed = None
        document = self.state.document
        if document is None:
            return
        # Imported late, as above.
        from .diagnosis_document import summarise

        persistent_notification.async_create(
            self.hass,
            (
                f"{summarise(document)}\n\n"
                "The download link in this notification has expired. Press "
                "**Diagnosis: start** again for a fresh one, or use "
                "**Download diagnostics** on the device page — that carries "
                "the same document and never expires.\n\n"
                "It carries a stand-in serial rather than the real one, and "
                "your address only if you allowed it. Send it to "
                f"[the diagnosis issue]({DIAGNOSIS_ISSUE_URL})."
            ),
            title=f"Diagnosis finished: {self.entry.title}",
            notification_id=self._notification_id,
        )

    @callback
    def _on_progress(self, fraction: float, step: str) -> None:
        """Record one step. Called from the reading loop, on the event loop."""
        self._set(fraction=fraction, step=step)


@callback
def async_runner(entry: SungrowConfigEntry) -> DiagnosisRunner:
    """Return the runner for one entry, from its runtime data."""
    runner: DiagnosisRunner = entry.runtime_data.diagnosis
    return runner


Progress = Callable[[float, str], None]
"""What `diagnosis_document.async_build` calls after each read it can count."""
