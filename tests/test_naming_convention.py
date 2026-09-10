"""One naming convention, enforced over all 127 entities.

The YAML package's names drifted because nothing checked them: `Battery min
SoC` beside `Battery Min Soc`, fourteen title-cased names among sentence-cased
ones, fifteen beginning with the device's own name. That is not a style
complaint. With `has_entity_name` set, the object id is slugified from the
name, so "Sungrow inverter serial" gives `sensor.sh10rt_sungrow_inverter_serial`
where "Serial number" gives `sensor.sh10rt_serial_number` — the names *are*
the ids -- cheap to change now and awkward later, though not impossible: a
name supplies an entity_id only at *creation*, so a rename after release
leaves an existing install's id alone and merely diverges it from a fresh
one. `tests/test_entity_naming.py` pins that.

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

from custom_components.sungrow_modbus.battery_descriptions import BATTERY_DESCRIPTIONS
from custom_components.sungrow_modbus.derived_descriptions import (
    DERIVED_BINARY_SENSORS,
    DERIVED_SENSORS,
)
from custom_components.sungrow_modbus.external_descriptions import EXTERNAL_SENSORS
from custom_components.sungrow_modbus.number_descriptions import NUMBER_DESCRIPTIONS
from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS
from custom_components.sungrow_modbus.sensor_descriptions import SENSOR_DESCRIPTIONS
from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
from custom_components.sungrow_modbus.wallbox_descriptions import (
    WALLBOX_BINARY_DESCRIPTIONS,
    WALLBOX_DESCRIPTIONS,
)
from homeassistant.const import EntityCategory
from homeassistant.util import slugify

REPO = Path(__file__).resolve().parent.parent
COMPONENT = REPO / "custom_components" / "sungrow_modbus"
ENTITY_MAP = REPO / "doc" / "legacy_entity_map.json"

DESCRIPTIONS = {
    # The battery's are here for the reason they most need to be: they are
    # the only descriptions in the integration that are **hand-written**, so
    # they are the ones a convention stops covering by accident.
    "sensor": (
        *SENSOR_DESCRIPTIONS,
        *DERIVED_SENSORS,
        *BATTERY_DESCRIPTIONS,
        *WALLBOX_DESCRIPTIONS,
        # Hand-written for a third reason again: these are arithmetic over
        # another integration's entities, so there is no register and no
        # legacy name to derive one from.
        *EXTERNAL_SENSORS,
    ),
    "binary_sensor": (*DERIVED_BINARY_SENSORS, *WALLBOX_BINARY_DESCRIPTIONS),
    # The writable platforms are held to the same convention. They carry the
    # worst of the YAML's names -- `Battery Max Soc`, `Battery Reserved SoC
    # for Backup` -- which is exactly why they are checked and not exempted.
    "number": NUMBER_DESCRIPTIONS,
    "switch": SWITCH_DESCRIPTIONS,
    "select": SELECT_DESCRIPTIONS,
}
#: Every description, keyed by the entity_id it becomes rather than by its
#: key. The YAML names the same concept in two domains -- `battery_max_soc` is
#: a sensor that reads the register and a number that writes it -- so keying by
#: key alone drops one of each pair silently, which is how five of these
#: entities would have gone unchecked.
BY_ID = {
    f"{domain}.{d.key}": d for domain, group in DESCRIPTIONS.items() for d in group
}
KEYS = {d.key for group in DESCRIPTIONS.values() for d in group}

#: Platforms whose entities are settings rather than readings.
CONFIG_DOMAINS = {"number", "switch", "select"}

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
    """Two names slugifying to one id, on one device, is how `_2` happens.

    Silently, and to a different entity after every restart.

    **Per device**, for the same reason the name rule is: Home Assistant
    prefixes the device name onto the object id, so the inverter's firmware
    version is `sensor.sh10rt_firmware_version` and the wallbox's is
    `sensor.ac22e_01_firmware_version`. Both are called "Firmware version",
    which is the right name for each, and neither collides. Scoping this
    globally would have forced one of them to be called something worse.
    """
    ids: dict[tuple[str, str], str] = {}
    for key, name in sorted(NAMES[domain].items()):
        where = (_device(key, domain), slugify(name))
        assert where not in ids, (
            f"{key} and {ids[where]} both slugify to "
            f"{domain}.{where[1]} on the {where[0]}"
        )
        ids[where] = key


def test_diagnostic_table_names_only_real_entities() -> None:
    # A key left behind by a rename would silently stop marking anything.
    assert KEYS >= DIAGNOSTIC


@pytest.mark.parametrize("entity_id", sorted(BY_ID))
def test_the_entity_category_matches_what_the_entity_is(entity_id: str) -> None:
    domain, key = entity_id.split(".", 1)
    if domain in CONFIG_DOMAINS:
        # A writable entity is a setting, and CONFIG is what Home Assistant
        # calls that. It has to be one consistently or the controls scatter
        # between the Controls and Configuration sections of the device page.
        assert BY_ID[entity_id].entity_category == EntityCategory.CONFIG
        return
    expected = EntityCategory.DIAGNOSTIC if key in DIAGNOSTIC else None
    assert BY_ID[entity_id].entity_category == expected


def test_legacy_names_are_untouched() -> None:
    """Every `legacy_name` is the YAML's name, character for character.

    The whole point of legacy mode: that string is what the entity_id a user
    already has was slugified from, so a single character wrong is a dashboard
    and years of history pointing at nothing.

    Looked up by `legacy_unique_id`, which is what actually identifies the
    YAML entity being replaced. Looking it up by the *modern* entity_id --
    which this test used to do -- silently checked nothing for any entity
    whose key was renamed on the way over, and five were: the three switches
    and both mode selects. `switch.export_power_limit` became
    `switch.export_power_limit_mode`, so the lookup missed and the assertion
    never ran on the name that carries the migration.
    """
    legacy = {
        (entity["domain"], entity["unique_id"]): entity["name"]
        for entity in json.loads(ENTITY_MAP.read_text(encoding="utf-8"))["entities"]
        # A specification addition has no YAML entity behind it, so it has no
        # legacy name to preserve -- and must not claim one.
        if entity["layer"] != "specification" and entity.get("unique_id")
    }
    checked = 0
    for entity_id, description in BY_ID.items():
        unique_id = getattr(description, "legacy_unique_id", None)
        if not unique_id:
            continue
        domain = entity_id.split(".", 1)[0]
        # A description naming a unique_id the YAML does not have would
        # migrate nothing, silently.
        assert (domain, unique_id) in legacy, f"{entity_id}: unknown {unique_id}"
        assert description.legacy_name == legacy[domain, unique_id], entity_id
        checked += 1
    # Guard the guard: an exception path that skipped everything would pass.
    assert checked >= 120, f"only checked {checked} legacy names"


def test_the_committed_names_are_what_the_generator_produces() -> None:
    # The convention is checked above; this only catches a strings.json edited
    # by hand, which would come back the next time anybody runs the generator.
    from generate_strings import render

    assert (COMPONENT / "strings.json").read_text(encoding="utf-8") == render()
    assert (COMPONENT / "translations" / "en.json").read_text(
        encoding="utf-8"
    ) == render()


def _key_paths(value: object, prefix: str = "") -> set[str]:
    """Return the dotted path to every leaf string in a translations file."""
    if isinstance(value, dict):
        return {
            path
            for key, child in value.items()
            for path in _key_paths(child, f"{prefix}.{key}" if prefix else key)
        }
    return {prefix}


@pytest.mark.parametrize(
    "path", sorted((COMPONENT / "translations").glob("*.json")), ids=lambda p: p.name
)
def test_every_translation_carries_the_same_keys(path: Path) -> None:
    """A translation with a missing key falls back silently to English.

    Which is the good case. The bad one is a key a translation carries that
    `strings.json` does not: it is dead weight that reads as a translated
    string somebody is maintaining, and it is what a key renamed on one side
    of the pair leaves behind. Neither shows up in the UI, so neither shows up
    in review either.

    Home Assistant's own hassfest validates the *shape* of these files. It
    does not compare one against another, because for core integrations
    translations arrive from Lokalise and cannot drift. This one is written by
    hand.
    """
    source = _key_paths(json.loads((COMPONENT / "strings.json").read_text("utf-8")))
    translated = _key_paths(json.loads(path.read_text("utf-8")))

    assert not translated - source, f"{path.name} translates keys that do not exist"
    missing = source - translated
    # English is the source, so it is the one file that has to be complete.
    if path.stem == "en":
        assert not missing, "en.json is the source language and must be complete"


#: Which device each description's entity belongs to.
#:
#: The integration creates three devices now -- the inverter, an SBR pack on
#: its own unit, and a wallbox on another -- and each gets its own page in
#: Home Assistant, with its own name prefixed onto every entity id.
DEVICE_OF = {
    id(description): device
    for device, group in (
        ("battery", BATTERY_DESCRIPTIONS),
        ("wallbox", WALLBOX_DESCRIPTIONS),
    )
    for description in group
}


def _device(key: str, domain: str) -> str:
    """Return which device an entity sits on, defaulting to the inverter."""
    for group_domain, group in DESCRIPTIONS.items():
        if group_domain != domain:
            continue
        for description in group:
            if description.key == key:
                return DEVICE_OF.get(id(description), "inverter")
    return "inverter"


def test_no_two_entities_a_user_sees_share_a_name() -> None:
    """One name, one entity — on the page a user actually looks at.

    Per-domain uniqueness above stops the registry appending `_2`. This is the
    other problem, which that test cannot see: a device page lists every
    domain together, so three entities named "Export power limit" -- the
    switch that turns limiting on, the number that sets the watts, and a
    read-only copy of that number -- are three rows a user cannot tell apart,
    and three identical choices in an automation picker.

    **Scoped per device**, which is what "the page a user looks at" means now
    that there are three of them. The rule was written when the integration
    made one device and read as global; a wallbox reporting "Phase A current"
    is not competing with an inverter reporting "Phase A current", because
    they are on separate pages, Home Assistant prefixes the device name onto
    each, and the entity ids differ -- `sensor.sh10rt_phase_a_current` beside
    `sensor.ac22e_01_phase_a_current`. Forcing them apart would mean
    inventing a prefix for a device that already has a name, which is the
    duplication the convention exists to remove.

    Where a name genuinely benefits from a distinguisher it still gets one:
    the pack's own voltage is "Pack voltage", not "Voltage", because the
    inverter reports its own view of the same quantity and a reader comparing
    the two should be able to tell which is which from the name.

    Also scoped to what **modern mode creates**, because legacy mode
    deliberately reproduces the YAML package's duplicates: it has both
    `number.battery_max_soc` and `sensor.battery_max_soc` because a YAML
    sensor cannot be written, and a migrating user's history depends on both
    existing. Those seventeen are `legacy_only` and are not created here.
    """
    from naming import LEGACY_ONLY_SENSORS

    seen: dict[tuple[str, str], str] = {}
    for domain, key, name in EVERY_NAME:
        if domain == "sensor" and key in LEGACY_ONLY_SENSORS:
            continue
        where = (_device(key, domain), name)
        assert where not in seen, (
            f"{domain}.{key} and {seen[where]} are both called {name!r} on the "
            f"{where[0]}, so its device page lists the same label twice"
        )
        seen[where] = f"{domain}.{key}"


def test_the_ing_ending_is_reserved_for_things_that_are_happening() -> None:
    """`-ing` means "right now", so it belongs to states and not to switches.

    Three names end in it -- Battery charging, Battery discharging, PV
    generating -- and all three are binary sensors reporting a condition. That
    is a pattern worth keeping: a switch called "Export power limiting" would
    read as something observed rather than something toggled, which is why
    that proposal was dropped in favour of "Export power limit mode",
    following `switch.backup_mode`.
    """
    for domain, key, name in EVERY_NAME:
        if name.lower().endswith("ing"):
            assert domain == "binary_sensor", (
                f"{domain}.{key} is called {name!r}; an -ing name reads as a "
                "condition, so it belongs to a binary sensor"
            )


def test_a_parenthetical_says_what_the_value_is() -> None:
    """Not which Home Assistant option produced it.

    Both parentheticals arrived from the YAML package naming a mechanism:
    `filter` was the platform it used for the moving average, `delay_on` the
    template option behind the seven binary sensors. A user should no more
    have to know that than they should have to know that 170 means enabled.

    The two are **not** the same mechanism, which is why they do not share a
    word: `(smoothed)` is a 300-second time-weighted average of a number, and
    `(delayed)` is a boolean that rises after sixty seconds and falls at once.
    Calling the second one smoothed would promise flicker suppression in both
    directions, and an automation built on that promise would be wrong every
    time a reading dipped.
    """
    # The rule is about *these words*, not about their grammar. A first
    # version also demanded the qualifier end in "-ed" or contain a space,
    # and it failed on `Battery charge (nominal)` -- which is a perfectly
    # good qualifier describing the value as the nameplate figure rather than
    # a measurement. Naming the mechanism is the mistake; adjectives are not.
    banned = {"filtered", "delay", "raw", "debounced", "template", "filter"}
    for domain, key, name in EVERY_NAME:
        if not name.endswith(")"):
            continue
        inside = name.rsplit("(", 1)[1].rstrip(")").strip().lower()
        assert inside not in banned, (
            f"{domain}.{key} is called {name!r}; a parenthetical names what "
            "the value is, not the option that produced it"
        )
