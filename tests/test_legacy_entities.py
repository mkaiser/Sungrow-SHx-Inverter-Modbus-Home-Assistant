"""The record of what the YAML package produces, and its invariants.

`scripts/generate/tables/legacy_entities.py` holds the entity ids, units and
state classes existing users have, which a migration must keep. These tests
fail if any of those properties stop holding.
"""

from __future__ import annotations

from collections import Counter
import sys

import pytest

sys.path.insert(0, "scripts/generate/tables")

from legacy_entities import ENTITIES

#: The layers that are the YAML package itself, as opposed to what the
#: specification and the diagnoses added.
YAML_LAYERS = frozenset({"modbus", "template", "filter"})

#: Entities whose ids appear in dashboards, the Energy dashboard and years of
#: history. If one of these moves, somebody's data is about to be orphaned.
CANARIES = {
    "sensor.total_dc_power": ("W", "measurement"),
    "sensor.daily_pv_generation": ("kWh", "total_increasing"),
    "sensor.total_pv_generation": ("kWh", "total"),
    "sensor.battery_level": ("%", "measurement"),
}


def test_no_two_entities_want_the_same_entity_id() -> None:
    # A collision means Home Assistant appended `_2` to whichever registered
    # second, so the id recorded here is wrong for one of them — and adopting
    # it would attach a replacement to another entity's history.
    counts = Counter(entity["entity_id"] for entity in ENTITIES)
    assert [entity_id for entity_id, n in counts.items() if n > 1] == []


def test_every_yaml_entity_has_a_unique_id() -> None:
    # Without one there is no registry entry, and nothing to migrate through.
    assert [
        entity["entity_id"]
        for entity in ENTITIES
        if entity["layer"] in YAML_LAYERS and not entity.get("unique_id")
    ] == []


@pytest.mark.parametrize(("entity_id", "expected"), sorted(CANARIES.items()))
def test_canary_entities_keep_their_id_unit_and_state_class(
    entity_id: str, expected: tuple[str, str]
) -> None:
    unit, state_class = expected
    matches = [e for e in ENTITIES if e["entity_id"] == entity_id]
    assert matches, f"{entity_id} is no longer produced by the YAML package"
    entry = matches[0]
    assert entry["unit_of_measurement"] == unit
    assert entry["state_class"] == state_class
