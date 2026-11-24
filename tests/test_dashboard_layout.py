"""Every entity the dashboard layout names is one the integration has.

The strategy (`frontend/sungrow-modbus.js`) resolves `<domain>.<translation_key>`
against the house's entities and leaves out a card that resolves nothing, which
is right for a capability the house lacks and wrong for a key that was renamed:
that card would vanish from every house without a word. So a key here must be
one `translations/en.json` names for that domain -- and `strings.json`, from
which it is generated, is built from the entity descriptions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import pytest

COMPONENT = Path(__file__).parent.parent / "custom_components" / "sungrow_modbus"
LAYOUT = json.loads(
    (COMPONENT / "frontend" / "layout.json").read_text(encoding="utf-8")
)
TRANSLATIONS = json.loads(
    (COMPONENT / "translations" / "en.json").read_text(encoding="utf-8")
)
#: The views the strategy's `views` option names, in the strategy's order.
VIEW_IDS = [
    "home",
    "energy",
    "history",
    "battery",
    "inverter",
    "wallbox",
    "controls",
    "diagnosis",
]
#: The layout's revision and the digest of its views. **A change to the views
#: raises `revision` and adds a line to `changes`**: that is how the owner of a
#: dashboard taken over learns of it. Then this pair follows.
REVISION = (5, "153f658f5e93")
#: What building the layout takes (`BUILDS` in the module) and the digest of the
#: keys and card types it uses. **A new word the module has to understand raises
#: `module` and `BUILDS`**, so that an older module says "reload" rather than fail.
MODULE = (3, "5a7895f6b89e")
#: Card types the strategy builds: the last nine are its own, the rest core's.
CARD_TYPES = {
    "tile",
    "entities",
    "history-graph",
    "statistics-graph",
    "markdown",
    "energy",
    "flow",
    "energy-flow",
    "tests",
    "settings",
    "run",
    "history",
    "device-link",
    "integration-link",
}


def _section_cards(section: dict):
    for group in section.get("groups", [section]):
        yield from group["cards"]


def _cards():
    for view in LAYOUT["views"]:
        for section in view["sections"]:
            yield from _section_cards(section)


def _badges():
    for view in LAYOUT["views"]:
        yield from view.get("badges", [])


def _refs(card: dict) -> list[str]:
    """Return every reference a card or badge may resolve, alternatives apart."""
    rows = [card["entity"]] if "entity" in card else list(card.get("entities", []))
    rows += card.get("roles", {}).values()
    rows += [card[key] for key in ("status", "step", "progress") if key in card]
    refs = [row["entity"] if isinstance(row, dict) else row for row in rows]
    low, high = card.get("repeat", (1, 1))
    expanded = [
        ref.replace("{n}", str(n)) for ref in refs for n in range(low, high + 1)
    ]
    return [alt.lstrip("~") for ref in expanded for alt in ref.split("|")]


def test_views_are_the_ones_the_strategy_offers() -> None:
    assert [view["id"] for view in LAYOUT["views"]] == VIEW_IDS


def test_every_card_type_is_one_the_strategy_builds() -> None:
    assert {card["type"] for card in _cards()} <= CARD_TYPES


@pytest.mark.parametrize(
    "ref", sorted({ref for card in [*_cards(), *_badges()] for ref in _refs(card)})
)
def test_every_entity_is_one_the_integration_has(ref: str) -> None:
    domain, _, key = ref.partition(".")
    assert key in TRANSLATIONS["entity"].get(domain, {}), (
        f"{ref} is not a translation key of {domain}"
    )


def test_every_view_a_tap_opens_is_one_there_is() -> None:
    sections = [s for view in LAYOUT["views"] for s in view["sections"]]
    for item in [*_cards(), *_badges(), *sections]:
        assert item.get("view", VIEW_IDS[0]) in VIEW_IDS, item


def test_a_setting_is_behind_the_lock_or_opens_no_dialog() -> None:
    """Its dialog would change the setting past the lock.

    But Stop, which is never to be refused.
    """
    writable = {"number", "select", "switch", "time", "button"}
    for view in LAYOUT["views"]:
        if view.get("locked"):
            continue
        for section in view["sections"]:
            for group in section.get("groups", [section]):
                if group.get("locked") or section.get("control"):
                    continue
                for card in group["cards"]:
                    refs = set(_refs(card)) - {"button.diagnosis_stop"}
                    if {ref.partition(".")[0] for ref in refs} & writable:
                        assert card.get("more_info") is False, card


def test_what_writes_is_for_administrators() -> None:
    for view in LAYOUT["views"]:
        groups = [g for s in view["sections"] for g in s.get("groups", [s])]
        if view.get("locked") or any(group.get("locked") for group in groups):
            assert view.get("admin") is True, view["id"]


def test_allowing_a_test_is_locked_and_answering_is_not() -> None:
    for view in LAYOUT["views"]:
        for section in view["sections"]:
            for group in section.get("groups", [section]):
                for card in group["cards"]:
                    if card["type"] == "settings":
                        assert bool(group.get("locked")) == (card["part"] == "tests")


def test_stop_is_never_locked() -> None:
    for view in LAYOUT["views"]:
        for section in view["sections"]:
            for group in section.get("groups", [section]):
                if any("button.diagnosis_stop" in _refs(c) for c in group["cards"]):
                    assert not (view.get("locked") or group.get("locked"))


def test_starting_and_clearing_are_locked_and_the_status_is_not() -> None:
    for view in LAYOUT["views"]:
        for section in view["sections"]:
            for group in section.get("groups", [section]):
                for card in group["cards"]:
                    if card["type"] == "run":
                        assert bool(group.get("locked")) == (card["part"] != "now")


def test_a_changed_layout_raises_its_revision() -> None:
    views = json.dumps(LAYOUT["views"], sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(views.encode()).hexdigest()[:12]
    assert (LAYOUT["revision"], digest) == REVISION
    assert max(c["revision"] for c in LAYOUT["changes"]) == LAYOUT["revision"]


def test_every_text_has_english_and_german() -> None:
    texts = re.findall(r'\{"en": [^{}]*\}', json.dumps(LAYOUT, ensure_ascii=False))
    assert texts
    for text in texts:
        assert set(json.loads(text)) == {"en", "de"}, text


def _vocabulary(value: object, keys: frozenset[str] = frozenset()) -> frozenset[str]:
    """Return every key and card type the layout uses."""
    if isinstance(value, dict):
        kind = (
            {f"type={value['type']}"} if isinstance(value.get("type"), str) else set()
        )
        return frozenset({*value, *kind}).union(*map(_vocabulary, value.values()))
    if isinstance(value, list):
        return frozenset().union(*map(_vocabulary, value))
    return keys


def test_a_module_too_old_for_the_layout_says_so() -> None:
    """A tab open over an update runs the old module on the new layout."""
    words = "\n".join(sorted(_vocabulary(LAYOUT["views"])))
    digest = hashlib.sha256(words.encode()).hexdigest()[:12]
    assert (LAYOUT["module"], digest) == MODULE
    script = (COMPONENT / "frontend" / "sungrow-modbus.js").read_text(encoding="utf-8")
    assert f"const BUILDS = {LAYOUT['module']};" in script
