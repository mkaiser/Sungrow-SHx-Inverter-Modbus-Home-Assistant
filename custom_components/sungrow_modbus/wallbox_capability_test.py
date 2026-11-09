"""The wallbox's capability test inside Home Assistant: a port, a snapshot, a ledger.

`sungrow_modbus.wallbox.capability_test` decides everything: what is written,
what is judged, what is put back. This is the part that needs Home Assistant,
the same four things the inverter's `capability_test.py` supplies: a port over
the entry's own connection to the wallbox, a snapshot that survives a restart,
the ledger of every kept run, and the options that say what a run may do.

**The port has no fresh session.** The wallbox is read and written through the
connection the entry already has -- its own address over TLS (unit 248), or unit
3 behind the dongle -- which every coordinator shares and which Home Assistant
serializes. A second connection to a wallbox that accepts few sessions would
be worse than the stale readback it would cure, so `fresh` is False: the run
says leg B is not independent, and what the car does is the evidence.

**Polling is held off** for the whole run (`SungrowRuntimeData.async_paused`),
the wallbox's coordinator included, and the run's own reads keep the session
alive: a wallbox drops a quiet one after 60 s and applies its fallback current.

**Nothing writes at setup.** A snapshot left by a run that did not finish is
logged when the entry loads and put back first thing in the next run, which is
an explicit act with leave.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from sungrow_modbus.wallbox import capability_test as wct, ledger, plausibility

from .const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_WALLBOX_HOST,
    CONF_WALLBOX_MAX_AMPS,
    DEFAULT_CAPABILITY_TEST_WALLBOX,
    DEFAULT_WALLBOX_MAX_AMPS,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .coordinator import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)

SNAPSHOT_VERSION = 1
SNAPSHOT_KEY = f"{DOMAIN}.wallbox_capability_snapshot"
LEDGER_VERSION = 1
LEDGER_KEY = f"{DOMAIN}.wallbox_capability_ledger"
PLAUSIBILITY_VERSION = 1
PLAUSIBILITY_KEY = f"{DOMAIN}.wallbox_plausibility"

#: How much the ledger keeps, as the inverter's does.
LEDGER_MAX_RUNS = 50
LEDGER_MAX_AGE = timedelta(days=30)

#: How long a change to the plausibility state may wait before it is saved.
PLAUSIBILITY_SAVE_DELAY = 600


def _store(
    hass: HomeAssistant, entry: SungrowConfigEntry, key: str, version: int
) -> Store[dict[str, Any]]:
    return Store(hass, version, f"{key}.{entry.entry_id}")


def snapshot_store(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> Store[dict[str, Any]]:
    """Return this entry's wallbox snapshot store."""
    return _store(hass, entry, SNAPSHOT_KEY, SNAPSHOT_VERSION)


