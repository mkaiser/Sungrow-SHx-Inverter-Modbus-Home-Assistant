"""An entry stored at minor version 1 comes up under minor version 2's names.

What matters most is the snapshot of an unfinished capability test: it is how
the owner's settings get put back, so the migration must carry it to the key
this version reads and must not lose it on the way.
"""

from __future__ import annotations

from typing import Any

from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.capability_test import async_leftover
from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_RESTART,
    CONF_DIAGNOSIS_COMMENT,
    CONF_DIAGNOSIS_DUMP,
    CONF_PERMISSIONS,
    DOMAIN,
    PERMISSION_CAPABILITY_TEST,
)
from custom_components.sungrow_modbus.entry_migration import (
    MINOR_VERSION,
    OLD_ISSUE_PREFIX,
    OLD_STORE_KEY,
    async_migrate_entry,
    migrated_options,
    new_unique_id,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from .conftest import SERIAL

LEFTOVER = {
    "taken_at": 1.0,
    "values": {"battery_min_soc": 10.0},
    "raw": {"battery_min_soc": 100},
    "bounds": {},
    "unreadable": {},
    "battery_ceiling": 5000,
    "stopped_at": None,
}


def _entry(options: dict[str, Any]) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        unique_id=SERIAL,
        data={},
        options=options,
    )


def test_old_option_and_permission_keys_take_their_new_names() -> None:
    migrated = migrated_options(
        {
            "survey_register_dump": False,
            "survey_comment": "garage",
            "control_test_restart": False,
            CONF_PERMISSIONS: {"control_test": "users", "start_stop": "admins"},
            "reporter": "martin",
        }
    )
    assert migrated == {
        CONF_DIAGNOSIS_DUMP: False,
        CONF_DIAGNOSIS_COMMENT: "garage",
        CONF_CAPABILITY_TEST_RESTART: False,
        CONF_PERMISSIONS: {PERMISSION_CAPABILITY_TEST: "users", "start_stop": "admins"},
        "reporter": "martin",
    }


def test_a_value_already_under_the_new_name_wins() -> None:
    migrated = migrated_options(
        {"survey_comment": "old", CONF_DIAGNOSIS_COMMENT: "new"}
    )
    assert migrated == {CONF_DIAGNOSIS_COMMENT: "new"}


def test_only_the_diagnosis_entities_unique_ids_move() -> None:
    assert new_unique_id(f"{SERIAL}_run_survey") == f"{SERIAL}_run_diagnosis"
    assert new_unique_id(f"{SERIAL}_run_control_test") == (
        f"{SERIAL}_run_capability_test"
    )
    assert new_unique_id(f"{SERIAL}_survey_step") == f"{SERIAL}_diagnosis_step"
    assert new_unique_id(f"{SERIAL}_battery_min_soc") is None


async def test_an_old_entry_migrates_and_keeps_its_snapshot_and_entity_ids(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    entry = _entry({"survey_register_dump": False})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    button = registry.async_get_or_create(
        "button", DOMAIN, f"{SERIAL}_run_survey", config_entry=entry
    )
    old_key = f"{OLD_STORE_KEY}.{entry.entry_id}"
    hass_storage[old_key] = {
        "version": 1,
        "minor_version": 1,
        "key": old_key,
        "data": LEFTOVER,
    }
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{OLD_ISSUE_PREFIX}_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="capability_test_unfinished",
    )

    assert await async_migrate_entry(hass, entry) is True

    assert entry.minor_version == MINOR_VERSION
    assert entry.options == {CONF_DIAGNOSIS_DUMP: False}
    moved = registry.async_get(button.entity_id)
    assert moved is not None
    assert moved.unique_id == f"{SERIAL}_run_diagnosis"
    snapshot = await async_leftover(hass, entry)
    assert snapshot is not None
    assert snapshot.values == {"battery_min_soc": 10.0}
    assert old_key not in hass_storage
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, f"{OLD_ISSUE_PREFIX}_{entry.entry_id}"
        )
        is None
    )


async def test_a_snapshot_already_at_the_new_key_is_kept(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """The new key is what this version wrote; an old one never overwrites it."""
    entry = _entry({})
    entry.add_to_hass(hass)
    newer = {**LEFTOVER, "values": {"battery_min_soc": 20.0}}
    old_key = f"{OLD_STORE_KEY}.{entry.entry_id}"
    new_key = f"{DOMAIN}.capability_test.{entry.entry_id}"
    hass_storage[old_key] = {
        "version": 1,
        "minor_version": 1,
        "key": old_key,
        "data": LEFTOVER,
    }
    hass_storage[new_key] = {
        "version": 1,
        "minor_version": 1,
        "key": new_key,
        "data": newer,
    }

    assert await async_migrate_entry(hass, entry) is True

    snapshot = await async_leftover(hass, entry)
    assert snapshot is not None
    assert snapshot.values == {"battery_min_soc": 20.0}
