"""Buttons: the diagnosis on every entry, and the inverter's commands besides.

**The diagnosis's buttons** -- start, stop, and clear the capability test's
history -- are on every inverter entry, so the one way this project measures
what a model answers is on the device page of whoever has the model, not
behind a diagnostics-only entry or an action in Developer tools. They are
diagnostic-category entities, so Home Assistant files them under their own
heading on the device page.

The capability test's start is among them, and deliberately: the contributor
who has hardware is exactly who this project needs a write measurement from.
What carries the warning is the button's own description, the mode select
beside it and the guards in `sungrow_modbus.capability_test`, not a missing
entity.

**The commands** in `button_descriptions.py` come after, each gated on a
capability only a watched write grants. A command register holds no state
worth a switch -- *Force startup* (13017) never reads back the 0xAA it was
sent -- so a press writes one word and the device page shows nothing else.
A diagnostics-only entry and an SG get none of them: the first writes nothing
but the capability test's own probes, and nothing here writes to an SG at all.

The same runs are reachable as the `run_diagnosis` and `run_capability_test`
actions, which is what a script or an automation can call.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .button_descriptions import BUTTON_DESCRIPTIONS
from .const import CONF_MODE, MODE_DEVICES, MODE_DIAGNOSTICS
from .coordinator import SungrowConfigEntry
from .diagnosis_entities import (
    ClearCapabilityTestHistoryButton,
    ClearCapabilityTestReadingsButton,
    DiagnosisStartButton,
    DiagnosisStopButton,
)
from .entity import SungrowButtonDescription, SungrowEntity

# One at a time, as on every platform that writes (see `number.py`):
# everything on this endpoint shares one serialized connection. The diagnosis
# buttons schedule their run and return, and the runner refuses a second run
# itself, so the limit costs them nothing.
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
    if runtime_data.is_wallbox_only:
        # Its diagnosis and capability test; the test writes only with leave.
        async_add_entities(
            [
                DiagnosisStartButton(runtime_data),
                DiagnosisStopButton(runtime_data),
                ClearCapabilityTestHistoryButton(runtime_data),
                ClearCapabilityTestReadingsButton(runtime_data),
            ]
        )
        return
    if runtime_data.is_device_only:
        # A read-only diagnosis, nothing else.
        async_add_entities(
            [DiagnosisStartButton(runtime_data), DiagnosisStopButton(runtime_data)]
        )
        return
    # The diagnosis's own buttons, on every inverter entry whatever its mode:
    # the one thing this project needs from a device -- a measurement of what
    # it answers -- belongs on its device page, not behind Developer tools.
    async_add_entities(
        [DiagnosisStartButton(runtime_data), DiagnosisStopButton(runtime_data)]
    )
    if runtime_data.is_string_inverter:
        # No capability test on an SG, so no history of one to clear -- and
        # nothing here writes to one, so none of the commands either.
        return
    async_add_entities(
        [
            ClearCapabilityTestHistoryButton(runtime_data),
            ClearCapabilityTestReadingsButton(runtime_data),
        ]
    )

    # A diagnostics-only entry stops there: no commands, because it writes
    # nothing but the capability test's own probes.
    if entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
        return

    async_add_entities(
        SungrowButton(runtime_data, description)
        for description in BUTTON_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowButton(SungrowEntity, ButtonEntity):
    """One command register: a press writes its word, then reads back."""

    entity_description: SungrowButtonDescription

    async def async_press(self) -> None:
        """Send the command."""
        await self._async_write(
            (self.entity_description.field, self.entity_description.press_value)
        )
