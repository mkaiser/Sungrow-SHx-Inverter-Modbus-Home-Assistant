"""Bring a config entry stored by an older version up to this one's names.

Minor version 2 names the diagnosis and the capability test by those names:
the options that configure them, the permission for the capability test,
the diagnosis entities' unique ids and the store holding an unfinished
capability test's snapshot. Nothing here reads or writes the inverter.

Minor version 3 drops what an inverter entry no longer has: the
`wallbox_host` option, which read a wallbox's own address from inside the
inverter's entry, and the wallbox test's leave and cap, since only a wallbox
entry of its own writes to a wallbox. A wallbox with an address of its own
is added through the search instead; no history is carried over (the YAML
package never had a wallbox). The sub-device the option made goes with it.

The snapshot is the part that must not be lost: it is what puts the owner's
settings back after a capability test that did not finish. It is copied to
its new key and only then removed from the old one, so an interruption at
any point leaves it in at least one place, and the new key is read first.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.storage import Store

from .capability_test import STORE_KEY, STORE_VERSION
from .const import (
    CONF_CAPABILITY_TEST_CHARGE_WINDOW,
    CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
    CONF_CAPABILITY_TEST_EXPORT,
    CONF_CAPABILITY_TEST_IMPORT_LIMIT,
    CONF_CAPABILITY_TEST_PV_CUT,
    CONF_CAPABILITY_TEST_RESTART,
    CONF_DIAGNOSIS_BATTERY,
    CONF_DIAGNOSIS_COMMENT,
    CONF_DIAGNOSIS_DUMP,
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL,
    CONF_DIAGNOSIS_POLLERS,
    CONF_DIAGNOSIS_PROXY,
    CONF_DIAGNOSIS_TRANSPORT,
    CONF_KIND,
    CONF_PERMISSIONS,
    DOMAIN,
    KIND_WALLBOX,
    PERMISSION_CAPABILITY_TEST,
)
from .repairs import ISSUE_PREFIX

_LOGGER = logging.getLogger(__name__)

#: The minor version this module brings an entry to.
MINOR_VERSION = 3

#: Options minor version 3 removes from an inverter entry.
REMOVED_INVERTER_OPTIONS = (
    "wallbox_host",
    "capability_test_wallbox",
    "wallbox_max_amps",
)

#: Option keys as minor version 1 stored them, to their names now.
RENAMED_OPTIONS: dict[str, str] = {
    "survey_comment": CONF_DIAGNOSIS_COMMENT,
    "survey_battery": CONF_DIAGNOSIS_BATTERY,
    "survey_transport": CONF_DIAGNOSIS_TRANSPORT,
    "survey_proxy": CONF_DIAGNOSIS_PROXY,
    "survey_pollers": CONF_DIAGNOSIS_POLLERS,
    "survey_other_inverter": CONF_DIAGNOSIS_OTHER_INVERTER,
    "survey_other_inverter_detail": CONF_DIAGNOSIS_OTHER_INVERTER_DETAIL,
    "survey_register_dump": CONF_DIAGNOSIS_DUMP,
    "control_test_restart": CONF_CAPABILITY_TEST_RESTART,
    "control_test_export_limit": CONF_CAPABILITY_TEST_EXPORT,
    "control_test_pv_cut": CONF_CAPABILITY_TEST_PV_CUT,
    "control_test_charge_window": CONF_CAPABILITY_TEST_CHARGE_WINDOW,
    "control_test_discharge_window": CONF_CAPABILITY_TEST_DISCHARGE_WINDOW,
    "control_test_import_limit": CONF_CAPABILITY_TEST_IMPORT_LIMIT,
}

#: Permission keys inside `CONF_PERMISSIONS`, likewise.
RENAMED_PERMISSIONS: dict[str, str] = {"control_test": PERMISSION_CAPABILITY_TEST}

#: The diagnosis entities' keys, the end of their unique ids (`{serial}_{key}`).
RENAMED_ENTITY_KEYS: dict[str, str] = {
    "run_survey": "run_diagnosis",
    "run_control_test": "run_capability_test",
    "survey_progress": "diagnosis_progress",
    "survey_step": "diagnosis_step",
    "survey_finished": "diagnosis_finished",
}

#: Where minor version 1 kept an unfinished run's snapshot, and its repair.
OLD_STORE_KEY = f"{DOMAIN}.control_test"
OLD_ISSUE_PREFIX = "control_test_unfinished"


def _renamed(values: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    """Return `values` with every old key under its new name.

    A value already under the new name wins: it was written by this version.
    """
    out = {names.get(key, key): value for key, value in values.items()}
    for old, new in names.items():
        if old in values and new in values:
            out[new] = values[new]
    return out


def migrated_options(options: dict[str, Any]) -> dict[str, Any]:
    """Return an entry's options with the keys minor version 2 names."""
    out = _renamed(options, RENAMED_OPTIONS)
    permissions = out.get(CONF_PERMISSIONS)
    if isinstance(permissions, dict):
        out[CONF_PERMISSIONS] = _renamed(permissions, RENAMED_PERMISSIONS)
    return out


