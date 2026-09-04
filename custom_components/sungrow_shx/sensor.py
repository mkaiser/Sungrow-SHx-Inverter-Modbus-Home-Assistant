"""Sensor platform for the Sungrow SHx integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowEntityDescription

# The coordinator does the polling; entities never talk to the inverter.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SungrowSensorDescription(SungrowEntityDescription, SensorEntityDescription):
    """Describe a Sungrow sensor."""


SENSOR_DESCRIPTIONS: tuple[SungrowSensorDescription, ...] = (
    SungrowSensorDescription(
        key="total_dc_power",
        component="readings",
        field="total_dc_power",
        translation_key="total_dc_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sungrow SHx sensors."""
    runtime_data = entry.runtime_data
    served = runtime_data.served_components
    async_add_entities(
        SungrowSensor(runtime_data, description)
        for description in SENSOR_DESCRIPTIONS
        if description.component in served
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
