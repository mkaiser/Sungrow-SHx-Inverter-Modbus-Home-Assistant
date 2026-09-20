"""Taking over the entity ids the YAML package created.

`modbus_sungrow.yaml` produces `sensor.total_dc_power`. This integration,
being device-scoped as a modern integration should be, would produce
`sensor.sh10rt_total_dc_power`. Recorder history and every dashboard card are
keyed by the entity_id, so which of the two an entity claims decides whether
years of data and a user's whole dashboard survive the switch.

The mechanism is `async_get_or_create(..., suggested_object_id=...)`, which
the entity registry documents as **not** prefixed with the device name. The
entities are registered on the legacy ids *before* the platforms add them; the
platforms then find the entries already there and keep them. History simply
continues — there is no recorder API involved, nothing is copied and nothing is
deleted.

What this deliberately does **not** change is the entities themselves. They
keep `has_entity_name`, their translation keys, device and state classes and
diagnostic categories, exactly as in a core integration. Only the id is
inherited, so a migrated installation is not a second-class one that has to be
maintained differently forever.

Three traps, each of which silently produces a wrong result rather than an
error, and each asserted in `tests/test_migration.py`:

* an id is handed out only if it is free in the registry **and** in the state
  machine, so the YAML package has to be unloaded — otherwise the registry
  appends `_2` and says nothing;
* removing the package does **not** free its registry rows. A YAML platform
  entity has no config entry to be cleaned up with, so its registry entry
  outlives it as an orphan and goes on reserving the id. It has to be removed
  before the id can be claimed — see `_async_release`;
* a rename *into* an id the recorder already knows is refused with nothing but
  a log line, which is why the id is claimed at creation rather than renamed
  into afterwards.
"""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from sungrow_modbus import Capability

from .const import CONF_LEGACY_SLOT, DOMAIN
from .derived_descriptions import DERIVED_BINARY_SENSORS, DERIVED_SENSORS
from .entity import SungrowEntityDescription
from .number_descriptions import NUMBER_DESCRIPTIONS
from .select_descriptions import SELECT_DESCRIPTIONS
from .sensor_descriptions import SENSOR_DESCRIPTIONS
from .switch_descriptions import SWITCH_DESCRIPTIONS

_LOGGER = logging.getLogger(__name__)

#: Every entity the integration can create, with the platform it belongs to.
DESCRIPTIONS: tuple[tuple[str, SungrowEntityDescription], ...] = (
    *((Platform.SENSOR.value, d) for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)),
    *((Platform.BINARY_SENSOR.value, d) for d in DERIVED_BINARY_SENSORS),
    # A `number` reads the same register as a sensor but is a different
    # entity, with its own id and its own history. The YAML had both, so a
    # migration has to claim both.
    *((Platform.NUMBER.value, d) for d in NUMBER_DESCRIPTIONS),
    *((Platform.SWITCH.value, d) for d in SWITCH_DESCRIPTIONS),
    *((Platform.SELECT.value, d) for d in SELECT_DESCRIPTIONS),
)


#: The YAML package's own sensor holding the inverter's serial number.
#:
#: The key to a two-inverter migration, and the reason it needs no question.
#: Its **state** is that inverter's serial, so an entry can find which of the
#: YAML's numbered slots was its own device by comparing against a serial it
#: already knows -- rather than asking the owner to remember which physical
#: inverter they called `inv 2` when they set the package up, possibly years
#: ago, in a file they may since have deleted.
LEGACY_SERIAL_UNIQUE_ID = "sg_inverter_serial"

#: What *registered* that sensor, which is not the domain it lives in. The
#: YAML package reads the serial over Modbus, so the registry records the
#: platform as `modbus` while the entity is a `sensor`. Getting this wrong
#: costs nothing visible -- the lookup simply never matches, and a
#: multi-inverter house silently migrates as though it had one inverter.
LEGACY_SERIAL_PLATFORM = "modbus"
LEGACY_SERIAL_DOMAIN = "sensor"