def new_unique_id(unique_id: str) -> str | None:
    """Return a diagnosis entity's unique id under its new key, None if unchanged."""
    for old, new in RENAMED_ENTITY_KEYS.items():
        if unique_id.endswith(f"_{old}"):
            return unique_id.removesuffix(old) + new
    return None


async def _async_move_snapshot(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Move an unfinished run's snapshot to the store this version reads."""
    old: Store[dict[str, Any]] = Store(
        hass, STORE_VERSION, f"{OLD_STORE_KEY}.{entry.entry_id}"
    )
    new: Store[dict[str, Any]] = Store(
        hass, STORE_VERSION, f"{STORE_KEY}.{entry.entry_id}"
    )
    data = await old.async_load()
    if not data:
        return
    if not await new.async_load():
        await new.async_save(data)
    await old.async_remove()
    _LOGGER.warning(
        "%s: moved an unfinished capability test's snapshot to its new store; "
        "its repair is raised again at setup",
        entry.title,
    )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate an entry stored at an older minor version to this one."""
    if entry.version > 1:
        return False
    if entry.minor_version >= MINOR_VERSION:
        return True
    if entry.minor_version < 2:
        await _async_migrate_names(hass, entry)
    if entry.minor_version < 3:
        _async_drop_wallbox_options(hass, entry)
    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.debug("%s: migrated to minor version %d", entry.title, MINOR_VERSION)
    return True


@callback
def _async_drop_wallbox_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove what minor version 3 takes from an inverter entry."""
    if entry.data.get(CONF_KIND) == KIND_WALLBOX:
        return
    had_host = bool(entry.options.get("wallbox_host"))
    options = {
        key: value
        for key, value in entry.options.items()
        if key not in REMOVED_INVERTER_OPTIONS
    }
    hass.config_entries.async_update_entry(entry, options=options)
    if not had_host or entry.unique_id is None:
        return
    # The wallbox it read at its own address was a sub-device keyed on the
    # inverter's serial. Removed rather than left unavailable; the wallbox
    # comes back as an entry of its own once the search adds it.
    registry = dr.async_get(hass)
    device = registry.async_get_device_by_identifier(
        (DOMAIN, f"{entry.unique_id}-wallbox"), entry.entry_id
    )
    if device is not None:
        registry.async_remove_device(device.id)
    _LOGGER.warning(
        "%s: the wallbox address option is gone; add the wallbox through "
        "Add integration > Search my network, as an entry of its own",
        entry.title,
    )


async def _async_migrate_names(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Bring minor version 1's names to minor version 2's."""
    await _async_move_snapshot(hass, entry)
    ir.async_delete_issue(hass, DOMAIN, f"{OLD_ISSUE_PREFIX}_{entry.entry_id}")
    # The new issue id is raised from the moved snapshot at setup.
    assert ISSUE_PREFIX != OLD_ISSUE_PREFIX

    @callback
    def _unique_id(entity: er.RegistryEntry) -> dict[str, Any] | None:
        renamed = new_unique_id(entity.unique_id)
        return {"new_unique_id": renamed} if renamed else None

    await er.async_migrate_entries(hass, entry.entry_id, _unique_id)
    hass.config_entries.async_update_entry(
        entry,
        data=migrated_options(dict(entry.data)),
        options=migrated_options(dict(entry.options)),
        minor_version=2,
    )
