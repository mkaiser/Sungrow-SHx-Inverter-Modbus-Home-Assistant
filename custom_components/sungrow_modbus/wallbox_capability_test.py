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

**A wallbox an inverter manages is tested at the inverter.** Its own registers
are the inverter's to drive (gerd, 2026-11-14), so where an inverter entry in
this Home Assistant left the wallbox to this entry (`wallbox_elsewhere`), a run
is `sungrow_modbus.wallbox.managed_test`: it writes that inverter entry's EV
charger block, reads this entry's wallbox for what the car does, and holds both
entries' polling off. A wallbox with no inverter entry beside it is not written
from here at all: nothing an entry has can say no inverter manages it.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from sungrow_modbus.wallbox import (
    capability_test as wct,
    ledger,
    managed_test as mt,
    plausibility,
)

from .const import (
    CONF_CAPABILITY_TEST_WALLBOX,
    CONF_KIND,
    CONF_WALLBOX_MAX_AMPS,
    DEFAULT_CAPABILITY_TEST_WALLBOX,
    DEFAULT_WALLBOX_MAX_AMPS,
    DOMAIN,
    KIND_WALLBOX,
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
    """Whether the owner has allowed the wallbox test to write.

    Only a wallbox entry of its own writes, at the wallbox's own address. A
    wallbox an inverter entry reads through its dongle stays read only: the
    direct path is the one this integration prefers, and the dongle's few
    sessions stay the inverter's.
    """
    return entry.data.get(CONF_KIND) == KIND_WALLBOX and bool(
        entry.options.get(CONF_CAPABILITY_TEST_WALLBOX, DEFAULT_CAPABILITY_TEST_WALLBOX)
    )


def declared_standalone(entry: SungrowConfigEntry) -> bool:
    """Whether the owner has said no inverter manages this wallbox.

    Never, yet: no option asks it, and a wrong yes writes registers an inverter
    overwrites. The one seam the tests of the write machinery replace.
    """
    return False


def managing_entry(
    hass: HomeAssistant | None, entry: SungrowConfigEntry
) -> SungrowConfigEntry | None:
    """Return the loaded inverter entry that manages this entry's wallbox, or None.

    The inverter entry that found this wallbox behind its dongle and left it to
    this entry (`SungrowRuntimeData.wallbox_elsewhere`). Behind the dongle means
    on the inverter's bus, which is what an inverter manages.
    """
    if hass is None or entry.data.get(CONF_KIND) != KIND_WALLBOX or not entry.unique_id:
        return None
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == entry.entry_id:
            continue
        runtime = getattr(other, "runtime_data", None)
        if getattr(runtime, "wallbox_elsewhere", None) == entry.unique_id:
            return other
    return None


def transport_of(entry: SungrowConfigEntry) -> str:
    """Name the path to the wallbox: its own address, or the dongle."""
    return "tls" if entry.data.get(CONF_KIND) == KIND_WALLBOX else "dongle"


def check_options(
    entry: SungrowConfigEntry, hass: HomeAssistant | None = None
) -> dict[str, bool]:
    """Return the checks the entry's leave allows, by who drives the wallbox.

    A wallbox declared standalone gets its own registers' checks; one an
    inverter entry here manages gets the inverter's (`managed`) and start/stop;
    any other gets none, so auto repeat waits for nothing it cannot do. The cap
    decides the checks that go beyond the default (`cap_explicit`).
    """
    on = consented(entry)
    alone = on and declared_standalone(entry)
    managed = on and not alone and managing_entry(hass, entry) is not None
    return {
        "standalone": alone,
        "follow": alone,
        "below_minimum": alone,
        "above_rating": alone,
        "start_stop": alone or managed,
        "enable": alone,
        "phase": alone,
        "phase_charging": alone,
        "fallback": alone,
        "mileage": alone,
        "managed": managed,
    }


def run_options(
    entry: SungrowConfigEntry, skip: frozenset[str] = frozenset()
) -> wct.Options:
    """Return what a run of the wallbox's own checks may do.

    `skip` names the checks earlier runs established, which auto repeat leaves
    out so that a run every half hour does not stop a car for answers kept.
    """
    cap = entry.options.get(CONF_WALLBOX_MAX_AMPS)
    # An option's checks are left out only when every one of them is established.
    owned: dict[str, list[str]] = {}
    for name, (_need, option) in ledger.CHECKS.items():
        if option is not None:
            owned.setdefault(option, []).append(name)
    fields = wct.Options.__dataclass_fields__
    wanted = {
        option: allowed and not all(name in skip for name in owned[option])
        for option, allowed in check_options(entry).items()
        if option in fields and option != "standalone"
    }
    return wct.Options(
        leave=consented(entry),
        max_amps=float(cap) if cap else DEFAULT_WALLBOX_MAX_AMPS,
        cap_explicit=bool(cap),
        current="output current" not in skip,
        # Nothing here can tell a wallbox an inverter manages from one no
        # inverter does, and a managed one overwrites every write (gerd,
        # 2026-11-14): unless declared, the library writes nothing and says why.
        standalone=declared_standalone(entry),
        **wanted,
    )


def managed_run_options(
    entry: SungrowConfigEntry, skip: frozenset[str] = frozenset()
) -> mt.Options:
    """Return what a run at the managing inverter may do, the owner's leave first."""
    cap = entry.options.get(CONF_WALLBOX_MAX_AMPS)
    return mt.Options(
        leave=consented(entry),
        max_amps=float(cap) if cap else DEFAULT_WALLBOX_MAX_AMPS,
        current="user current" not in skip,
        floor="floor" not in skip,
        start_stop="start/stop" not in skip,
    )


class InverterBlockPort:
    """The managing inverter entry's own connection, as the managed test's port."""

    def __init__(self, device: Any) -> None:
        """Bind the inverter device that entry polls."""
        self._device = device

    async def read(self, address: int, count: int) -> list[int]:
        """Read holding words on that entry's connection."""
        words: list[int] = await self._device.async_read_words(
            "holding", address, count
        )
        return words

    async def write(self, address: int, word: int) -> None:
        """Write one holding word."""
        await self._device.async_write_word(address, word)


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
        "managed": bool(data.get("managed")),
        "charging_at_start": bool(data.get("charging_at_start")),
    }


