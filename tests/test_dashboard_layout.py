"""Every entity the dashboard layout names is one the integration has.

The strategy (`frontend/sungrow-modbus.js`) resolves `<domain>.<translation_key>`
against the house's entities and leaves out a card that resolves nothing, which
is right for a capability the house lacks and wrong for a key that was renamed:
that card would vanish from every house without a word. So a key here must be
one `translations/en.json` names for that domain -- and `strings.json`, from
which it is generated, is built from the entity descriptions.
"""

from __future__ import annotations

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
VIEW_IDS = ["overview", "battery", "inverter", "wallbox", "controls"]
#: Card types the strategy builds: `device-link` is its own, the rest Home Assistant's.
CARD_TYPES = {
    "tile",
    "gauge",
    "entities",
    "history-graph",
    "statistics-graph",
    "markdown",
    "device-link",
}


def _cards():
    for view in LAYOUT["views"]:
        for section in view["sections"]:
            yield from section["cards"]


def _refs(card: dict) -> list[str]:
    refs = [card["entity"]] if "entity" in card else list(card.get("entities", []))
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
    "ref", sorted({ref for card in _cards() for ref in _refs(card)})
)
def test_every_entity_is_one_the_integration_has(ref: str) -> None:
    domain, _, key = ref.partition(".")
    assert key in TRANSLATIONS["entity"].get(domain, {}), (
        f"{ref} is not a translation key of {domain}"
    )


def test_every_text_has_english_and_german() -> None:
    texts = re.findall(r'\{"en": [^{}]*\}', json.dumps(LAYOUT, ensure_ascii=False))
    assert texts
    for text in texts:
        assert set(json.loads(text)) == {"en", "de"}, text
