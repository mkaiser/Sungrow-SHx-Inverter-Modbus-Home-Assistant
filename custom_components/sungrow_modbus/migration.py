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

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from sungrow_modbus import Capability

from .const import DOMAIN
from .derived_descriptions import DERIVED_BINARY_SENSORS, DERIVED_SENSORS
from .entity import SungrowEntityDescription
from .sensor_descriptions import SENSOR_DESCRIPTIONS

_LOGGER = logging.getLogger(__name__)

#: Every entity the integration can create, with the platform it belongs to.
DESCRIPTIONS: tuple[tuple[str, SungrowEntityDescription], ...] = (
    *((Platform.SENSOR.value, d) for d in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)),
    *((Platform.BINARY_SENSOR.value, d) for d in DERIVED_BINARY_SENSORS),
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
    """Return every entity_id this integration could take over."""
    return frozenset(
        entity_id
        for platform, description in DESCRIPTIONS
        if (entity_id := legacy_entity_id(platform, description)) is not None
    )


@callback
def async_legacy_ids_known(hass: HomeAssistant) -> set[str]:
    """Return the legacy ids the entity registry knows about.

    Evidence that the YAML package is or was installed. Entries this
    integration itself owns are excluded, so a reload does not read as a
    second YAML package.
    """
    registry = er.async_get(hass)
    known: set[str] = set()
    for entity_id in legacy_entity_ids():
        entry = registry.async_get(entity_id)
        if entry is not None and entry.platform != DOMAIN:
            known.add(entity_id)
    return known


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

    for platform, description in DESCRIPTIONS:
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
