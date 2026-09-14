"""The one button this integration has: run a capability survey.

Set up in both modes, and that is the point of the platform existing at all.
A diagnostics-only entry has no sensors, no controls and no numbers -- it was
set up by somebody who offered to send a reading and did not want their house
filled with entities -- so this button and the three sensors beside it are
the entirety of its device page, and the reason it has one.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .survey_entities import SurveyButton


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the survey button."""
    async_add_entities([SurveyButton(entry.runtime_data)])