#: The suffixes a YAML install can have used, in the order they are tried.
#:
#: `legacy/modbus_sungrow.yaml` carries none;
#: `modbus_sungrow_multiple_inverters_<n>.yaml` appends ` inv <n>` to every
#: name and `_inv_<n>` to every unique_id. Both shapes exist in the wild for a
#: first inverter: the generator makes an `_inv_1` file, so a two-inverter
#: house may be running either the plain file plus `_inv_2`, or `_inv_1` plus
#: `_inv_2`. Which is why this is a search rather than arithmetic on an index.
LEGACY_SUFFIXES: tuple[str, ...] = ("", "_inv_1", "_inv_2", "_inv_3")


@callback
def async_legacy_suffix(hass: HomeAssistant, serial: str | None) -> str | None:
    """Return which of the YAML package's inverter slots holds this device.

    `""` for a single-inverter install, `"_inv_2"` for the second inverter of a
    multi-inverter one, and `None` when the question cannot be answered --
    which is not a failure and must not be treated as `""`. Claiming the first
    inverter's ids for the second inverter's entry would hand one device the
    other's years of history, silently, and there is no undoing that by
    guessing again.

    Answered by **evidence rather than by asking**: the YAML's serial sensor
    for each slot holds that inverter's own serial as its state, and this entry
    already knows which serial it is talking to. A match is proof; the absence
    of one is only ignorance.

    Unanswerable in two ordinary cases, both of which mean the YAML package is
    not running right now: the package has already been removed, or the sensor
    is unavailable because the inverter is. So a caller that gets `None` should
    fall back to what it has stored rather than re-deriving.
    """
    if not serial:
        return None
    registry = er.async_get(hass)
    for suffix in LEGACY_SUFFIXES:
        entity_id = registry.async_get_entity_id(
            LEGACY_SERIAL_DOMAIN,
            LEGACY_SERIAL_PLATFORM,
            f"{LEGACY_SERIAL_UNIQUE_ID}{suffix}",
        )
        if entity_id is None:
            continue
        state = hass.states.get(entity_id)
        if state is not None and state.state == serial:
            _LOGGER.debug(
                "Serial %s matches the YAML package's %s slot (%s)",
                serial,
                suffix or "single-inverter",
                entity_id,
            )
            return suffix
    return None


def legacy_entity_id(
    platform: str, description: SungrowEntityDescription, suffix: str = ""
) -> str | None:
    """Return the entity_id the YAML package gave this entity, if it had one.

    Derived the same way Home Assistant derived it in the first place — by
    slugifying the name — rather than from a table, so the two cannot drift.

    `suffix` is a slot from `LEGACY_SUFFIXES`, and it is applied to the **name**
    rather than to the finished id, because that is where the generator applies
    it: `modbus_sungrow_multiple_inverters_2.yaml` renames `Total DC power` to
    `Total DC power inv 2`, and Home Assistant slugified *that*. Appending
    `_inv_2` to the id reaches the same answer here and would stop doing so the
    first time a name contained something slugify treats differently.
    """
    if description.legacy_name is None:
        return None
    name = description.legacy_name
    if suffix:
        name = f"{name} inv {suffix.removeprefix('_inv_')}"
    return f"{platform}.{slugify(name)}"


def legacy_unique_id(description: SungrowEntityDescription, suffix: str = "") -> str:
    """Return the YAML unique_id for one description in one inverter slot."""
    return f"{description.legacy_unique_id}{suffix}"


def legacy_entity_ids(suffix: str = "") -> frozenset[str]:
    """Return the entity_id each YAML entity had **if it was never renamed**.

    Only the naming tests use this. Identification goes through
    `async_legacy_entities`, which asks the registry rather than assuming.
    """
    return frozenset(
        entity_id
        for platform, description in DESCRIPTIONS
        if (entity_id := legacy_entity_id(platform, description, suffix)) is not None
    )


