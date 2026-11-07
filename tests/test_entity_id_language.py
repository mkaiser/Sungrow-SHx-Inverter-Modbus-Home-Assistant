"""Entity ids are English in every language; only the names are translated.

Home Assistant builds a new entity's id from its name in the system's
language, and German is one of the languages it does that for. One id has to
mean the same entity in every house, in the docs and in support
(`doc/architecture.md`), so `entity.EnglishEntityId` builds it from `en.json`
while the displayed name follows the system's language.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_MODE,
    CONF_UNIT_ID,
    DOMAIN,
    MODE_DEVICES,
)
from homeassistant.const import ATTR_FRIENDLY_NAME, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .conftest import SERIAL


async def _set_up(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.178.35",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODE: MODE_DEVICES,
        },
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


#: The English names, which every id is built from.
ENGLISH = json.loads(
    (
        Path(__file__).parent.parent
        / "custom_components/sungrow_modbus/translations/en.json"
    ).read_text(encoding="utf-8")
)["entity"]


@pytest.mark.parametrize(
    ("language", "name"),
    [
        ("en", "SH10RT Total PV input power"),
        ("de", "SH10RT Gesamte PV-Eingangsleistung"),
    ],
)
async def test_the_id_is_english_and_the_name_is_translated(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit, language: str, name: str
) -> None:
    """A German system gets the English id and the German name."""
    hass.config.language = language
    await _set_up(hass, sungrow_unit)

    state = hass.states.get("sensor.sh10rt_total_pv_input_power")
    assert state is not None
    assert state.attributes[ATTR_FRIENDLY_NAME] == name


async def test_every_id_is_english_in_german(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Not one entity, every one: a German id anywhere is the bug.

    Each id is checked against the one its English name makes, rather than
    against an English run's: Home Assistant hands a removed entity its old
    id back, so a second setup in one test would pass without the fix.
    """
    hass.config.language = "de"
    entry = await _set_up(hass, sungrow_unit)

    items = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert items
    for item in items:
        assert item.translation_key is not None, item.entity_id
        english = ENGLISH[item.domain][item.translation_key]["name"]
        assert item.entity_id == f"{item.domain}.{slugify(f'SH10RT {english}')}"
