"""The flows' sentences come from the translation, never from the code.

A dialog's description is translated, but a placeholder is inserted as it is,
so a sentence built in code reached a German dialog in English (found
2026-11-06). `texts.py` holds the fix: every sentence the flows choose between
is a `flow_text` entry in `strings.json`, and the generator writes its German.
These tests hold the two ends together.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

from custom_components.sungrow_modbus import config_flow
from custom_components.sungrow_modbus.texts import async_texts
from homeassistant.core import HomeAssistant

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "sungrow_modbus"
TABLE = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))[
    "selector"
]["flow_text"]["options"]
GERMAN = json.loads(
    (COMPONENT / "translations" / "de.json").read_text(encoding="utf-8")
)["selector"]["flow_text"]["options"]

SOURCE = "\n".join(path.read_text(encoding="utf-8") for path in COMPONENT.glob("*.py"))

#: Every `texts("key"...)` call in the integration's code.
CALLED = set(re.findall(r'texts\(\s*"(\w+)"', SOURCE))

#: Every table key the code names anywhere, which also counts a key chosen
#: through a variable (`key = "survey_direct"`) or called on the table
#: directly (the repair's `(await async_texts(hass))("...")`).
USED = {key for key in TABLE if f'"{key}"' in SOURCE}


def test_every_sentence_the_code_asks_for_exists() -> None:
    assert CALLED - set(TABLE) == set()


def test_no_sentence_in_the_table_is_left_unused() -> None:
    assert set(TABLE) - USED == set()


def test_every_sentence_has_its_german() -> None:
    assert set(GERMAN) == set(TABLE)


async def test_a_german_system_gets_the_german_sentence(hass: HomeAssistant) -> None:
    hass.config.language = "de"
    texts = await async_texts(hass)

    assert texts("package_not_loaded") == GERMAN["package_not_loaded"]
    assert texts("package_loaded", live=3).startswith(
        "⚠️ **Das YAML-Paket läuft noch.** 3"
    )


async def test_english_answers_where_a_language_has_no_translation(
    hass: HomeAssistant,
) -> None:
    hass.config.language = "fr"
    texts = await async_texts(hass)

    assert texts("package_not_loaded") == TABLE["package_not_loaded"]


async def test_the_yaml_question_s_status_is_german_on_a_german_system(
    hass: HomeAssistant,
) -> None:
    """The case that was found: a German page, an English status line."""
    hass.config.language = "de"
    texts = await async_texts(hass)

    free = config_flow._entity_ids_placeholders({"sensor.a"}, set(), texts)
    held = config_flow._entity_ids_placeholders({"sensor.a"}, {"sensor.a"}, texts)

    assert free["status"] == GERMAN["package_not_loaded"]
    assert "läuft noch" in held["status"]
    assert "running" not in free["status"] + held["status"]
