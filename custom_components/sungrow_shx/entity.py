"""Shared base entity for the Sungrow SHx integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN, MANUFACTURER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import SungrowModbusCoordinator


class SungrowEntity(CoordinatorEntity["SungrowModbusCoordinator"]):
    """Base class that wires up device info and the name/id attributes."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SungrowModbusCoordinator,
        entry: ConfigEntry,
        *,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.serial}_{key}"
        host = entry.data.get(CONF_HOST)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial)},
            manufacturer=MANUFACTURER,
            model=coordinator.model,
            sw_version=coordinator.firmware,
            name=entry.title,
            configuration_url=f"http://{host}" if host else None,
        )
