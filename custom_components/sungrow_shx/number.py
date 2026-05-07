"""Number platform for the Sungrow SHx Inverter integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_BATTERY_MAX_POWER
from .descriptions import NUMBERS, NumberDescription
from .entity import SungrowEntity

if TYPE_CHECKING:
    from . import SungrowConfigEntry

_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sungrow SHx number entities from a config entry."""
    coordinator = entry.runtime_data
    unsupported = coordinator.unsupported_keys
    entities = [
        SungrowNumber(coordinator, entry, desc)
        for desc in NUMBERS
        if desc.source_key not in unsupported
    ]
    async_add_entities(entities)


class SungrowNumber(SungrowEntity, NumberEntity):
    """Writable numeric setpoint backed by a holding register."""

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: NumberDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description
        self._attr_native_min_value = description.min_value
        self._attr_native_step = description.step
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_max_value = self._resolve_max(description, entry)
        # Family-specific scale override (e.g. SH-RT writes 0.1-W units
        # while RS writes 1-W units for the export power limit).
        self._set_scale = description.set_scale
        if (
            description.family_scale_overrides
            and coordinator.family in description.family_scale_overrides
        ):
            self._set_scale = description.family_scale_overrides[coordinator.family]

    def _resolve_max(
        self, description: NumberDescription, entry: SungrowConfigEntry
    ) -> float:
        """Compute an effective max_value at setup.

        Priority: ``max_source_key`` (decoded register, e.g. inverter
        rated output) → ``max_from_config`` (entry data, e.g. user-set
        battery_max_power) → declared ``max_value`` → fallback to the
        battery_max_power default if max_value is 0/unset.
        """
        if description.max_source_key:
            value = self.coordinator.decoded.get(description.max_source_key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        if description.max_from_config:
            value = entry.data.get(description.max_from_config)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        if description.max_value and description.max_value > 0:
            return description.max_value
        return float(DEFAULT_BATTERY_MAX_POWER)

    @property
    def native_value(self) -> float | None:
        return self.coordinator.decoded.get(self._description.source_key)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.decoded.get(self._description.source_key) is not None

    async def async_set_native_value(self, value: float) -> None:
        """Write the new value back to the holding register."""
        raw = int(round(value / self._set_scale))
        await self.coordinator.client.write_register(
            self._description.set_address,
            raw,
            slave=self.coordinator.inverter_slave,
        )
        await self.coordinator.async_request_refresh()
