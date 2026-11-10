"""Mode flags, each one holding register carrying 0xAA or 0x55.

The YAML package used the Modbus platform's own `switches:` with
`verify: true`, which reads the register back after writing to confirm it
took. That instinct was right and is kept: the write is followed by a refresh,
so what the interface shows afterwards is what the inverter actually holds
rather than what it was asked for.

What is *not* kept is the YAML's assumption that any value other than the
`on` code means off. A register reporting the specification's 0xFFFF
"unavailable" sentinel is neither on nor off, and saying "off" to that is how
a user concludes a feature is disabled when in fact their model does not have
it.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MODE, MODE_DEVICES, MODE_DIAGNOSTICS
from .coordinator import SungrowConfigEntry
from .diagnosis_entities import SkipEstablishedCapabilityTestsSwitch
from .entity import SungrowEntity, SungrowSwitchDescription
from .switch_descriptions import SWITCH_DESCRIPTIONS

# One at a time, and not for the usual reason. A Sungrow accepts very few
# simultaneous Modbus sessions, and everything on this endpoint is already
# serialized behind one connection -- so two writes issued at once do not go
# faster, they queue, and the second one's timeout starts while it is still
# waiting. Worse, these registers interlock: `battery_min_soc` and
# `battery_max_soc` are rejected if they cross, so an automation that sets both
# in one call has an ordering that matters and must not be raced.
#
# `sensor` and `binary_sensor` set 0 instead because the coordinator does their
# polling and the entities never talk to the inverter at all.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mode flags this device actually has."""
    runtime_data = entry.runtime_data
    if (
        runtime_data.is_wallbox_only
        or entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS
    ):
        # A diagnostics-only entry has no controls; its one switch is what a
        # single extended run leaves out, and only a hybrid has a capability
        # test.
        if not runtime_data.is_string_inverter:
            async_add_entities([SkipEstablishedCapabilityTestsSwitch(runtime_data)])
        return
    async_add_entities(
        SungrowSwitch(runtime_data, description)
        for description in SWITCH_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowSwitch(SungrowEntity, SwitchEntity):
    """One mode flag, read and written by the same entity."""

    entity_description: SungrowSwitchDescription

    @property
    def is_on(self) -> bool | None:
        """Return whether the flag is set, or None if it is neither.

        Three states, not two. A register that answered with the codes the
        specification defines is on or off; one that answered 0xFFFF, or that
        has never been read, is unknown — and reporting that as "off" would
        tell a user a feature is disabled when their model simply does not
        have it.
        """
        raw = self.native_value_source
        if raw is None:
            return None
        value = int(raw)
        if value == self.entity_description.on_value:
            return True
        if (
            value == self.entity_description.off_value
            or value in self.entity_description.also_off
        ):
            return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the flag."""
        await self._async_write(
            (self.entity_description.field, self.entity_description.on_value)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the flag."""
        await self._async_write(
            (self.entity_description.field, self.entity_description.off_value)
        )
