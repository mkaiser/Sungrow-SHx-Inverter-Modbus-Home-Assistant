"""Which entry answers the questions an extended run is refused without."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_DIAGNOSIS_OTHER_INVERTER,
    CONF_DIAGNOSIS_PROXY,
    CONF_DIAGNOSIS_TRANSPORT,
    CONF_KIND,
    DOMAIN,
    KIND_WALLBOX,
)
from custom_components.sungrow_modbus.testimony import (
    REQUIRED,
    async_refuse_if_unanswered,
    unanswered,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

ANSWERS = {
    CONF_DIAGNOSIS_TRANSPORT: "direct_lan",
    CONF_DIAGNOSIS_PROXY: "no",
    CONF_DIAGNOSIS_OTHER_INVERTER: "unknown",
}
MANAGING = "custom_components.sungrow_modbus.wallbox_capability_test.managing_entry"


def _wallbox(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_KIND: KIND_WALLBOX}, title="AC22E-01"
    )
    entry.add_to_hass(hass)
    return entry


def _inverter(hass: HomeAssistant, options: dict[str, str]) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options, title="SH8.0RT")
    entry.add_to_hass(hass)
    return entry


async def test_an_inverter_entry_answers_for_itself(hass: HomeAssistant) -> None:
    """The questions are on the inverter's own options page."""
    assert unanswered(hass, _inverter(hass, {})) == [label for _, label in REQUIRED]
    assert unanswered(hass, _inverter(hass, ANSWERS)) == []


async def test_a_managed_wallbox_is_answered_by_its_inverter(
    hass: HomeAssistant,
) -> None:
    """A wallbox's options have no inverter questions (gerd's, 2026-11-17).

    The managed test was refused for answers its own options page cannot
    give; the house it runs in is the managing inverter entry's.
    """
    wallbox = _wallbox(hass)
    inverter = _inverter(hass, {})
    with patch(MANAGING, return_value=inverter):
        assert len(unanswered(hass, wallbox)) == 3
        with pytest.raises(ServiceValidationError, match="testimony_missing") as err:
            async_refuse_if_unanswered(hass, wallbox)
        # The refusal names the entry where the answers go.
        assert err.value.translation_placeholders == {"title": "SH8.0RT"}

        hass.config_entries.async_update_entry(inverter, options=ANSWERS)
        assert unanswered(hass, wallbox) == []
        async_refuse_if_unanswered(hass, wallbox)


async def test_a_wallbox_no_inverter_manages_is_asked_nothing(
    hass: HomeAssistant,
) -> None:
    """No inverter to describe: the three questions do not apply."""
    wallbox = _wallbox(hass)
    with patch(MANAGING, return_value=None):
        assert unanswered(hass, wallbox) == []
        async_refuse_if_unanswered(hass, wallbox)
