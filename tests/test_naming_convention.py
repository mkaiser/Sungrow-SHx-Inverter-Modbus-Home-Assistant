"""One naming convention, enforced over all 127 entities.

The YAML package's names drifted because nothing checked them: `Battery min
SoC` beside `Battery Min Soc`, fourteen title-cased names among sentence-cased
ones, fifteen beginning with the device's own name. That is not a style
complaint. With `has_entity_name` set, the object id is slugified from the
name, so "Sungrow inverter serial" gives `sensor.sh10rt_sungrow_inverter_serial`
where "Serial number" gives `sensor.sh10rt_serial_number` — the names *are*
the ids, and ids are cheap to change now and impossible to change later.

So the rule is written down in `scripts/naming.py` and asserted here against
the **committed** `strings.json`, not against the generator's output. Checking
the generator against itself would prove nothing, and would let an entry in the
override table opt itself out of the convention it exists to serve.

Legacy names are the deliberate exception, and the last test pins that: legacy
mode has to reproduce a user's existing entity_ids byte for byte, so the YAML's
inconsistency is preserved there exactly.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, "scripts")

from naming import DIAGNOSTIC, violations

from custom_components.sungrow_modbus.derived_descriptions import (
    DERIVED_BINARY_SENSORS,
    DERIVED_SENSORS,
)
from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
from homeassistant.const import EntityCategory
from homeassistant.util import slugify

REPO = Path(__file__).resolve().parent.parent
COMPONENT = REPO / "custom_components" / "sungrow_modbus"
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"

DESCRIPTIONS = {
    "sensor": (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS),
    "binary_sensor": DERIVED_BINARY_SENSORS,
}
BY_KEY = {d.key: d for group in DESCRIPTIONS.values() for d in group}
DOMAIN_OF = {d.key: domain for domain, group in DESCRIPTIONS.items() for d in group}

NAMES: dict[str, dict[str, str]] = {
    domain: {key: entry["name"] for key, entry in entries.items()}
    for domain, entries in json.loads(
        (COMPONENT / "strings.json").read_text(encoding="utf-8")
    )["entity"].items()
}

#: (domain, key, name) for every entity, which most tests want one at a time.
EVERY_NAME = [
    (domain, key, name)
    for domain, entries in sorted(NAMES.items())
    for key, name in sorted(entries.items())
]


@pytest.mark.parametrize(("domain", "key", "name"), EVERY_NAME)
def test_every_name_follows_the_convention(domain: str, key: str, name: str) -> None:
    problems = violations(key, name, key in DIAGNOSTIC)
    assert not problems, "\n".join(problems)


def test_every_entity_has_a_name_and_no_name_is_orphaned() -> None:
    # A missing entry shows in the interface as the raw translation key; an
    # extra one is a rename that left its old name behind.
    for domain, group in DESCRIPTIONS.items():
        assert {d.key for d in group} == set(NAMES[domain]), domain


@pytest.mark.parametrize("domain", sorted(DESCRIPTIONS))
def test_no_two_entities_share_a_modern_entity_id(domain: str) -> None:
    # Two names slugifying to one id is how the registry ends up appending
    # `_2` to whichever registered second — silently, and to a different one
    # after every restart.
    ids: dict[str, str] = {}
    for key, name in sorted(NAMES[domain].items()):
        object_id = slugify(name)
        assert object_id not in ids, (
            f"{key} and {ids[object_id]} both slugify to {domain}.{object_id}"
        )
        ids[object_id] = key


def test_diagnostic_table_names_only_real_entities() -> None:
    # A key left behind by a rename would silently stop marking anything.
    assert set(BY_KEY) >= DIAGNOSTIC


@pytest.mark.parametrize("key", sorted(BY_KEY))
def test_diagnostic_category_matches_the_table(key: str) -> None:
    expected = EntityCategory.DIAGNOSTIC if key in DIAGNOSTIC else None
    assert BY_KEY[key].entity_category == expected


def test_legacy_names_are_untouched() -> None:
    # The whole point of legacy mode. Every description's `legacy_name` has to
    # be the YAML's name character for character, because that string is what
    # the entity_id a user already has was slugified from.
    # Keyed by the whole entity_id, because the YAML names the same concept
    # twice in two domains — `sensor.battery_max_soc` reads the register and
    # `number.battery_max_soc` writes it, and only the first is ported yet.
    legacy = {
        entity["entity_id"]: entity["name"]
        for entity in json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
    }
    for key, description in BY_KEY.items():
        entity_id = f"{DOMAIN_OF[key]}.{key}"
        if entity_id in legacy:
            assert description.legacy_name == legacy[entity_id], entity_id


def test_the_committed_names_are_what_the_generator_produces() -> None:
    # The convention is checked above; this only catches a strings.json edited
    # by hand, which would come back the next time anybody runs the generator.
    from generate_strings import render

    assert (COMPONENT / "strings.json").read_text(encoding="utf-8") == render()
    assert (COMPONENT / "translations" / "en.json").read_text(
        encoding="utf-8"
    ) == render()
