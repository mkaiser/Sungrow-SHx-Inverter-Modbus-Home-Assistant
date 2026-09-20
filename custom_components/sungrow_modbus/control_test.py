"""Part B of the survey: write each control, read it back, and put it back.

Part A asks what is here and answers it entirely by reading. This asks whether
writing works -- whether a value sent to a register arrives at the scale
everybody involved believes it has -- and there is no way to ask that without
writing. So this is the one part of the integration that changes a setting
without a person having set it, and every design decision below follows from
that being true.

**Nothing here decides anything.** The procedure, the probe values, the
verdicts, the restore order and the refusals all live in
`sungrow_modbus.control_test`, which has no Home Assistant in it and is driven
identically by `scripts/sungrow_control_test.py`. What lives here is the four
things that need Home Assistant: a snapshot that survives a restart, a
shutdown hook so a stopped inverter is started again, the progress callback the
device page draws, and the options that say what this run has leave to do.

The snapshot is the part worth reading twice. It goes into HA's own store
*before the first write*, and it is cleared only once everything has been put
back and read back. Anything left in it on the next setup is a house still
carrying this run's values, which `repairs.py` turns into a repair somebody can
click.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from sungrow_modbus.control_test import ControlTest, Options, Snapshot, document

from .const import CONF_CONTROL_TEST_EXPORT, CONF_CONTROL_TEST_RESTART, DOMAIN

if TYPE_CHECKING:
    from . import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)

#: One store per config entry, because one entry is one endpoint and a house
#: may have two. Version 1; a future shape change bumps it and migrates, which
#: is why the payload is a plain dict rather than the dataclass.
STORE_VERSION = 1
STORE_KEY = f"{DOMAIN}.control_test"

#: The component that reports whether the inverter is running, refreshed after
#: a start or stop because the *written* register is in the holding space and
#: the state is read from the input side of the same address. Refreshing what
#: was written would show the old state.
STATE_COMPONENT = "realtime_input"


def _store(hass: HomeAssistant, entry: SungrowConfigEntry) -> Store[dict[str, Any]]:
    """Return this entry's snapshot store."""
    return Store(hass, STORE_VERSION, f"{STORE_KEY}.{entry.entry_id}")


