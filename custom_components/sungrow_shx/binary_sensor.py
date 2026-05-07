"""Binary sensor platform for the Sungrow SHx Inverter integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptions import COMPUTED_BINARY_SENSORS, ComputedBinarySensorDescription
from .entity import SungrowEntity

if TYPE_CHECKING:
    from . import SungrowConfigEntry


def _coerce_device_class(value: str | None) -> BinarySensorDeviceClass | None:
    if value is None:
        return None
    try:
        return BinarySensorDeviceClass(value)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sungrow SHx binary sensors from a config entry."""
    coordinator = entry.runtime_data
    unsupported = coordinator.unsupported_keys
    entities = [
        SungrowComputedBinarySensor(coordinator, entry, desc)
        for desc in COMPUTED_BINARY_SENSORS
        if not any(k in unsupported for k in desc.requires)
    ]
    async_add_entities(entities)


class SungrowComputedBinarySensor(SungrowEntity, BinarySensorEntity):
    """Binary sensor whose value is computed by the coordinator."""

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: ComputedBinarySensorDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description
        self._attr_device_class = _coerce_device_class(description.device_class)

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.decoded.get(self._description.key)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.decoded.get(self._description.key) is not None