@callback
def async_legacy_entities(
    hass: HomeAssistant, suffix: str = ""
) -> dict[tuple[str, str], str]:
    """Return each description's YAML entity, as `{(platform, key): id now}`.

    Keyed by platform *and* key, because a setting has two descriptions with
    the same key: `sensor.battery_min_soc` read the register and
    `number.battery_min_soc` wrote it. Keying by the key alone let the second
    overwrite the first, and the sensor then lost its id to a `_2` suffix
    while the number took the one it wanted.

    Looked up by `unique_id` and platform, never by entity_id. That matters
    twice.

    It is the only **correct** identification. 69 of the 127 legacy ids carry
    nothing Sungrow-specific — `sensor.battery_level`, `sensor.grid_frequency`,
    `binary_sensor.battery_charging` — so matching on the id alone would
    mistake a battery integration's entity for one of ours, and then delete
    its registry entry in order to take the id.

    And it follows **renames**. A user who renamed `sensor.total_pv_generation`
    took their history with them, because the recorder keys on the id. Asking
    what registered the entity finds where the history actually is, where
    slugifying the YAML's old name would claim an id nothing has written to
    for years.
    """
    registry = er.async_get(hass)
    found: dict[tuple[str, str], str] = {}
    for platform, description in DESCRIPTIONS:
        if not (description.legacy_unique_id and description.legacy_platform):
            continue
        entity_id = registry.async_get_entity_id(
            platform,
            description.legacy_platform,
            legacy_unique_id(description, suffix),
        )
        if entity_id is not None:
            found[platform, description.key] = entity_id
    return found


@callback
def async_legacy_ids_known(hass: HomeAssistant, suffix: str = "") -> set[str]:
    """Return the entity ids the YAML package's own entities hold right now.

    Evidence that it is or was installed. `suffix` narrows that to one
    inverter's slot, so a second inverter is offered its *own* history rather
    than the first one's -- which is what it would be offered if this kept
    answering for the unsuffixed set.
    """
    return set(async_legacy_entities(hass, suffix).values())


@callback
def keys_for(entity_ids: set[str], suffix: str = "") -> frozenset[tuple[str, str]]:
    """Return the (platform, key) pairs whose un-renamed legacy id is here."""
    return frozenset(
        (platform, description.key)
        for platform, description in DESCRIPTIONS
        if legacy_entity_id(platform, description, suffix) in entity_ids
    )


async def async_legacy_ids_with_history(
    hass: HomeAssistant, suffix: str = ""
) -> set[str]:
    """Return legacy ids the recorder still holds rows for.

    The registry lookup is the good path, but it is not the only evidence that
    a YAML package was here. `doc/cleanup_entities.md` has told users for years
    to delete the orphaned entries a removed YAML platform leaves behind, and
    plenty have. Their registry is then clean while the recorder still holds
    years of rows under those ids — history that is perfectly migratable and
    that the registry can no longer point at.

    Without this the setup dialog would say nothing, hand out device-scoped
    ids, and strand the lot, with no way for the user to opt in afterwards.

    Falls back on the ids the YAML's names slugify to, since there is no
    registry entry left to ask. That cannot follow a rename — but a user who
    renamed an entity and then deleted its registry entry has already lost the
    thread themselves.

    Returns nothing when the recorder is not set up, which is legitimate: no
    recorder means no history to preserve.
    """
    if RECORDER_DOMAIN not in hass.config.components:
        return set()

    from sqlalchemy import select

    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.db_schema import StatesMeta
    from homeassistant.components.recorder.util import session_scope

    wanted = legacy_entity_ids(suffix)

    def _query() -> set[str]:
        with session_scope(hass=hass, read_only=True) as session:
            rows = session.execute(
                select(StatesMeta.entity_id).where(StatesMeta.entity_id.in_(wanted))
            )
            return {row[0] for row in rows}

    try:
        return await get_instance(hass).async_add_executor_job(_query)
    except (SQLAlchemyError, RuntimeError) as err:
        # A database that will not answer is not a reason to fail setup; it
        # only means this piece of evidence is unavailable.
        _LOGGER.debug("Could not ask the recorder about legacy entities: %s", err)
        return set()


@callback
def async_legacy_ids_live(hass: HomeAssistant, suffix: str = "") -> set[str]:
    """Return the legacy ids that still have a state.

    A live entity holds its id against the registry, so adopting one would
    produce `sensor.total_dc_power_2` instead — silently. This is the check
    that turns that into an error the user can act on: remove the YAML
    package and restart.
    """
    return {
        entity_id
        for entity_id in async_legacy_ids_known(hass, suffix)
        if hass.states.get(entity_id) is not None
    }


