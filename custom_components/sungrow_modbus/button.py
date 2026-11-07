"""Buttons: the inverter's commands, and on a diagnostics-only entry the diagnosis.

**An ordinary entry** gets the commands in `button_descriptions.py`, each
gated on a capability only a watched write grants. A command register holds
no state worth a switch -- *Force startup* (13017) never reads back the 0xAA
it was sent -- so a press writes one word and the device page shows nothing
else.

**A diagnostics-only entry** gets the diagnosis and capability test buttons, and
nothing else. Such an entry has no readings, no controls and no numbers -- it
was set up by somebody who offered to send a reading and did not want their
house filled with entities -- so these buttons and the three sensors beside
them are the entirety of its device page, and the reason it has one. An
ordinary entry reaches the same runs through the `run_diagnosis` and
`run_capability_test` actions, which leave no entity behind.

The capability test button is there too. That entry mode exists for the
contributor who has hardware and offered to help, which is exactly who this
project needs a write measurement from; what carries the warning is the
button's own description and the guards behind it, not a missing entity.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .button_descriptions import BUTTON_DESCRIPTIONS
from .const import CONF_MODE, MODE_DEVICES, MODE_DIAGNOSTICS
from .coordinator import SungrowConfigEntry
from .diagnosis_entities import CapabilityTestButton, DiagnosisButton
from .entity import SungrowButtonDescription, SungrowEntity

# One at a time, as on every platform that writes: everything on this endpoint
# shares one serialized connection. The diagnosis buttons schedule their run and
# return, and the runner refuses a second run itself, so the limit costs them
# nothing.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the commands this device has, or the diagnosis's buttons.

    No capability test button on an SG: nothing in this integration writes to
    one, and a button that can only refuse is worse than none.
    """
    runtime_data = entry.runtime_data
    if entry.data.get(CONF_MODE, MODE_DEVICES) != MODE_DIAGNOSTICS:
        async_add_entities(
            SungrowButton(runtime_data, description)
            for description in BUTTON_DESCRIPTIONS
            if runtime_data.serves(description)
        )
        return
    if runtime_data.is_string_inverter:
        async_add_entities([DiagnosisButton(runtime_data)])
        return
    async_add_entities(
        [DiagnosisButton(runtime_data), CapabilityTestButton(runtime_data)]
    )


class SungrowButton(SungrowEntity, ButtonEntity):
    """One command register: a press writes its word, then reads back."""

    entity_description: SungrowButtonDescription

    async def async_press(self) -> None:
        """Send the command."""
        await self._async_write(
            (self.entity_description.field, self.entity_description.press_value)
        )