def plausibility_store(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> Store[dict[str, Any]]:
    """Return this entry's wallbox plausibility store."""
    return _store(hass, entry, PLAUSIBILITY_KEY, PLAUSIBILITY_VERSION)


def _ledger_store(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> Store[dict[str, Any]]:
    return _store(hass, entry, LEDGER_KEY, LEDGER_VERSION)


def firmware_of(device: Any) -> str:
    """Return the firmware a wallbox's evidence is kept for (input 21226)."""
    try:
        return str(device.field("version_string") or "")
    except AttributeError:
        return ""


class EntryWallboxPort:
    """The entry's own connection to its wallbox, as the procedure's port."""

    fresh = False

    def __init__(self, device: Any) -> None:
        """Bind the wallbox device the coordinator polls."""
        self._device = device

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read on the connection the entry already has."""
        words: list[int] = await self._device.async_read_words(space, address, count)
        return words

    async def read_fresh(self, space: str, address: int, count: int) -> list[int]:
        """Read as `read`: there is no second session, and `fresh` says so."""
        return await self.read(space, address, count)

    async def write(self, address: int, word: int) -> None:
        """Write one holding word."""
        await self._device.async_write_word(address, word)


def consented(entry: SungrowConfigEntry) -> bool:
    """Whether the owner has allowed the wallbox test to write."""
    return bool(
        entry.options.get(CONF_CAPABILITY_TEST_WALLBOX, DEFAULT_CAPABILITY_TEST_WALLBOX)
    )


def transport_of(entry: SungrowConfigEntry) -> str:
    """Name the path to the wallbox: its own address, or the dongle."""
    return "tls" if entry.options.get(CONF_WALLBOX_HOST) else "dongle"


def check_options(entry: SungrowConfigEntry) -> dict[str, bool]:
    """Return the checks the entry's leave allows: all of them, or none.

    The cap decides the three that go beyond the default (`cap_explicit`); the
    library skips those, and says why, until the owner has set it.
    """
    on = consented(entry)
    return {
        "follow": on,
        "below_minimum": on,
        "above_rating": on,
        "start_stop": on,
        "enable": on,
        "phase": on,
        "phase_charging": on,
        "fallback": on,
        "mileage": on,
    }


def run_options(
    entry: SungrowConfigEntry, skip: frozenset[str] = frozenset()
) -> wct.Options:
    """Return what a run may do: the leave, the cap, and what is not yet known.

    `skip` names the checks earlier runs established, which auto repeat leaves
    out so that a run every half hour does not stop a car for answers kept.
    """
    cap = entry.options.get(CONF_WALLBOX_MAX_AMPS)
    # An option's checks are left out only when every one of them is established.
    owned: dict[str, list[str]] = {}
    for name, (_need, option) in ledger.CHECKS.items():
        if option is not None:
            owned.setdefault(option, []).append(name)
    wanted = {
        option: allowed and not all(name in skip for name in owned[option])
        for option, allowed in check_options(entry).items()
    }
    return wct.Options(
        leave=consented(entry),
        max_amps=float(cap) if cap else DEFAULT_WALLBOX_MAX_AMPS,
        cap_explicit=bool(cap),
        current="output current" not in skip,
        **wanted,
    )


# -- the snapshot ---------------------------------------------------------------


async def async_leftover(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> dict[str, Any] | None:
    """Return a snapshot a run never finished with, or None."""
    data = await snapshot_store(hass, entry).async_load()
    if not data or not data.get("touched"):
        return None
    return {
        "raw": {int(a): int(w) for a, w in (data.get("raw") or {}).items()},
        "touched": [int(a) for a in data["touched"]],
    }


def _snapshot_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the snapshot as JSON: store keys are strings."""
    return {
        "raw": {str(a): w for a, w in snapshot["raw"].items()},
        "touched": list(snapshot["touched"]),
        "taken_at": dt_util.utcnow().isoformat(),
    }


# -- the ledger -----------------------------------------------------------------


async def async_ledger_runs(
    hass: HomeAssistant, entry: SungrowConfigEntry, firmware: str
) -> list[dict[str, Any]]:
    """Return the kept runs for this firmware, oldest first, within the bounds."""
    data = await _ledger_store(hass, entry).async_load()
    if not data or data.get("firmware") != firmware:
        return []
    cutoff = dt_util.utcnow() - LEDGER_MAX_AGE
    runs = [
        run
        for run in data.get("runs") or []
        if (when := dt_util.parse_datetime(str(run.get("read_at")))) is not None
        and when >= cutoff
    ]
    return runs[-LEDGER_MAX_RUNS:]


async def async_ledger_add(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    firmware: str,
    block: dict[str, Any],
) -> list[dict[str, Any]]:
    """Keep a finished run and return the runs that fold with it.

    A run of another path or session kind starts the ledger again, as the
    inverter's does; a dry run is never kept.
    """
    if not block.get("leave"):
        return [block]
    runs = await async_ledger_runs(hass, entry, firmware)
    if runs and ledger.fold_key(runs[-1]) != ledger.fold_key(block):
        runs = []
    runs = [*runs, block][-LEDGER_MAX_RUNS:]
    await _ledger_store(hass, entry).async_save({"firmware": firmware, "runs": runs})
    return runs


async def async_ledger_clear(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Forget every kept run."""
    await _ledger_store(hass, entry).async_remove()


async def async_plausibility_load(
    hass: HomeAssistant, entry: SungrowConfigEntry, firmware: str
) -> dict[str, Any] | None:
    """Return the kept plausibility state for this firmware, or None."""
    data = await plausibility_store(hass, entry).async_load()
    if not data or data.get("firmware") != firmware:
        return None
    state: dict[str, Any] | None = data.get("state")
    return state


def live_of(device: Any) -> ledger.Live:
    """Return the wallbox now, from what the coordinator last polled."""
    status: int | None
    try:
        raw = device.field("charging_status_raw")
        status = None if raw is None else int(raw)
    except AttributeError:
        status = None
    draws: list[float] = []
    for phase in "abc":
        try:
            value = device.field(f"phase_{phase}_current")
        except AttributeError:
            continue
        if value is not None:
            draws.append(float(value))
    try:
        setting = device.field("output_current_setting")
    except AttributeError:
        setting = None
    return ledger.Live(
        status,
        max(draws) if draws else None,
        None if setting is None else float(setting),
    )


def readings_of(device: Any) -> dict[str, float | None]:
    """Return the wallbox's polled fields the plausibility checks read."""
    out: dict[str, float | None] = {}
    for name in plausibility.FIELDS:
        try:
            value = device.field(name)
        except AttributeError:
            value = None
        out[name] = None if value is None else float(value)
    return out


# -- the run ---------------------------------------------------------------------


class WallboxTestRunner:
    """Drives one entry's wallbox test, and guarantees the wallbox comes back."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        *,
        skip: frozenset[str] = frozenset(),
    ) -> None:
        """Prepare a run; nothing is read or written until `async_run`."""
        self.hass = hass
        self.entry = entry
        self.skip = skip
        self._test: wct.WallboxCapabilityTest | None = None

    def _device(self) -> Any:
        coordinator = self.entry.runtime_data.wallbox
        assert coordinator is not None
        return coordinator.device

    async def _async_restore_leftover(self, port: EntryWallboxPort) -> None:
        """Put back what a run that never finished left, before anything else.

        Before a new snapshot replaces it: the new one would record the
        leftover's values as the owner's.
        """
        leftover = await async_leftover(self.hass, self.entry)
        if leftover is None:
            return
        _LOGGER.warning(
            "%s: a wallbox capability test did not finish; putting its settings "
            "back before this run",
            self.entry.title,
        )
        restorer = wct.WallboxCapabilityTest(port, wct.Options())
        restorer.snapshot = leftover
        await restorer.async_restore()
        if any(not row.restored for row in restorer.restores):
            # Kept: the registers still hold a test's values, and a new snapshot
            # would call them the owner's. The run is refused, not attempted.
            raise wct.Guard(5, "the wallbox settings of an earlier run are not back")
        await snapshot_store(self.hass, self.entry).async_remove()

    def request_stop(self) -> None:
        """Not interruptible mid-step: a step ends in seconds and a restore follows."""

    async def async_run(
        self, on_progress: Callable[[str], None] | None = None
    ) -> dict[str, Any]:
        """Run the procedure and return the run's block for the ledger."""
        device = self._device()
        port = EntryWallboxPort(device)
        store = snapshot_store(self.hass, self.entry)
        options = run_options(self.entry, self.skip)

        async def keep(snapshot: dict[str, Any]) -> None:
            # Before the first write, and awaited: a snapshot that reaches the
            # disk after the write it was taken to undo describes a house that
            # has already been changed.
            await store.async_save(_snapshot_data(snapshot))

        try:
            await self._async_restore_leftover(port)
        except wct.Guard as guard:
            outcome = wct.Outcome(
                guard.code, (), (), {"guard": guard.reason}, (guard.reason,)
            )
            return ledger.block(
                outcome,
                options,
                transport=transport_of(self.entry),
                fresh=False,
                firmware=firmware_of(device),
            )
        self._test = wct.WallboxCapabilityTest(
            port,
            options,
            on_snapshot=keep if options.leave else None,
            on_step=on_progress,
        )
        _LOGGER.warning(
            "%s: running the wallbox capability test. It writes to the wallbox's "
            "settings and puts each one back.",
            self.entry.title,
        )
        outcome = await self._test.async_run()
        if outcome.not_restored:
            _LOGGER.error(
                "%s: the wallbox capability test could not put %s back; the "
                "snapshot is kept and the next run restores it first",
                self.entry.title,
                ", ".join(str(row.address + 1) for row in outcome.not_restored),
            )
        else:
            await store.async_remove()
        return ledger.block(
            outcome,
            options,
            transport=transport_of(self.entry),
            fresh=port.fresh,
            firmware=firmware_of(device),
        )
