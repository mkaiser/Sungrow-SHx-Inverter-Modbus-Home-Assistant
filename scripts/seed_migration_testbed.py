#!/usr/bin/env python3
"""Make the dev instance look like a house that has run the YAML package for years.

The migration is the one feature that cannot be judged from a unit test alone.
Whether the setup dialog explains the choice well enough to make it, whether
the history graph really is continuous afterwards, whether the Energy
dashboard keeps its numbers — those are things you have to look at.

So this fabricates the starting state: the entity registry entries
`modbus_sungrow.yaml` leaves behind, and months of recorded readings and
long-term statistics under the entity ids it used. Home Assistant must be
**stopped** while it runs, because it writes the registry and the recorder
database directly.

    scripts/develop                                  # once, to create config/
    # stop it
    python scripts/seed_migration_testbed.py         # seed
    scripts/simulate &                               # an inverter to talk to
    scripts/develop                                  # and now migrate in the UI

By default the entities come from `doc/legacy_entity_map.json`, which is
generated from the YAML package and carries no personal data. `--from` reads a
registry snapshot exported from a real instance instead, which is more faithful
— it has the user's own `_2` suffixes and disabled entities — but such a file
belongs in `.testdata/`, never in the repository.

    python scripts/seed_migration_testbed.py --from .testdata/live_entity_registry.json

`--reset` throws the seeded state away again, so the same instance can be used
to try the other answer.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import sqlite3
import sys
import uuid

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config"
STORAGE = CONFIG / ".storage"
REGISTRY = STORAGE / "core.entity_registry"
DATABASE = CONFIG / "home-assistant_v2.db"
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"

#: Platforms whose entities the YAML package owns. `homeassistant` entries in
#: a real snapshot are the user's own helpers and are left alone.
YAML_PLATFORMS = {"modbus", "template", "filter"}

#: How much history to fabricate. Long enough that the Energy dashboard has
#: something to show and a graph is worth looking at; short enough to seed in
#: a couple of seconds.
DAYS = 30

#: The sensors given real history, chosen because they are what a reviewer
#: actually looks at: a cumulative meter the Energy dashboard reads, a live
#: power, and a percentage. The fourth field is the statistics **unit class**,
#: and it has to be right — long-term statistics pin it, and a mismatch is the
#: trap that freezes a series flat while raw history keeps filling.
SEEDED: dict[str, tuple[str, str, str, str | None]] = {
    "sensor.total_pv_generation": ("kWh", "energy", "total_increasing", "energy"),
    "sensor.daily_pv_generation": ("kWh", "energy", "total_increasing", "energy"),
    "sensor.total_active_power": ("W", "power", "measurement", "power"),
    "sensor.battery_level": ("%", "battery", "measurement", None),
}


def _entities(source: Path | None) -> list[dict]:
    """Return the registry entries to seed, from a snapshot or the entity map."""
    if source is not None:
        snapshot = json.loads(source.read_text(encoding="utf-8"))
        entries = (
            snapshot["data"]["entities"] if isinstance(snapshot, dict) else snapshot
        )
        return [e for e in entries if e.get("platform") in YAML_PLATFORMS]

    mapped = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return [
        {
            "entity_id": entity["entity_id"],
            "platform": "modbus" if entity["layer"] == "modbus" else entity["layer"],
            "unique_id": entity["unique_id"],
            "original_name": entity["name"],
            "unit_of_measurement": entity.get("unit_of_measurement"),
            "device_class": entity.get("device_class"),
        }
        for entity in mapped
        if entity.get("unique_id")
    ]


def _registry_entry(entity: dict) -> dict:
    """Return one entity registry row, shaped as Home Assistant stores it.

    Deliberately with `config_entry_id: null` and `device_id: null`, because
    that is what a YAML platform entity looks like — and it is exactly why
    removing the package leaves the row behind to block the entity_id.
    """
    return {
        # `aliases_v2` is the current shape; `aliases` is kept because
        # `_async_load` still reads it as `compat_aliases`. `COMPUTED_NAME` is
        # spelled `None` on disk, and every entry carries it.
        "aliases": [],
        "aliases_v2": [None],
        "area_id": None,
        "capabilities": None,
        "categories": {},
        "config_entry_id": None,
        "config_subentry_id": None,
        "created_at": "1970-01-01T00:00:00+00:00",
        "device_class": None,
        "device_id": None,
        "disabled_by": None,
        "entity_category": None,
        "entity_id": entity["entity_id"],
        "hidden_by": None,
        "icon": None,
        "id": uuid.uuid4().hex,
        "has_entity_name": False,
        "labels": [],
        "modified_at": "1970-01-01T00:00:00+00:00",
        "name": None,
        # What a device-scoped id would be built from. A YAML platform entity
        # has no device, so it is simply the name.
        "object_id_base": entity.get("original_name"),
        "options": {},
        "original_device_class": entity.get("device_class"),
        "original_icon": None,
        "original_name": entity.get("original_name"),
        "platform": entity.get("platform", "modbus"),
        "previous_unique_id": None,
        "suggested_object_id": None,
        "supported_features": 0,
        "translation_key": None,
        "unique_id": entity["unique_id"],
        "unit_of_measurement": entity.get("unit_of_measurement"),
    }


def _write_registry(entries: list[dict]) -> int:
    """Merge the YAML package's entries into the dev instance's registry."""
    STORAGE.mkdir(parents=True, exist_ok=True)
    if REGISTRY.exists():
        document = json.loads(REGISTRY.read_text(encoding="utf-8"))
    else:
        document = {
            "version": 1,
            "minor_version": 23,
            "key": "core.entity_registry",
            "data": {"entities": [], "deleted_entities": []},
        }

    existing = {e["entity_id"] for e in document["data"]["entities"]}
    added = 0
    for entity in entries:
        if entity["entity_id"] in existing:
            continue
        document["data"]["entities"].append(_registry_entry(entity))
        added += 1

    REGISTRY.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return added


def _reading(entity_id: str, step: int, steps: int) -> float:
    """Return a plausible value, so the graphs look like a house and not a saw."""
    day = step / steps * DAYS
    # A daily sine, positive only, as a PV system produces.
    sun = max(0.0, math.sin((day % 1.0) * math.pi * 2 - math.pi / 2))
    if entity_id == "sensor.total_pv_generation":
        return round(12000.0 + day * 25.0, 1)
    if entity_id == "sensor.daily_pv_generation":
        return round(sun * 28.0, 1)
    if entity_id == "sensor.total_active_power":
        return round(sun * 7200.0, 0)
    return round(20.0 + sun * 70.0, 1)


def _seed_history(connection: sqlite3.Connection) -> int:
    """Write raw states for the seeded sensors, hourly, over DAYS days."""
    cursor = connection.cursor()
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=DAYS)
    steps = DAYS * 24
    written = 0

    for entity_id, (unit, device_class, state_class, _unit_class) in SEEDED.items():
        cursor.execute(
            "INSERT INTO states_meta (entity_id) VALUES (?) "
            "ON CONFLICT(entity_id) DO NOTHING",
            (entity_id,),
        )
        cursor.execute(
            "SELECT metadata_id FROM states_meta WHERE entity_id = ?", (entity_id,)
        )
        metadata_id = cursor.fetchone()[0]

        attributes = json.dumps(
            {
                "unit_of_measurement": unit,
                "device_class": device_class,
                "state_class": state_class,
                "friendly_name": entity_id.split(".", 1)[1]
                .replace("_", " ")
                .capitalize(),
            },
            sort_keys=True,
        )
        cursor.execute(
            "INSERT INTO state_attributes (hash, shared_attrs) VALUES (?, ?)",
            (hash(attributes) & 0xFFFFFFFF, attributes),
        )
        attributes_id = cursor.lastrowid

        rows = []
        for step in range(steps):
            when = (start + timedelta(hours=step)).timestamp()
            rows.append(
                (
                    metadata_id,
                    str(_reading(entity_id, step, steps)),
                    when,
                    when,
                    attributes_id,
                )
            )
        cursor.executemany(
            "INSERT INTO states "
            "(metadata_id, state, last_updated_ts, last_changed_ts, attributes_id) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        written += len(rows)

    connection.commit()
    return written


def _seed_statistics(connection: sqlite3.Connection) -> int:
    """Write hourly long-term statistics, which is what the Energy dashboard reads."""
    cursor = connection.cursor()
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=DAYS)
    steps = DAYS * 24
    written = 0

    for entity_id, (unit, _device_class, state_class, unit_class) in SEEDED.items():
        has_sum = state_class == "total_increasing"
        # mean_type: 0 NONE, 1 ARITHMETIC. A sum-bearing meter has no mean.
        cursor.execute(
            "INSERT INTO statistics_meta "
            "(statistic_id, source, unit_of_measurement, unit_class, "
            "has_mean, has_sum, mean_type, name) "
            "VALUES (?, 'recorder', ?, ?, ?, ?, ?, NULL) "
            "ON CONFLICT(statistic_id) DO NOTHING",
            (
                entity_id,
                unit,
                unit_class,
                0 if has_sum else 1,
                1 if has_sum else 0,
                0 if has_sum else 1,
            ),
        )
        cursor.execute(
            "SELECT id FROM statistics_meta WHERE statistic_id = ?", (entity_id,)
        )
        metadata_id = cursor.fetchone()[0]

        rows = []
        running = 0.0
        for step in range(steps):
            when = (start + timedelta(hours=step)).timestamp()
            value = _reading(entity_id, step, steps)
            if has_sum:
                running += max(value, 0.0) / steps
                rows.append((metadata_id, when, when, value, running, None, None, None))
            else:
                rows.append((metadata_id, when, when, None, None, value, value, value))
        cursor.executemany(
            "INSERT INTO statistics "
            "(metadata_id, created_ts, start_ts, state, sum, mean, min, max) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        written += len(rows)

    connection.commit()
    return written


def _reset() -> None:
    """Remove the seeded registry entries and recorded rows."""
    if REGISTRY.exists():
        document = json.loads(REGISTRY.read_text(encoding="utf-8"))
        before = len(document["data"]["entities"])
        document["data"]["entities"] = [
            entity
            for entity in document["data"]["entities"]
            if entity.get("platform") not in YAML_PLATFORMS
        ]
        REGISTRY.write_text(json.dumps(document, indent=2), encoding="utf-8")
        print(f"Removed {before - len(document['data']['entities'])} registry entries")

    if DATABASE.exists():
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()
        for entity_id in SEEDED:
            cursor.execute(
                "DELETE FROM states WHERE metadata_id IN "
                "(SELECT metadata_id FROM states_meta WHERE entity_id = ?)",
                (entity_id,),
            )
            cursor.execute("DELETE FROM states_meta WHERE entity_id = ?", (entity_id,))
            cursor.execute(
                "DELETE FROM statistics WHERE metadata_id IN "
                "(SELECT id FROM statistics_meta WHERE statistic_id = ?)",
                (entity_id,),
            )
            cursor.execute(
                "DELETE FROM statistics_meta WHERE statistic_id = ?", (entity_id,)
            )
        connection.commit()
        connection.close()
        print(f"Removed recorded rows for {len(SEEDED)} sensors")


def main() -> int:
    """Seed the testbed, or reset it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from",
        dest="source",
        type=Path,
        help="registry snapshot from a real instance, instead of the entity map",
    )
    parser.add_argument("--reset", action="store_true", help="undo a previous seed")
    args = parser.parse_args()

    if not CONFIG.exists():
        print(
            "config/ does not exist. Run scripts/develop once first.", file=sys.stderr
        )
        return 1
    if not DATABASE.exists():
        print(
            f"{DATABASE.relative_to(REPO)} does not exist. Run scripts/develop once "
            "and let it start, then stop it.",
            file=sys.stderr,
        )
        return 1

    if args.reset:
        _reset()
        return 0

    entries = _entities(args.source)
    added = _write_registry(entries)
    connection = sqlite3.connect(DATABASE)
    states = _seed_history(connection)
    statistics = _seed_statistics(connection)
    connection.close()

    print(f"Registry:   {added} entities added ({len(entries)} in the source)")
    print(f"History:    {states} states over {DAYS} days")
    print(f"Statistics: {statistics} hourly rows")
    print()
    print("Now start the simulator and Home Assistant:")
    print("  scripts/simulate &")
    print("  scripts/develop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