def _snapshot_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the snapshot as JSON: store keys are strings."""
    return {
        "raw": {str(a): w for a, w in snapshot["raw"].items()},
        "touched": list(snapshot["touched"]),
        "taken_at": dt_util.utcnow().isoformat(),
        "managed": bool(snapshot.get("managed")),
        "charging_at_start": bool(snapshot.get("charging_at_start")),
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

    async def _async_restore_leftover(
        self, port: EntryWallboxPort, inverter: InverterBlockPort | None = None
    ) -> None:
        """Put back what a run that never finished left, before anything else.

        Before a new snapshot replaces it: the new one would record the
        leftover's values as the owner's. A managed run's snapshot is the
        inverter's block and goes back through the inverter entry; without one
        it cannot, and the run is refused.
        """
        leftover = await async_leftover(self.hass, self.entry)
        if leftover is None:
            return
        _LOGGER.warning(
            "%s: a wallbox capability test did not finish; putting its settings "
            "back before this run",
            self.entry.title,
        )
        if leftover["managed"]:
            if inverter is None:
                raise wct.Guard(
                    5, "an earlier run's inverter settings are not back: no inverter"
                )
            managed = mt.ManagedWallboxTest(inverter, port, mt.Options())
            managed.snapshot = leftover
            await managed.async_restore()
            if not managed.restored:
                raise wct.Guard(
                    5, f"an earlier run left the house changed: {mt.ON_SITE}"
                )
        else:
            restorer = wct.WallboxCapabilityTest(port, wct.Options())
            restorer.snapshot = leftover
            await restorer.async_restore()
            if any(not row.restored for row in restorer.restores):
                # Kept: the registers still hold a test's values, and a new
                # snapshot would call them the owner's. The run is refused.
                raise wct.Guard(
                    5, "the wallbox settings of an earlier run are not back"
                )
        await snapshot_store(self.hass, self.entry).async_remove()

    def request_stop(self) -> None:
        """Not interruptible mid-step: a step ends in seconds and a restore follows."""

    async def async_run(
        self, on_progress: Callable[[str], None] | None = None
    ) -> dict[str, Any]:
        """Run the procedure and return the run's block for the ledger."""
        inverter_entry = managing_entry(self.hass, self.entry)
        if inverter_entry is not None:
            return await self._async_run_managed(inverter_entry, on_progress)
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

    async def _async_run_managed(
        self,
        inverter_entry: SungrowConfigEntry,
        on_progress: Callable[[str], None] | None,
    ) -> dict[str, Any]:
        """Test the wallbox at the inverter that manages it; keep the run."""
        device = self._device()
        reader = EntryWallboxPort(device)
        port = InverterBlockPort(
            inverter_entry.runtime_data.inverter_coordinator.device
        )
        store = snapshot_store(self.hass, self.entry)
        options = managed_run_options(self.entry, self.skip)

        async def keep(snapshot: dict[str, Any]) -> None:
            # Before the first write, and awaited, as for the wallbox's own test.
            await store.async_save(_snapshot_data({**snapshot, "managed": True}))

        # The inverter entry polls the same inverter: held off as this one is.
        async with inverter_entry.runtime_data.async_paused():
            try:
                await self._async_restore_leftover(reader, port)
            except wct.Guard as guard:
                return ledger.managed_block(
                    mt.Outcome(guard.code, (), False, {"guard": guard.reason}),
                    options,
                    firmware=firmware_of(device),
                )
            test = mt.ManagedWallboxTest(
                port,
                reader,
                options,
                on_snapshot=keep if options.leave else None,
                on_step=on_progress,
            )
            _LOGGER.warning(
                "%s: running the wallbox capability test at the inverter that "
                "manages it (%s). It writes the inverter's EV charger settings "
                "and puts them back, the charge included.",
                self.entry.title,
                inverter_entry.title,
            )
            outcome = await test.async_run()
        if outcome.restored:
            await store.async_remove()
        else:
            _LOGGER.error(
                "%s: the wallbox capability test left the house changed: %s",
                self.entry.title,
                mt.ON_SITE,
            )
        return ledger.managed_block(outcome, options, firmware=firmware_of(device))
