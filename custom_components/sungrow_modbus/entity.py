"""Base entity for the Sungrow Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from sungrow_modbus import Capability

from .coordinator import SungrowDataUpdateCoordinator, SungrowRuntimeData


@dataclass(frozen=True, kw_only=True)
class SungrowEntityDescription(EntityDescription):
    """Describe a Sungrow entity."""

    component: str
    """Attribute name of the component on SungrowInverter, for example readings."""

    field: str
    """Attribute name of the field on that component."""

    requires: Capability | None = None
    """A capability this entity needs, or None if every device has it.

    An entity is not created at all when its capability is absent, rather
    than created and left permanently unavailable. That is the difference
    between an integration that fits the hardware and the pile of dead
    entities legacy/doc/cleanup_entities.md exists to help people delete.
    """

    depends_on: tuple[str, ...] = ()
    """Register fields a derived value reads.

    A derived value is computed on read, so it is never stale in itself — but
    something has to decide when Home Assistant writes the new state. That is
    the **fastest** tier among these fields: attached to a slower one, the
    derived entity would visibly lag the raw sensors it is computed from,
    which is the one thing the template sensors it replaces never did.

    It also decides availability: a derived value is unavailable when any
    component it reads is.
    """

    legacy_name: str | None = None
    """The name the YAML package used for this entity.

    Legacy mode sets it as the entity's name, which is what makes the
    entity_id come out byte for byte the same — Home Assistant derives the
    object id from the name, and `_attr_name` short-circuits translation, so
    it holds in every interface language.
    """


@dataclass(frozen=True, kw_only=True)
class SungrowSensorDescription(SungrowEntityDescription, SensorEntityDescription):
    """Describe a Sungrow sensor."""


@dataclass(frozen=True, kw_only=True)
class SungrowBinarySensorDescription(
    SungrowEntityDescription, BinarySensorEntityDescription
):
    """Describe a Sungrow binary sensor."""


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
        # A derived value has no component of its own, so it is written by
        # the fastest tier it reads — otherwise it would visibly lag the raw
        # sensors it is computed from.
        if entity_description.depends_on:
            polled = runtime_data.fastest_component(entity_description.depends_on)
        else:
            polled = entity_description.component
        super().__init__(runtime_data.coordinator_for(polled))
        self._runtime_data = runtime_data
        self.entity_description = entity_description
        serial = self.coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{entity_description.key}"
        self._attr_device_info = self.coordinator.device_info

    @property
    def native_value_source(self) -> object:
        """Return the decoded field value, or None if it was never read."""
        device = self.coordinator.device
        component = (
            device.derived
            if self.entity_description.component == "derived"
            else device.component(self.entity_description.component)
        )
        return getattr(component, self.entity_description.field)

    @property
    def available(self) -> bool:
        """Whether every component this entity reads answered its last poll."""
        if not super().available:
            return False
        for component in self._sources:
            coordinator = self._runtime_data.coordinator_for(component)
            if coordinator.data is None or component in coordinator.data.failed:
                return False
        return True

    @property
    def _sources(self) -> set[str]:
        """Components this entity's value depends on."""
        description = self.entity_description
        if not description.depends_on:
            return {description.component}
        return {
            self._runtime_data.component_of(field) for field in description.depends_on
        }
