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

from .const import DOMAIN
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


def legacy_entity_id(
    platform: str, description: SungrowEntityDescription
) -> str | None:
    """Return the entity_id the YAML package gave this entity, if it had one.

    Derived the same way Home Assistant derived it in the first place — by
    slugifying the name — rather than from a table, so the two cannot drift.
    """
    if description.legacy_name is None:
        return None
    return f"{platform}.{slugify(description.legacy_name)}"


def legacy_entity_ids() -> frozenset[str]:
    """Return the entity_id each YAML entity had **if it was never renamed**.

    Only the naming tests use this. Identification goes through
    `async_legacy_entities`, which asks the registry rather than assuming.
    """
    return frozenset(
        entity_id
        for platform, description in DESCRIPTIONS
        if (entity_id := legacy_entity_id(platform, description)) is not None
    )


@callback
def async_legacy_entities(hass: HomeAssistant) -> dict[tuple[str, str], str]:
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
            platform, description.legacy_platform, description.legacy_unique_id
        )
        if entity_id is not None:
            found[platform, description.key] = entity_id
    return found


@callback
def async_legacy_ids_known(hass: HomeAssistant) -> set[str]:
    """Return the entity ids the YAML package's own entities hold right now.

    Evidence that it is or was installed.
    """
    return set(async_legacy_entities(hass).values())


@callback
def keys_for(entity_ids: set[str]) -> frozenset[tuple[str, str]]:
    """Return the (platform, key) pairs whose un-renamed legacy id is here."""
    return frozenset(
        (platform, description.key)
        for platform, description in DESCRIPTIONS
        if legacy_entity_id(platform, description) in entity_ids
    )


async def async_legacy_ids_with_history(hass: HomeAssistant) -> set[str]:
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

    wanted = legacy_entity_ids()

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
def async_legacy_ids_live(hass: HomeAssistant) -> set[str]:
    """Return the legacy ids that still have a state.

    A live entity holds its id against the registry, so adopting one would
    produce `sensor.total_dc_power_2` instead — silently. This is the check
    that turns that into an error the user can act on: remove the YAML
    package and restart.
    """
    return {
        entity_id
        for entity_id in async_legacy_ids_known(hass)
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
    """
    registry = er.async_get(hass)
    claimed: list[str] = []
    legacy = async_legacy_entities(hass)

    for platform, description in DESCRIPTIONS:
        legacy_id = legacy.get((platform, description.key))
        if legacy_id is None and (platform, description.key) in with_history:
            # No registry entry left, but the recorder still has the rows.
            legacy_id = legacy_entity_id(platform, description)
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
