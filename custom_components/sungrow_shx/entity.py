"""Base entity for the Sungrow SHx integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SungrowDataUpdateCoordinator, SungrowRuntimeData


@dataclass(frozen=True, kw_only=True)
class SungrowEntityDescription(EntityDescription):
    """Describe a Sungrow entity."""

    component: str
    """Attribute name of the component on SungrowInverter, for example readings."""

    field: str
    """Attribute name of the field on that component."""


class SungrowEntity(CoordinatorEntity[SungrowDataUpdateCoordinator]):
    """Base entity backed by one field of one component."""

    _attr_has_entity_name = True
    entity_description: SungrowEntityDescription

    def __init__(
        self,
        runtime_data: SungrowRuntimeData,
        entity_description: SungrowEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(runtime_data.coordinator_for(entity_description.component))
        self.entity_description = entity_description
        serial = self.coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{entity_description.key}"
        self._attr_device_info = self.coordinator.device_info

    @property
    def native_value_source(self) -> object:
        """Return the decoded field value, or None if it was never read."""
        component = getattr(self.coordinator.device, self.entity_description.component)
        return getattr(component, self.entity_description.field)

    @property
    def available(self) -> bool:
        """Whether this entity's component answered the most recent poll."""
        if not super().available:
            return False
        return self.entity_description.component not in self.coordinator.data.failed
