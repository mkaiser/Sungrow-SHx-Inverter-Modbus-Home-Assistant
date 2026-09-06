"""Binary sensor platform: the power flow status bits.

The inverter reports what is flowing where as bits of one register, which the
YAML package split into seven binary sensors. They are all computed from the
same reading, so they share a coordinator and go unavailable together.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SungrowConfigEntry
from .derived_descriptions import DERIVED_BINARY_SENSORS
from .entity import SungrowBinarySensorDescription, SungrowEntity

# The coordinator does the polling; entities never talk to the inverter.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sungrow binary sensors."""
    runtime_data = entry.runtime_data
    async_add_entities(
        SungrowBinarySensor(runtime_data, description)
        for description in DERIVED_BINARY_SENSORS
        if runtime_data.serves(description)
    )


class SungrowBinarySensor(SungrowEntity, BinarySensorEntity):
    """One bit of the inverter's power flow status."""

    entity_description: SungrowBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return whether the bit is set, or None if it was never read."""
        value = self.native_value_source
        return None if value is None else bool(value)