@callback
def async_claim_legacy_ids(
    hass: HomeAssistant,
    entry: ConfigEntry,
    serial: str,
    capabilities: frozenset[Capability],
    with_history: frozenset[tuple[str, str]] = frozenset(),
) -> list[str]:
    """Register this integration's entities on the YAML package's ids.

    Runs before the platforms are forwarded, so the entries are already in
    place when the entities are added. Returns what was claimed, for the log.

    Only entities that will actually be created are claimed: pre-registering
    MPPT3 on a two-tracker inverter would leave a registry entry that nothing
    ever fills, which is the dead-entity problem this integration exists to
    avoid.

    Which **slot** of a multi-inverter YAML install this device was comes from
    the entry, written there when it was set up. It is not re-derived here, and
    that is the point: detection needs the YAML package to be running, and by
    the second setup it usually is not -- the user removed it, which is what
    the migration told them to do. Re-deriving would answer `None` then, and a
    `None` read as "no suffix" would point the second inverter at the first
    one's ids.
    """
    suffix = entry.data.get(CONF_LEGACY_SLOT) or ""
    registry = er.async_get(hass)
    claimed: list[str] = []
    legacy = async_legacy_entities(hass, suffix)

    for platform, description in DESCRIPTIONS:
        legacy_id = legacy.get((platform, description.key))
        if legacy_id is None and (platform, description.key) in with_history:
            # No registry entry left, but the recorder still has the rows.
            legacy_id = legacy_entity_id(platform, description, suffix)
        if legacy_id is None:
            continue
        if (
            description.requires is not None
            and description.requires not in capabilities
        ):
            continue

        unique_id = f"{serial}_{description.key}"
        if registry.async_get_entity_id(platform, DOMAIN, unique_id) is not None:
            # Already registered, from an earlier run of this entry.
            continue
        if not _async_release(hass, registry, legacy_id):
            continue

        created = registry.async_get_or_create(
            platform,
            DOMAIN,
            unique_id,
            suggested_object_id=legacy_id.split(".", 1)[1],
            config_entry=entry,
        )
        if created.entity_id != legacy_id:
            # The id was taken after all. Leaving the entry behind would ship
            # the `_2` suffix this whole mechanism exists to avoid, so drop it
            # and let the platform assign a device-scoped id instead.
            _LOGGER.warning(
                "Could not take over %s; it is already in use. %s will get a "
                "device-scoped id instead",
                legacy_id,
                description.key,
            )
            registry.async_remove(created.entity_id)
            continue
        claimed.append(legacy_id)

    return claimed


@callback
def _async_release(
    hass: HomeAssistant, registry: er.EntityRegistry, legacy_id: str
) -> bool:
    """Free a legacy id from the registry. False if it cannot be freed.

    Removing `modbus_sungrow.yaml` does not remove its entity registry
    entries. A YAML platform entity belongs to no config entry, so nothing
    ever cleans its row up: it stays behind as an orphan, shows in the UI as
    unavailable, and — the part that matters here — goes on reserving the
    entity_id. Claiming the id means removing that row first.

    **This does not touch any history.** The recorder keys its rows by
    entity_id through `states_meta`, which knows nothing about the registry,
    so the row is exactly what the new entity then writes into. That is also
    why the reverse migration works: nothing was deleted, only re-pointed.

    Removal is refused while the entity is still live, because then the YAML
    package is still loaded and the user should be removing it properly rather
    than having it pulled out from under a running instance.
    """
    existing = registry.async_get(legacy_id)
    if existing is None:
        return True
    if existing.platform == DOMAIN:
        # Ours already, from a previous setup of this entry.
        return True
    if hass.states.get(legacy_id) is not None:
        _LOGGER.warning(
            "%s is still provided by the %s integration; remove the YAML "
            "package and restart before migrating",
            legacy_id,
            existing.platform,
        )
        return False
    _LOGGER.debug(
        "Releasing %s from the %s integration so it can be taken over",
        legacy_id,
        existing.platform,
    )
    registry.async_remove(legacy_id)
    return True
