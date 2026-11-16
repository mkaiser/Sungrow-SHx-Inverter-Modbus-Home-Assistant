"""`doc/scenes.md` is a user's copy-paste, so every value in it must be live.

The page exists because the YAML package's scenes cannot be pasted back: the
package's dropdowns held their label, the integration's hold an option key,
and Home Assistant skips an entity whose stored state no option matches
(`homeassistant/components/select/reproduce_state.py`) while applying the
rest of the scene around it. A rewritten scene that goes stale the same way
would fail the same silent half-applied way, in somebody's house, so the
page is held to the descriptions here rather than proof-read.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from custom_components.sungrow_modbus.migration import legacy_entity_id
from custom_components.sungrow_modbus.number_descriptions import NUMBER_DESCRIPTIONS
from custom_components.sungrow_modbus.select_descriptions import SELECT_DESCRIPTIONS
from custom_components.sungrow_modbus.switch_descriptions import SWITCH_DESCRIPTIONS
from homeassistant.util import slugify

PAGE = Path(__file__).resolve().parents[1] / "doc" / "scenes.md"

#: The legacy entity_id of every entity the page may name, to its description.
BY_LEGACY_ID = {
    legacy_entity_id(platform, description): description
    for platform, table in (
        ("select", SELECT_DESCRIPTIONS),
        ("number", NUMBER_DESCRIPTIONS),
        ("switch", SWITCH_DESCRIPTIONS),
    )
    for description in table
    if legacy_entity_id(platform, description) is not None
}


def _blocks() -> list[Any]:
    """Return every fenced YAML block on the page, parsed."""
    found = re.findall(r"```yaml\n(.*?)```", PAGE.read_text(), re.DOTALL)
    assert found, "no YAML blocks on the page"
    return [yaml.safe_load(text) for text in found]


def _scenes() -> list[dict[str, Any]]:
    """Return the scene definitions: the first block on the page."""
    scenes = _blocks()[0]
    assert isinstance(scenes, list)
    return scenes


def test_the_page_offers_every_scene_the_package_had() -> None:
    """Seven, so nobody migrating finds one of theirs quietly dropped.

    Read from the package's own `scene:` block rather than from a list kept
    here, so a scene added or renamed there is not silently left behind.
    """
    package = Path(__file__).resolve().parents[1] / "legacy" / "modbus_sungrow.yaml"
    text = package.read_text()
    block = text[text.index("\nscene:\n") :]
    had = re.findall(r"^  - name: (.+)$", block, re.MULTILINE)
    assert len(had) == 7, had

    assert sorted(scene["name"] for scene in _scenes()) == sorted(had)


@pytest.mark.parametrize("scene", _scenes(), ids=lambda scene: scene["name"])
def test_every_entity_named_is_one_the_integration_creates(
    scene: dict[str, Any],
) -> None:
    """A typo here is a line in somebody's log and nothing on their screen."""
    for entity_id in scene["entities"]:
        assert entity_id in BY_LEGACY_ID, entity_id


@pytest.mark.parametrize("scene", _scenes(), ids=lambda scene: scene["name"])
def test_every_value_is_one_the_entity_accepts(scene: dict[str, Any]) -> None:
    """The failure this page was written to end, caught in the repository.

    A select takes an option key; a switch takes on or off; a number takes a
    value inside its own range, where that range is fixed rather than read
    from the device (`native_max_value` 0 means the device decides).
    """
    for entity_id, value in scene["entities"].items():
        description = BY_LEGACY_ID[entity_id]
        platform = entity_id.split(".", 1)[0]
        if platform == "select":
            assert value in description.options, f"{entity_id}: {value}"
        elif platform == "switch":
            assert value in ("on", "off"), f"{entity_id}: {value}"
        else:
            assert isinstance(value, int | float), f"{entity_id}: {value}"
            assert value >= description.native_min_value, f"{entity_id}: {value}"
            if description.native_max_value:
                assert value <= description.native_max_value, f"{entity_id}: {value}"


def test_the_automations_fire_on_scenes_the_page_defines() -> None:
    """An automation keyed to a scene that is not here would never run."""
    # Home Assistant's own slugify, because that is what builds the id the
    # trigger has to match -- `(max battery discharge)` loses its brackets
    # and `Self-Consumption` its hyphen, and guessing either is how a
    # trigger comes to name an entity that never exists.
    slugs = {slugify(scene["name"]) for scene in _scenes()}

    for automation in _blocks()[1]:
        for trigger in automation["triggers"]:
            entity_id = trigger["entity_id"]
            assert entity_id.startswith("scene."), entity_id
            assert entity_id.removeprefix("scene.") in slugs, entity_id
