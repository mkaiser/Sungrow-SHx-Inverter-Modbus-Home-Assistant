"""Who writes to an entry's device: the owner's controls, or a capability test.

Never both at once. A capability test snapshots every control it will touch,
writes test values, watches what the house does and writes the snapshot back.
A control written by the owner in between is overwritten by that restore, and
what the house does because of it is read as the test's effect. So while a
run writes, the controls refuse, with an error that names the run, and the
run steps aside for the owner the other way round:

- **A run holds the controls** from just before its snapshot is flushed until
  its restore is checked (`async_test_owns_writes`). Part A only reads and
  holds nothing. A wallbox test that writes an inverter entry's EV charger
  block holds that entry's controls too: the block is the inverter's.
- **A control refuses while a run holds it** (`refuse_while_test_writes`),
  before a byte is sent, as a `ServiceValidationError` an automation can see.
  The controls stay available: Home Assistant drops a call to an unavailable
  entity without a word, and an automation would believe it had written.
  *Diagnosis: controls held by test* shows the hold on a dashboard.
- **Auto repeat waits after the owner wrote** (`owner_quiet_until`): a run
  would read the house still answering the owner's change. `OWNER_QUIET` for
  the inverter, `OWNER_QUIET_EV` for a wallbox an inverter manages, whose
  charging session is the owner's.
- **The owner's write replaces a leftover snapshot's entry**
  (`async_owner_wrote`). A run that did not finish leaves its snapshot, and
  the next restore would write it back over a value the owner has set since.
  The owner's value is the one the house should keep: the inverter's snapshot
  drops that field, a managed wallbox's takes the owner's word.

What none of this can hold: a write that does not go through these entities,
`modbus.write_register` or another program on its own connection.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from modbus_connection.model import PackedBitsField, RegisterField

from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.hybrid_inverter.capabilities import Capability
from sungrow_modbus.hybrid_inverter.registers import COMPONENTS

from .const import DOMAIN

if TYPE_CHECKING:
    from modbus_connection.model import Component

    from homeassistant.core import HomeAssistant

    from .coordinator import SungrowConfigEntry, SungrowRuntimeData

_LOGGER = logging.getLogger(__name__)

#: How long auto repeat waits after the owner changed an inverter control.
#: Long enough for the house to settle on the owner's value (a battery limit
#: is followed within a minute or two), short against the wait between runs.
OWNER_QUIET = timedelta(minutes=10)

#: How long a wallbox run waits after the owner changed the EV charger block.
#: Short enough that a car started from Home Assistant can be tested in its own
#: session, which an hour outlasted (gerd's, 2026-11-24). A run interrupts the
#: charge for about two minutes, and a check that has passed is not run again.
OWNER_QUIET_EV = timedelta(minutes=10)

#: The component the managed wallbox's controls write.
EV_CHARGER = "ev_charger"

#: Domain and translation key of the entity this module adds to an entry with
#: controls; `scripts/generate/descriptions.py` names it from here.
CONTROL_ENTITIES: tuple[tuple[str, str], ...] = (
    ("binary_sensor", "controls_held_by_test"),
)


@dataclass(frozen=True)
class WriteOwner:
    """A run holding an entry's controls: whose run, and since when."""

    by: str
    """The title of the entry whose run it is: the wallbox entry's, when its
    test writes the inverter's EV charger block."""
    since: datetime


def holder(runtime: SungrowRuntimeData) -> WriteOwner | None:
    """Return the run holding this entry's controls, or None."""
    return runtime.write_owners[0] if runtime.write_owners else None


def _notify(entry: SungrowConfigEntry) -> None:
    """Tell the entry's diagnosis entities the hold changed."""
    runner = getattr(entry.runtime_data, "diagnosis", None)
    if runner is not None:
        runner.async_notify()


@asynccontextmanager
async def async_test_owns_writes(
    entries: Iterable[SungrowConfigEntry], by: str
) -> AsyncIterator[None]:
    """Hold these entries' controls for the duration, and let go in a `finally`.

    A list per entry rather than a flag, so a run inside another's hold (a
    wallbox run beside an inverter run on the same entry) cannot release the
    other's.
    """
    owner = WriteOwner(by=by, since=dt_util.utcnow())
    held = list(entries)
    for entry in held:
        entry.runtime_data.write_owners.append(owner)
        _notify(entry)
    try:
        yield
    finally:
        for entry in held:
            entry.runtime_data.write_owners.remove(owner)
            _notify(entry)


def refuse_while_test_writes(runtime: SungrowRuntimeData, target: str) -> None:
    """Raise when a run holds the controls; `target` names what was not written."""
    owner = holder(runtime)
    if owner is None:
        return
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="test_has_link",
        translation_placeholders={
            "target": target,
            "by": owner.by,
            "since": f"{dt_util.as_local(owner.since):%H:%M}",
        },
    )


