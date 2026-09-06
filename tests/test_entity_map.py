"""The generated map of what the YAML package produces, and its invariants.

`doc/legacy_entity_map.json` is what the port is built and checked against, so
it has to stay true to `modbus_sungrow.yaml`. These tests fail if it goes
stale, and if any of the properties a migration depends on stop holding.
"""

from __future__ import annotations

import json
import sys

import pytest

sys.path.insert(0, "scripts")

from generate_entity_map import OUTPUT, build

#: Entities whose ids appear in dashboards, the Energy dashboard and years of
#: history. If one of these moves, somebody's data is about to be orphaned.
CANARIES = {
    "sensor.total_dc_power": ("W", "measurement"),
    "sensor.daily_pv_generation": ("kWh", "total_increasing"),
    "sensor.total_pv_generation": ("kWh", "total"),
    "sensor.battery_level": ("%", "measurement"),
}


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def test_the_committed_map_is_current() -> None:
    expected = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    assert OUTPUT.read_text(encoding="utf-8") == expected, (
        "doc/legacy_entity_map.json is stale — run scripts/generate_entity_map.py"
    )


def test_no_two_entities_want_the_same_entity_id(committed: dict) -> None:
    # A collision means Home Assistant appended `_2` to whichever registered
    # second, so the id recorded here is wrong for one of them — and adopting
    # it would attach a replacement to another entity's history.
    assert committed["summary"]["entity_id_collisions"] == {}


def test_every_entity_has_a_unique_id(committed: dict) -> None:
    # Without one there is no registry entry, and nothing to migrate through.
    assert committed["summary"]["without_unique_id"] == []


def test_every_statistics_entity_has_a_unit(committed: dict) -> None:
    # Long-term statistics pin the unit. An entity carrying a state class with
    # no unit cannot be checked against its replacement for the unit-class
    # trap, which is the failure that freezes statistics flat.
    assert committed["summary"]["state_class_without_unit"] == []


@pytest.mark.parametrize(("entity_id", "expected"), sorted(CANARIES.items()))
def test_canary_entities_keep_their_id_unit_and_state_class(
    committed: dict, entity_id: str, expected: tuple[str, str]
) -> None:
    unit, state_class = expected
    matches = [e for e in committed["entities"] if e["entity_id"] == entity_id]
    assert matches, f"{entity_id} is no longer produced by the YAML package"
    entry = matches[0]
    assert entry["unit_of_measurement"] == unit
    assert entry["state_class"] == state_class