async def async_leftover(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> Snapshot | None:
    """Return a snapshot a previous run never finished with, if there is one.

    Called on setup. A snapshot here means the last run did not reach the end
    of its restore -- Home Assistant was restarted, the entry was reloaded, the
    link went away -- and the registers it names may still hold this run's
    values rather than the owner's.
    """
    data = await _store(hass, entry).async_load()
    if not data:
        return None
    return Snapshot.from_dict(data)


async def async_forget(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Drop the snapshot, once everything in it is known to be back."""
    await _store(hass, entry).async_remove()


class ControlTestRunner:
    """Drives one entry's control test, and guarantees the inverter comes back.

    Held by the survey runner rather than standing alone, because the two share
    a connection and a Sungrow grants very few sessions: two of these at once on
    one endpoint would interleave their reads and their writes, and the writes
    are the half where that matters.
    """

    def __init__(self, hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
        """Prepare a runner. Nothing is read or written until `async_run`."""
        self.hass = hass
        self.entry = entry
        self._remove_shutdown_job: Any = None
        self._test: ControlTest | None = None

    def _options(self) -> Options:
        """Read what this run has leave to do, from the entry's options.

        `allow_dark` is **always on here**, and it is the one flag that differs
        from the CLI's default. The reason is who is pressing the button.

        A CLI user chose the moment and can pass `--allow-dark` when they mean
        it. Somebody on Home Assistant OS has no terminal at all, so a run
        refused for want of sun is a run they can never make -- and in a German
        December that is most of the day. What the refusal would cost them is
        the **readback** half, which is the half that finds a factor-10 error
        and which does not care whether the sun is up: it writes a register and
        compares the word that comes back against the specification.

        The behavioural half genuinely cannot run in the dark, and it is not
        pretended otherwise -- each check self-skips and says why, and those
        reasons are what "what this run could not establish" is generated from.
        A report that names four things it could not measure is worth more than
        a refusal that measures nothing.
        """
        options = self.entry.options
        return Options(
            allow_dark=True,
            restart=bool(options.get(CONF_CONTROL_TEST_RESTART, False)),
            enable_export_limit=bool(options.get(CONF_CONTROL_TEST_EXPORT, False)),
        )

    @callback
    def _arm_shutdown_guard(self) -> None:
        """Make sure a shutdown cannot leave the inverter stopped.

        A shutdown job is awaited **before** `EVENT_HOMEASSISTANT_STOP` fires,
        and background tasks are cancelled after that -- so a job registered
        here runs while the event loop and this connection are still alive,
        which a `finally` inside a cancelled task cannot promise.

        Armed the moment before 0xCE goes out and removed as soon as the
        inverter reports running, so it exists only for the window in which it
        could be needed.
        """
        if self._remove_shutdown_job is not None:
            return
        self._remove_shutdown_job = self.hass.async_add_shutdown_job(
            HassJob(self._async_start_again, "sungrow control test: start the inverter")
        )

    @callback
    def _disarm_shutdown_guard(self) -> None:
        """Remove the hook once the inverter is known to be running."""
        if self._remove_shutdown_job is not None:
            self._remove_shutdown_job()
            self._remove_shutdown_job = None

    async def _async_start_again(self, *_args: Any) -> None:
        """Start the inverter, from wherever this is called."""
        if self._test is not None:
            _LOGGER.warning(
                "%s: the control test is stopping; starting the inverter first",
                self.entry.title,
            )
            await self._test.async_ensure_running()
        self._disarm_shutdown_guard()

    async def async_run(self, on_progress: Any = None) -> dict[str, Any]:
        """Run the procedure and return the block for the survey document."""
        runtime = self.entry.runtime_data
        coordinator = next(iter(runtime.coordinators.values()))
        store = _store(self.hass, self.entry)

        async def keep(snapshot: Snapshot) -> None:
            # Before the first write, and awaited rather than scheduled: a
            # snapshot that reaches the disk after the write it was taken to
            # undo describes a house that has already been changed.
            if snapshot.stopped_at is not None:
                self._arm_shutdown_guard()
            await store.async_save(snapshot.to_dict())

        self._test = ControlTest(
            coordinator.device,
            options=self._options(),
            on_progress=on_progress,
            on_snapshot=keep,
        )
        _LOGGER.warning(
            "%s: running the control test. It writes to every control this "
            "integration can write to, and puts each one back.",
            self.entry.title,
        )
        try:
            outcome = await self._test.async_run()
        finally:
            self._disarm_shutdown_guard()

        if outcome.not_restored:
            # Left deliberately. The next setup turns it into a repair, which
            # is the only thing that still works after the run is gone.
            _LOGGER.error(
                "%s: the control test could not put %s back; the snapshot is kept "
                "so this can be repaired",
                self.entry.title,
                ", ".join(row.field for row in outcome.not_restored),
            )
        else:
            await store.async_remove()

        await coordinator.async_refresh()
        return document(outcome)

    async def async_restore(self, snapshot: Snapshot) -> bool:
        """Put a leftover snapshot back. Used by the repair flow.

        Starts the inverter first where the snapshot says it was stopped,
        because a register written to a stopped inverter is a register written
        to something that may not be listening.
        """
        runtime = self.entry.runtime_data
        coordinator = next(iter(runtime.coordinators.values()))
        test = ControlTest(coordinator.device)
        if snapshot.stopped_at is not None:
            await test.async_ensure_running()
        results = await test.async_restore(snapshot)
        await coordinator.async_refresh()
        if all(row.restored for row in results):
            await async_forget(self.hass, self.entry)
            return True
        return False