def cluster_busy(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> SungrowConfigEntry | None:
    """Return another member of the cluster whose controls a run holds, or None.

    A cluster slave's 13050 follows the master's (wiki:
    does-a-cluster-slave-mirror-the-masters-ems-mode), so a run on one member
    changes what a run on the other reads and cannot put back: swo14's slave
    ended in outcome 5 beside the host's run. No register says *which* cluster
    an inverter is in, so two members on one instance are taken for one
    cluster; a house with two clusters tests them one after the other.

    Only runs of this Home Assistant are seen. A restore is never refused.
    """
    runtime = entry.runtime_data
    if Capability.CLUSTER_MEMBER not in runtime.capabilities:
        return None
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == entry.entry_id:
            continue
        theirs = getattr(other, "runtime_data", None)
        if (
            theirs is not None
            and Capability.CLUSTER_MEMBER in getattr(theirs, "capabilities", ())
            and holder(theirs) is not None
        ):
            return other
    return None


def refuse_while_cluster_tested(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Raise when another member of the cluster is under test."""
    if (other := cluster_busy(hass, entry)) is None:
        return
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="cluster_under_test",
        translation_placeholders={"title": entry.title, "other": other.title},
    )


def owner_quiet_until(
    runtime: SungrowRuntimeData,
    quiet: timedelta,
    components: Iterable[str] | None = None,
    now: datetime | None = None,
) -> datetime | None:
    """Return when a run may start after the owner's last write, or None if now.

    `components` limits the writes counted, None counting every one.
    """
    wanted = None if components is None else set(components)
    times = [
        when
        for component, when in runtime.owner_writes.items()
        if wanted is None or component in wanted
    ]
    if not times:
        return None
    until = max(times) + quiet
    return until if until > (now or dt_util.utcnow()) else None


def written(
    component: Component, writes: Sequence[tuple[str, Any]]
) -> list[tuple[int, int | None]]:
    """Return each write as its protocol address and the word it sends.

    The word only where the field encodes one plain word by itself: a packed
    field merges into the register's other bits, a validator may change the
    value and a scale register needs a read, so those say None.
    """
    out: list[tuple[int, int | None]] = []
    for name, value in writes:
        resolved = component.resolved_fields.get(name)
        if resolved is None:
            continue
        field = resolved.field
        word: int | None = None
        if (
            isinstance(field, RegisterField)
            and not isinstance(field, PackedBitsField)
            and field.scale_register is None
            and not callable(field.writable)
            and field.count == 1
        ):
            try:
                words = field.encode(value)
            except (TypeError, ValueError):
                words = []
            word = int(words[0]) if len(words) == 1 else None
        out.append((resolved.address, word))
    return out


async def async_owner_wrote(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    component: str,
    writes: Sequence[tuple[int, int | None]],
) -> None:
    """Record a write the owner made, and keep a leftover snapshot from undoing it."""
    entry.runtime_data.owner_writes[component] = dt_util.utcnow()
    addresses = {address for address, _word in writes}
    try:
        await _async_amend_inverter_leftover(hass, entry, addresses)
        if component == EV_CHARGER:
            await _async_amend_managed_leftover(hass, entry, writes)
    except Exception:  # the write succeeded; the leftover keeps its repair
        _LOGGER.exception(
            "%s: the owner's write could not be taken into a capability test's "
            "leftover snapshot; its repair would still write the old value back",
            entry.title,
        )


def _address_of(device: Any, name: str) -> int | None:
    """Return the protocol address of an inverter field, or None."""
    for attribute in COMPONENTS:
        resolved = device.component(attribute).resolved_fields.get(name)
        if resolved is not None:
            return int(resolved.address)
    return None


async def _async_amend_inverter_leftover(
    hass: HomeAssistant, entry: SungrowConfigEntry, addresses: set[int]
) -> None:
    """Drop the written registers from this entry's leftover snapshot."""
    from .capability_test import async_forget, async_keep, async_leftover
    from .repairs import async_clear, async_raise

    snapshot = await async_leftover(hass, entry)
    if snapshot is None:
        return
    device = entry.runtime_data.inverter_coordinator.device
    dropped = [
        name for name in snapshot.values if _address_of(device, name) in addresses
    ]
    if not dropped:
        return
    for name in dropped:
        snapshot.values.pop(name, None)
        snapshot.raw.pop(name, None)
        snapshot.bounds.pop(name, None)
        if snapshot.touched is not None and name in snapshot.touched:
            snapshot.touched.remove(name)
    _LOGGER.warning(
        "%s: the owner set %s after a capability test left it changed; the "
        "test's leftover no longer puts it back",
        entry.title,
        ", ".join(dropped),
    )
    if not snapshot.values and snapshot.stopped_at is None:
        await async_forget(hass, entry)
        async_clear(hass, entry)
        return
    await async_keep(hass, entry, snapshot)
    async_raise(hass, entry, snapshot)


async def _async_amend_managed_leftover(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    writes: Sequence[tuple[int, int | None]],
) -> None:
    """Give a managed wallbox's leftover snapshot the owner's words."""
    from .repairs import async_raise_wallbox
    from .wallbox_capability_test import async_keep_leftover, async_leftover

    serial = entry.runtime_data.wallbox_elsewhere
    if serial is None:
        return
    wallbox_entry = next(
        (
            other
            for other in hass.config_entries.async_entries(DOMAIN)
            if other.unique_id == serial
            and other.entry_id != entry.entry_id
            and getattr(other, "runtime_data", None) is not None
        ),
        None,
    )
    if wallbox_entry is None:
        return
    leftover = await async_leftover(hass, wallbox_entry)
    if leftover is None or not leftover["managed"]:
        return
    raw: dict[int, int] = leftover["raw"]
    taken: list[int] = []
    for address, word in writes:
        if address not in raw:
            continue
        if word is None:
            _LOGGER.warning(
                "%s: register %d was written, but its word is not known here; "
                "the wallbox test's leftover still puts its own back",
                entry.title,
                address + 1,
            )
            continue
        raw[address] = word
        taken.append(address)
        if address == ev.CHARGING and word == ev.OFF:
            # The owner stopped the charge: the restore must not restart it.
            leftover["charging_at_start"] = False
    if not taken:
        return
    _LOGGER.warning(
        "%s: the owner set register(s) %s after a wallbox capability test left "
        "them changed; the test's leftover now puts the owner's value back",
        entry.title,
        ", ".join(str(address + 1) for address in taken),
    )
    await async_keep_leftover(hass, wallbox_entry, leftover)
    await async_raise_wallbox(hass, wallbox_entry, leftover)
