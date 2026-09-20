"""The two buttons this integration has: survey, and control test.

Set up in both modes, and that is the point of the platform existing at all.
A diagnostics-only entry has no sensors, no controls and no numbers -- it was
set up by somebody who offered to send a reading and did not want their house
filled with entities -- so these buttons and the three sensors beside them are
the entirety of its device page, and the reason it has one.

Both are set up in both modes, the control test included. That entry mode
exists for the contributor who has hardware and offered to help, which is
exactly who this project needs a write measurement from; what carries the
warning is the button's own description and the guards behind it, not a
missing entity.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .survey_entities import ControlTestButton, SurveyButton

# A press schedules the run and returns; it does not hold the call open for
# the ten minutes a control test takes. So there is nothing to serialize here,
# and a limit would suggest there is. The runner refuses a second run itself,
# which is the check that actually matters: two surveys would interleave on one
# serialized connection.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the survey button and the control test button."""
    async_add_entities(
        [SurveyButton(entry.runtime_data), ControlTestButton(entry.runtime_data)]
    )
