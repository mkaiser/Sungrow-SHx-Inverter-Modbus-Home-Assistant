"""The migration testbed's seed refuses where it would break the instance.

`scripts/dev/seed_migration_testbed.py` writes a dev instance's registry and
recorder directly.

Nothing here touches a real config directory: the script's paths are pointed
at a temporary one, with the recorder tables it writes created by hand.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parent.parent

#: The columns the script writes, in the shape Home Assistant's recorder has
#: them, unique constraints included.
SCHEMA = """
CREATE TABLE states_meta (metadata_id INTEGER PRIMARY KEY, entity_id TEXT UNIQUE);
CREATE TABLE state_attributes (
    attributes_id INTEGER PRIMARY KEY, hash INTEGER, shared_attrs TEXT);
CREATE TABLE states (
    state_id INTEGER PRIMARY KEY, metadata_id INTEGER, state TEXT,
    last_updated_ts REAL, last_changed_ts REAL, attributes_id INTEGER);
CREATE TABLE statistics_meta (
    id INTEGER PRIMARY KEY, statistic_id TEXT UNIQUE, source TEXT,
    unit_of_measurement TEXT, unit_class TEXT, has_mean INTEGER,
    has_sum INTEGER, mean_type INTEGER, name TEXT);
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY, metadata_id INTEGER, created_ts REAL, start_ts REAL,
    state REAL, sum REAL, mean REAL, min REAL, max REAL,
    UNIQUE (metadata_id, start_ts));
"""


@pytest.fixture
def seed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the script with its paths in a scratch config directory."""
    spec = importlib.util.spec_from_file_location(
        "seed_migration_testbed", REPO / "scripts" / "dev" / "seed_migration_testbed.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "CONFIG", config)
    monkeypatch.setattr(module, "STORAGE", config / ".storage")
    registry = config / ".storage" / "core.entity_registry"
    monkeypatch.setattr(module, "REGISTRY", registry)
    monkeypatch.setattr(module, "DATABASE", config / "home-assistant_v2.db")
    connection = sqlite3.connect(config / "home-assistant_v2.db")
    connection.executescript(SCHEMA)
    connection.close()
    return module


def _statistics_rows(module: ModuleType) -> int:
    connection = sqlite3.connect(module.DATABASE)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM statistics").fetchone()[0])
    finally:
        connection.close()


def test_a_seed_writes_the_registry_and_the_recorder(seed: ModuleType) -> None:
    assert seed.main([]) == 0
    assert _statistics_rows(seed) == len(seed.SEEDED) * seed.DAYS * 24
    entities = json.loads(seed.REGISTRY.read_text(encoding="utf-8"))["data"]["entities"]
    assert {entity["platform"] for entity in entities} <= seed.YAML_PLATFORMS


def test_a_second_seed_is_refused_rather_than_stopped_half_way(
    seed: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    assert seed.main([]) == 0
    rows = _statistics_rows(seed)

    assert seed.main([]) == 1
    assert "--reset" in capsys.readouterr().err
    assert _statistics_rows(seed) == rows


def test_a_reset_makes_room_for_a_new_seed(seed: ModuleType) -> None:
    assert seed.main([]) == 0
    assert seed.main(["--reset"]) == 0
    assert _statistics_rows(seed) == 0
    assert seed.main([]) == 0


def test_nothing_is_written_while_home_assistant_runs(
    seed: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    # This test's own process stands in for a live Home Assistant.
    (seed.CONFIG / ".ha_run.lock").write_text(json.dumps({"pid": os.getpid()}))

    assert seed.main([]) == 1
    assert seed.main(["--reset"]) == 1
    assert "Stop it first" in capsys.readouterr().err
    assert not seed.REGISTRY.exists()
    assert _statistics_rows(seed) == 0


def test_a_lock_left_behind_by_a_stopped_instance_does_not_block(
    seed: ModuleType,
) -> None:
    # Home Assistant leaves the file on exit; a pid nothing runs as is stale.
    # 2**22 is above Linux's default pid_max, so no process has it.
    (seed.CONFIG / ".ha_run.lock").write_text(json.dumps({"pid": 2**22 + 1}))

    assert seed.main([]) == 0
