"""Times of day the inverter holds as two registers, an hour and a minute.

The forced-charging schedule (V1.1.16, registers 33210-33213 and 33215-33218)
is the first. Shown as one `time` entity per pair, so a window reads as
02:00-05:00 rather than as four numbers an automation has to keep in step.
"""

from __future__ import annotations

from datetime import time

from modbus_connection import ModbusError

from homeassistant.components.time import TimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from sungrow_modbus import present

from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowTimeDescription, write_failed
from .time_descriptions import TIME_DESCRIPTIONS

# One write at a time: see `switch.py`. A time is two writes, and two of them
# interleaved would leave each window half moved.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the times this device actually has."""
    runtime_data = entry.runtime_data
    async_add_entities(
        SungrowTime(runtime_data, description)
        for description in TIME_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowTime(SungrowEntity, TimeEntity):
    """One time of day, read and written by the same entity."""

    entity_description: SungrowTimeDescription

    @property
    def native_value(self) -> time | None:
        """Return the time, or None where either register is not a time.

        The specification gives 0-23 for the hour and 0-59 for the minute.
        Anything else, 0xFFFF included, is not a time of day, and showing a
        nearby one instead would be a guess about what the inverter does.
        """
        hour = self.native_value_source
        component = self.coordinator.device.component(self.entity_description.component)
        minute = present(getattr(component, self.entity_description.minute_field))
        if hour is None or minute is None:
            return None
        hour, minute = int(hour), int(minute)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return time(hour, minute)

    async def async_set_value(self, value: time) -> None:
        """Write the hour, then the minute, then read both back at once."""
        description = self.entity_description
        component = self.coordinator.device.component(description.component)
        try:
            await component.write(description.field, value.hour)
            await component.write(description.minute_field, value.minute)
        except ModbusError as err:
            raise write_failed(self.entity_id, err) from err
        # Not debounced, for the reason `switch.py` gives.
        await self.coordinator.async_refresh()
