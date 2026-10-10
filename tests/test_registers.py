"""The register map, checked against the YAML package it replaces.

`registers.py` is edited by hand, so the risk is the ordinary one: somebody
mistypes an address or a scale, and nobody notices, because a wrong scale
produces a plausible number rather than an error. These tests compare every
field against the entity map entry it was ported from.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from modbus_connection.model import Component
import pytest

from sungrow_modbus import registers
from sungrow_modbus.layout import COUNTS, ISOLATE

ENTITY_MAP = Path(__file__).resolve().parent.parent / "doc" / "legacy_entity_map.json"


def _expected() -> dict[str, dict]:
    """Return the modbus read entities, keyed by the field name they become."""
    entities = json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    return {
        e["entity_id"].split(".", 1)[1]: e
        for e in entities
        if e["layer"] in {"modbus", "specification"}
        and e.get("address") is not None
        and e["domain"] != "switch"
    }


#: Kept empty on purpose. Another device's components do not belong in this
#: module at all -- `registers.py` is generated from the *inverter's* map, and
#: the SBR's components now live in `battery_registers.py` for exactly that
#: reason. This set was how they were excluded while they were still in here,
#: and it stays as the place to name any future exception rather than
#: inventing the mechanism again under pressure.
OTHER_DEVICES: set[str] = set()


def _generated() -> dict[str, tuple[type[Component], object]]:
    """Return every generated field of the *inverter*, keyed by its name."""
    found: dict[str, tuple[type[Component], object]] = {}
    for value in vars(registers).values():
        if not (
            isinstance(value, type)
            and issubclass(value, Component)
            and value is not Component
        ):
            continue
        if value.__name__ in OTHER_DEVICES:
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
        # A length in `layout.COUNTS` overrides the YAML's, and only ever
        # because hardware proved the YAML's does not read. Asserted against
        # the table rather than skipped, so a correction still has to be
        # declared to exist.
        expected = COUNTS.get(name, entity.get("count", 1))
        assert field.count == expected, "string length"
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
    assert set(registers.TIER_COMPONENTS) == {"realtime", "fast", "medium", "slowest"}
    assert registers.DEFAULT_INTERVALS == {
        "realtime": 5,
        "fast": 10,
        "medium": 60,
        "slowest": 600,
    }
    # A tier is named now, so the YAML's scan_interval maps to it through the
    # defaults rather than being the key itself.
    for tier, attributes in registers.TIER_COMPONENTS.items():
        interval = registers.DEFAULT_INTERVALS[tier]
        for attribute in attributes:
            component = registers.COMPONENTS[attribute]
            for name in vars(component):
                if name in EXPECTED:
                    assert EXPECTED[name]["scan_interval"] == interval


def test_every_component_is_reachable_by_the_name_entities_use() -> None:
    # Entity descriptions name a component by string, so the two mappings have
    # to agree or an entity silently finds nothing.
    named = {a for attributes in registers.TIER_COMPONENTS.values() for a in attributes}
    assert named == set(registers.COMPONENTS)


@pytest.mark.parametrize("field", sorted(COUNTS))
def test_a_corrected_length_is_isolated(field: str) -> None:
    """A field whose length was corrected cannot share a read.

    `layout.COUNTS` is right only for a request covering exactly one of these
    fields -- the firmware that needs the correction answers 15 registers
    whatever was asked for. Pool two of them and the request is 31 registers
    long again, which is the bug the correction was for.
    """
    assert field in ISOLATE, f"{field} has a corrected length but is pooled"
    others = [f for f, group in ISOLATE.items() if group == ISOLATE[field]]
    assert others == [field], f"{field} shares a component with {others}"


@pytest.mark.parametrize("group", sorted(set(ISOLATE.values())))
def test_an_isolated_group_is_a_component_of_its_own(group: str) -> None:
    """`layout.ISOLATE` is the record; `registers.py` has to honour it.

    This is what stops a field being moved back into its tier's pooled
    component -- which reads fine on most hardware and empties the whole
    component again on the firmware the entry was measured on.
    """
    assert group in registers.COMPONENTS, f"no component named {group}"
    expected = {f for f, g in ISOLATE.items() if g == group}
    component = registers.COMPONENTS[group]
    actual = {name for name, (owner, _f) in GENERATED.items() if owner is component}
    assert actual == expected


def test_the_scan_plan_matches_the_library() -> None:
    """The artefact that lets the scanner run without the library.

    `scripts/sungrow_survey/` is run by contributors with nothing installed, so it
    cannot import `sungrow_modbus` -- it reads which blocks to fetch and how to
    decode them out of a committed JSON instead. Stale, that file would make
    the scanner measure a plan the integration no longer uses, which is worse
    than not measuring: the numbers would look fine.

    CI checks this too; asserting it here means a local `pytest` catches the
    staleness before a push does.
    """
    sys.path.insert(
        0, str(Path(__file__).resolve().parent.parent / "scripts" / "generate")
    )
    from generate_scan_plan import OUTPUT, render

    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "Run scripts/generate/generate_scan_plan.py and commit the result."
    )
