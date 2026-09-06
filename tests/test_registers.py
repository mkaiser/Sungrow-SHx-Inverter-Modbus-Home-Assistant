"""The generated register map, checked against the YAML it came from.

`registers.py` is generated, so the risk is not that somebody mistypes an
address — it is that the generator quietly drops or mistranslates something
and nobody notices, because a wrong scale produces a plausible number rather
than an error. These tests compare every generated field against the entity
map entry it was derived from.
"""

from __future__ import annotations

import json
from pathlib import Path

from modbus_connection.model import Component
import pytest

from sungrow_modbus import registers

ENTITY_MAP = Path(__file__).resolve().parent.parent / "doc" / "legacy_entity_map.json"


def _expected() -> dict[str, dict]:
    """Return the modbus read entities, keyed by the field name they become."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in entities
        if e["layer"] == "modbus"
        and e.get("address") is not None
        and e["domain"] != "switch"
    }


def _generated() -> dict[str, tuple[type[Component], object]]:
    """Return every generated field, keyed by its name."""
    found: dict[str, tuple[type[Component], object]] = {}
    for value in vars(registers).values():
        if not (
            isinstance(value, type)
            and issubclass(value, Component)
            and value is not Component
        ):
            continue
        for name, field in vars(value).items():
            if name.startswith("_") or name in {"register_space", "declared_fields"}:
                continue
            found[name] = (value, field)
    return found


EXPECTED = _expected()
GENERATED = _generated()


def test_every_read_register_was_ported() -> None:
    assert set(GENERATED) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_field_matches_the_yaml(name: str) -> None:
    entity = EXPECTED[name]
    component, field = GENERATED[name]

    assert field.address == entity["address"], "address"
    assert component.register_space == entity["input_type"], "register space"

    if entity.get("data_type") == "string":
        assert field.count == entity.get("count", 1), "string length"
        return

    # A wrong scale is the dangerous one: it yields a plausible number.
    assert field.scale == float(entity.get("scale") or 1), "scale"
    # The library normalises a single sentinel into a frozenset.
    expected_nan = entity.get("nan_value")
    if expected_nan is None:
        assert not field.nan, "unavailable sentinel"
    else:
        assert field.nan == frozenset({expected_nan}), "unavailable sentinel"
    assert (field.unit or None) == entity.get("unit_of_measurement"), "unit"

    if entity.get("data_type") in {"int16", "int32"}:
        assert field.signed is True, "signedness"
    elif entity.get("data_type") in {"uint16", "uint32"}:
        assert field.signed is False, "signedness"

    # Sungrow sends 32-bit values low word first throughout.
    if entity.get("swap") == "word":
        assert field.word_order == "little", "word order"


def test_the_tiers_match_the_yaml_scan_intervals() -> None:
    assert set(registers.TIERS) == {5, 10, 60, 600}
    for tier, attributes in registers.TIERS.items():
        for attribute in attributes:
            component = registers.COMPONENTS[attribute]
            for name in vars(component):
                if name in EXPECTED:
                    assert EXPECTED[name]["scan_interval"] == tier


def test_every_component_is_reachable_by_the_name_entities_use() -> None:
    # Entity descriptions name a component by string, so the two mappings have
    # to agree or an entity silently finds nothing.
    named = {a for attributes in registers.TIERS.values() for a in attributes}
    assert named == set(registers.COMPONENTS)
