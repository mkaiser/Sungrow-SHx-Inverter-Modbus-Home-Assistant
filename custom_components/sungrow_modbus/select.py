"""Enumerations the user can change: EMS mode, forced charge, load control.

These are the settings the YAML package guards behind a dashboard toggle it
calls danger mode, and the reason is not that a wrong value damages anything
— it is that a wrong value changes what the whole inverter does. An inverter
left in External EMS mode with no EMS on the other end, or in forced
discharge, is a house that behaves oddly until somebody works out why.

So two things are deliberate here. The mapping between what the interface
shows and what goes in the register is **one table**, generated, because two
tables — one for reading and one for writing — eventually disagree. And a
register holding a value the table does not know reports `None` rather than
the nearest guess: the YAML falls back to a default option, which shows the
user a mode their inverter is not in.
"""

from __future__ import annotations

from modbus_connection import ModbusError

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowSelectDescription
from .select_descriptions import SELECT_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the modes this device actually has."""
    runtime_data = entry.runtime_data
    async_add_entities(
        SungrowSelect(runtime_data, description)
        for description in SELECT_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowSelect(SungrowEntity, SelectEntity):
    """One enumeration register, read and written by the same entity."""

    entity_description: SungrowSelectDescription

    @property
    def current_option(self) -> str | None:
        """Return the option the register currently holds, if it is one.

        An unrecognised value returns `None`, which shows as unknown. The
        YAML package falls back to the default option instead, which tells the
        user the inverter is in a mode it is not in — and hides the fact that
        Sungrow has added a value nobody has written down yet.
        """
        raw = self.native_value_source
        if raw is None:
            return None
        value = int(raw)
        for option, candidate in self.entity_description.values.items():
            if candidate == value:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        """Write the value this option maps to, then read the register back."""
        description = self.entity_description
        value = description.values[option]
        component = self.coordinator.device.component(description.component)
        try:
            await component.write(description.field, value)
        except ModbusError as err:
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: {err}"
            ) from err
        # Immediate, not debounced: see the note in number.py. A ten-second
        # cooldown between an explicit change and its confirmation is the
        # readback problem this integration exists to have fixed.
        await self.coordinator.async_refresh()
