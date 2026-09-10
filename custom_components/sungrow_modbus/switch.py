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

from modbus_connection import ModbusError

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowSwitchDescription
from .switch_descriptions import SWITCH_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mode flags this device actually has."""
    runtime_data = entry.runtime_data
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
        if value == self.entity_description.off_value:
            return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the flag."""
        await self._async_write(self.entity_description.on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the flag."""
        await self._async_write(self.entity_description.off_value)

    async def _async_write(self, value: int) -> None:
        """Write one of the two codes, then read the register back at once."""
        component = self.coordinator.device.component(self.entity_description.component)
        try:
            await component.write(self.entity_description.field, value)
        except ModbusError as err:
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: {err}"
            ) from err
        # `async_refresh`, not `async_request_refresh`. The latter goes
        # through the coordinator's debouncer, which has a **10 second
        # cooldown** -- so a second change inside that window is written to
        # the register and never read back, and the interface shows the
        # previous value for up to ten seconds. That is precisely the bug the
        # YAML package's `homeassistant.update_entity` calls existed to work
        # around, and it would have shipped as a regression.
        #
        # The debouncer is there to coalesce storms of *automatic* refresh
        # requests. An explicit user action is not a storm.
        await self.coordinator.async_refresh()
