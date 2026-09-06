"""Sensor platform for the Sungrow Modbus integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .derived_descriptions import DERIVED_SENSORS
from .entity import SungrowEntity, SungrowSensorDescription
from .sensor_descriptions import SENSOR_DESCRIPTIONS

# The coordinator does the polling; entities never talk to the inverter.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sungrow sensors."""
    runtime_data = entry.runtime_data
    async_add_entities(
        SungrowSensor(runtime_data, description)
        for description in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)
        if runtime_data.serves(description)
    )


class SungrowSensor(SungrowEntity, SensorEntity):
    """A sensor reading one field off the inverter."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the decoded register value."""
        value = self.native_value_source
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float, str)):
            return value
        return None
