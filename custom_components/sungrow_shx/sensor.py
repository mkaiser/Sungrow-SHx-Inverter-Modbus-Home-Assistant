"""Sensor platform for the Sungrow SHx Inverter integration.

Two kinds of sensors are exposed:

* :class:`SungrowModbusSensor` — a straight decoded read from a modbus
  register, described by :class:`descriptions.ModbusSensorDescription`.
* :class:`SungrowComputedSensor` — a derived sensor whose value is a
  plain-Python function of other decoded values, described by
  :class:`descriptions.ComputedSensorDescription`. The compute callable
  is invoked by the coordinator after every refresh so the entity just
  reads a key out of ``coordinator.decoded`` like any modbus sensor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptions import (
    COMPUTED_SENSORS,
    MODBUS_SENSORS,
    ComputedSensorDescription,
    ModbusSensorDescription,
)
from .entity import SungrowEntity

if TYPE_CHECKING:
    from . import SungrowConfigEntry


def _coerce_device_class(value: str | None) -> SensorDeviceClass | None:
    if value is None:
        return None
    try:
        return SensorDeviceClass(value)
    except ValueError:
        return None


def _coerce_state_class(value: str | None) -> SensorStateClass | None:
    if value is None:
        return None
    try:
        return SensorStateClass(value)
    except ValueError:
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sungrow SHx sensors from a config entry."""
    coordinator = entry.runtime_data
    unsupported = coordinator.unsupported_keys
    entities: list[SensorEntity] = []
    for desc in MODBUS_SENSORS:
        if desc.key in unsupported:
            continue
        entities.append(SungrowModbusSensor(coordinator, entry, desc))
    for desc in COMPUTED_SENSORS:
        if any(k in unsupported for k in desc.requires):
            continue
        entities.append(SungrowComputedSensor(coordinator, entry, desc))
    async_add_entities(entities)


class SungrowModbusSensor(SungrowEntity, SensorEntity):
    """Sensor backed by a decoded modbus register."""

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: ModbusSensorDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = _coerce_device_class(description.device_class)
        self._attr_state_class = _coerce_state_class(description.state_class)
        if description.precision is not None:
            self._attr_suggested_display_precision = description.precision

    @property
    def native_value(self) -> Any:
        return self.coordinator.decoded.get(self._description.key)


class SungrowComputedSensor(SungrowEntity, SensorEntity):
    """Sensor whose value is computed by the coordinator from decoded data."""

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: ComputedSensorDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = _coerce_device_class(description.device_class)
        self._attr_state_class = _coerce_state_class(description.state_class)

    @property
    def native_value(self) -> Any:
        return self.coordinator.decoded.get(self._description.key)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.decoded.get(self._description.key) is not None
