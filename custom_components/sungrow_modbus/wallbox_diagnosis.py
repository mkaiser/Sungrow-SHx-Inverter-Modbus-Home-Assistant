"""The diagnosis and capability test of a wallbox that is an entry of its own.

A wallbox at its own address (TLS, port 516, unit 248) has no inverter beside
it, but the same tests an inverter entry runs on its wallbox: the procedure in
`sungrow_modbus.wallbox.capability_test`, the port, snapshot and ledger in
`wallbox_capability_test.py`, the plausibility of its readings, and auto
repeat. All of that lives on the inverter's `DiagnosisRunner`, which reaches
the wallbox through `runtime_data.wallbox` -- so this runner *is* one, with
only the parts that assume an inverter replaced:

- **the read** is the wallbox's own document (`device_diagnosis.wallbox_builder`),
  the one `wallbox_direct.py` writes, rather than the inverter's;
- **an extended run** reads, then runs the wallbox's checks: the leave and
  the cap are this entry's options. Without the leave it reads only, and says so;
- **the ledger and the plausibility** loaded at setup are the wallbox's alone;
- **auto repeat** asks only the wallbox's ledger (`inverter_tests` is False).

Nothing writes at setup: a snapshot a run left is logged, and put back first
by the next run, which is an explicit act with leave.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util
from sungrow_modbus.capability_test import ledger as inverter_ledger
from sungrow_modbus.wallbox import (
    ledger as wallbox_ledger,
    plausibility as wallbox_plausibility,
)

from .const import (
    DIAGNOSIS_ISSUE_URL,
    DIAGNOSIS_MODE_AUTO_REPEAT,
    DIAGNOSIS_MODE_EXTENDED,
    DIAGNOSIS_MODE_READ_ONLY,
    DOMAIN,
    LINK_VALID,
)
from .continuous import WALLBOX_ALONE_INTERVAL
from .coordinator import SungrowConfigEntry
from .device_diagnosis import _fields, wallbox_builder, wallbox_summary
from .diagnosis import DiagnosisRunner
from .wallbox_capability_test import (
    async_ledger_clear,
    async_ledger_runs,
    async_plausibility_load,
    check_options,
    consented,
    firmware_of,
    plausibility_store,
)

_LOGGER = logging.getLogger(__name__)

#: Said in place of the test when an extended run had no leave to write.
NO_LEAVE = (
    "The capability test did not run: it writes to the wallbox only once you "
    "switch it on in this entry's options (**Configure**)."
)


class WallboxDiagnosisRunner(DiagnosisRunner):
    """The inverter's runner, pointed at a wallbox with no inverter beside it."""

    inverter_tests = False
    wallbox_interval = WALLBOX_ALONE_INTERVAL

    def __init__(self, hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
        """Prepare a runner. Nothing runs until `async_start`."""
        super().__init__(hass, entry)
        self._build = wallbox_builder(entry)
        #: Whether the run in flight was asked to test and had no leave.
        self._no_leave = False
        #: The kept runs, oldest first, for the status sensor's count and log.
        self._wallbox_runs: list[dict[str, Any]] = []

    @property
    def tests(self) -> dict[str, Any] | None:
        """The wallbox's kept runs and its readings' checks, counted together.

        `runs` in the shape the status sensor reads (`ledger.run_lines`): the
        wallbox's fold counts its runs, and an inverter entry's runs are a list.
        """
        shown = inverter_ledger.with_plausibility(None, self._wallbox_rows())
        if shown is not None and self._wallbox_runs:
            shown["runs"] = [_run_line(run) for run in self._wallbox_runs]
        return shown

    async def _async_wallbox_test(self) -> dict[str, Any]:
        """Run the wallbox's checks as the inverter's runner does, and keep the runs."""
        block = await super()._async_wallbox_test()
        self._wallbox_runs = await async_ledger_runs(
            self.hass, self.entry, firmware_of(self._wallbox_device())
        )
        return block

    @callback
    def async_observe(self, now: Any) -> None:
        """Feed the wallbox's polled readings to its plausibility checks."""
        if self.state.running:
            return
        self._async_observe_wallbox(now)

    async def _async_run(self, capability_test: bool = False) -> None:
        """Read the wallbox, then, with leave, run its checks; end in a state."""
        self._no_leave = capability_test and not consented(self.entry)
        test = capability_test and not self._no_leave
        share = 0.3 if test else 1.0
        try:
            async with self.entry.runtime_data.async_paused():
                document = await self._build(
                    lambda fraction, step: self._on_progress(fraction * share, step)
                )
                if test:
                    await self._async_wallbox_test()
                if self._wallbox_folded is not None:
                    document["wallbox_capability_test"] = wallbox_ledger.document(
                        self._wallbox_folded, check_options(self.entry)
                    )
                if self.wallbox_plausibility.observations:
                    document["wallbox_plausibility"] = (
                        self.wallbox_plausibility.document()
                    )
        except Exception as err:  # a button press must not crash the loop
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
        coordinator = self.entry.runtime_data.wallbox
        if test and coordinator is not None:
            # Polling was held off for minutes, and the run changed settings
            # and put them back: show what the wallbox holds now.
            await coordinator.async_refresh()
        self._set(
            running=False,
            fraction=1.0,
            step=None,
            finished=dt_util.now(),
            fields_read=_fields(document),
            error=None,
            document=document,
            part=None,
            stopped=self._stop_requested,
        )
        try:
            self._async_offer_the_document(document)
        except Exception:  # the run succeeded; losing its notice must not fail it
            _LOGGER.exception(
                "The diagnosis for %s finished but could not be announced",
                self.entry.title,
            )

    def _summary(self, document: dict[str, Any]) -> str:
        """Say what the document holds: the read, the tests, a missing leave."""
        lines = [wallbox_summary(document)]
        block = document.get("wallbox_capability_test")
        if isinstance(block, dict):
            runs = block.get("runs")
            count = len(runs) if isinstance(runs, list) else runs
            lines.append(f"- Capability test: {count or 0} run(s) kept.")
        if self._no_leave:
            lines.append(f"- {NO_LEAVE}")
        return "\n".join(lines)

    @callback
    def _async_offer_the_document(self, document: dict[str, Any]) -> None:
        """Offer the wallbox's document, as the inverter's runner offers its own."""
        from .download import async_download_url

        url = async_download_url(self.hass, self.entry)
        lapses = dt_util.now() + LINK_VALID
        persistent_notification.async_create(
            self.hass,
            f"{self._summary(document)}\n\n"
            # Raw HTML with `target`: `DiagnosisRunner._async_offer_the_document`
            # says why a markdown link does nothing here.
            f'<a href="{url}" target="_blank">Download the document</a>'
            f" — this link stops working at {lapses.strftime('%H:%M')}. After "
            "that, press **Diagnosis: start** again for a fresh one, or use "
            "**Download diagnostics** on the device page.\n\n"
            "It carries a stand-in in place of the serial number, and your "
            "address only if you allowed it. Send it to "
            f"[the diagnosis issue]({DIAGNOSIS_ISSUE_URL}).",
            title=(
                f"Diagnosis {'stopped' if self.state.stopped else 'finished'}: "
                f"{self.entry.title}"
            ),
            notification_id=self._notification_id,
        )
        self._lapsed = async_call_later(self.hass, LINK_VALID, self._async_mark_lapsed)

    @callback
    def _async_mark_lapsed(self, _now: Any) -> None:
        """Say the link died, keeping the summary."""
        self._lapsed = None
        document = self.state.document
        if document is None:
            return
        persistent_notification.async_create(
            self.hass,
            f"{self._summary(document)}\n\nThe download link has expired. Press "
            "**Diagnosis: start** again for a fresh one, or use **Download "
            "diagnostics** on the device page. Send it to "
            f"[the diagnosis issue]({DIAGNOSIS_ISSUE_URL}).",
            title=f"Diagnosis finished: {self.entry.title}",
            notification_id=self._notification_id,
        )

    @callback
    def async_announce_start(self, mode: str) -> None:
        """Say what was started, in the wallbox's words."""
        leave = consented(self.entry)
        what = {
            DIAGNOSIS_MODE_READ_ONLY: (
                "A read-only diagnosis is running. It only reads; nothing on "
                "the wallbox changes."
            ),
            DIAGNOSIS_MODE_EXTENDED: (
                "An extended test is running: the diagnosis, then the wallbox "
                "capability test. Most checks need a car charging; one that "
                "has none to judge is recorded as waiting. Every setting it "
                "changes is put back and read again."
                if leave
                else f"The diagnosis is running. {NO_LEAVE}"
            ),
            DIAGNOSIS_MODE_AUTO_REPEAT: (
                "The wallbox capability test repeats on its own: whenever a "
                "check still missing can be answered (most need a car "
                "charging), a run starts, at most every 15 minutes, and leaves "
                "out what earlier runs established. **A charge in progress is "
                "interrupted** by some checks. **Diagnosis: current step** "
                "shows what it waits for; **Diagnosis: stop** ends it, and so "
                "does a restart."
                if leave
                else f"Nothing will run. {NO_LEAVE}"
            ),
        }[mode]
        persistent_notification.async_create(
            self.hass,
            f"{what}\n\nIt runs in the background: you can leave this page. "
            "**Diagnosis: stop** ends a run early; every value it changed is "
            "still put back.",
            title=f"Diagnosis started: {self.entry.title}",
            notification_id=self._notification_id,
        )

    async def async_load_ledger(self) -> None:
        """Fold the wallbox's kept runs and readings for its firmware."""
        firmware = firmware_of(self._wallbox_device())
        runs = await async_ledger_runs(self.hass, self.entry, firmware)
        self._wallbox_runs = runs
        self._wallbox_folded = wallbox_ledger.fold(runs) if runs else None
        self._wallbox_firmware = firmware
        self.wallbox_plausibility = wallbox_plausibility.WallboxPlausibility.from_dict(
            await async_plausibility_load(self.hass, self.entry, firmware)
        )
        await self._async_warn_wallbox_leftover()
        self.async_notify()

    async def async_clear_ledger(self) -> None:
        """Forget the wallbox's kept runs and readings."""
        await async_ledger_clear(self.hass, self.entry)
        await plausibility_store(self.hass, self.entry).async_remove()
        self.wallbox_plausibility = wallbox_plausibility.WallboxPlausibility()
        self._wallbox_folded = None
        self._wallbox_runs = []
        self._set(part=None)
        persistent_notification.async_dismiss(
            self.hass, f"{DOMAIN}_wallbox_ledger_{self.entry.entry_id}"
        )


def _run_line(run: dict[str, Any]) -> dict[str, Any]:
    """Return one kept wallbox run as a row of the status sensor's log."""
    guard = (run.get("conditions") or {}).get("guard")
    steps = run.get("steps") or []
    means = (
        f"refused: {guard}"
        if guard
        else f"{len(steps)} step(s), exit {run.get('code')}"
    )
    return {"read_at": run.get("read_at"), "outcome_means": means}
