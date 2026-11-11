"""An iHomeManager's readings: its coordinators, and the sensors they feed.

An iHomeManager entry was its diagnosis and nothing else; it now shows what
the device reports too, read only (`ihomemanager_descriptions.py` says what,
and why some fields are left out). The library's `SungrowIHomeManager` polls,
one coordinator per tier, as on an SG.

**The device has no serial** (`sungrow_modbus.ihomemanager.registers`), so
its entities' unique ids are the entry's unique id (kind, host and port), as
its device's identifier already is.

**Each of its ports takes one connection** (V1.0.2, table 2). A diagnosis
held its port for a minute; polling holds it while the entry is loaded. Any
other client of the iHomeManager -- evcc, a second Home Assistant -- needs
one of the other two ports.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from modbus_connection import ModbusConnectionError, ModbusError, ModbusExceptionError

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from sungrow_modbus.ihomemanager import SungrowIHomeManager
from sungrow_modbus.model import UpdateReport

from .const import DOMAIN
from .coordinator import PausableCoordinator
from .entity import EnglishEntityId, SungrowSensorDescription, as_reading

if TYPE_CHECKING:
    from .coordinator import SungrowConfigEntry

_LOGGER = logging.getLogger(__name__)


class SungrowIHomeManagerCoordinator(
    PausableCoordinator, DataUpdateCoordinator[UpdateReport]
):
    """Poll one tier of an iHomeManager's registers."""

    config_entry: SungrowConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        device: SungrowIHomeManager,
        tier: str,
        interval: timedelta,
        device_info: dr.DeviceInfo,
    ) -> None:
        """Initialize the coordinator for one tier."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.title} {tier}",
            update_interval=interval,
        )
        self.device = device
        self.tier = tier
        self.device_info = device_info

    async def _async_update_data(self) -> UpdateReport:
        """Poll the tier, unless a diagnosis has asked for the link."""
        if (paused := self._skip_while_paused()) is not None:
            return paused
        try:
            report = await self.device.async_update_tier(self.tier)
        except ModbusConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="connection_lost",
                translation_placeholders={"error": str(err)},
            ) from err
        except ModbusError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        # A refused block is the device answering: its entities do not
        # exist, and the entry stays up. Only a tier that heard nothing fails.
        if not report.updated and not all(
            isinstance(err, ModbusExceptionError) for err in report.failed.values()
        ):
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="no_block_answered",
            )
        return report


class SungrowIHomeManagerSensor(
    EnglishEntityId,
    CoordinatorEntity[SungrowIHomeManagerCoordinator],
    SensorEntity,
):
    """A sensor reading one value an iHomeManager reports."""

    _attr_has_entity_name = True
    entity_description: SungrowSensorDescription

    def __init__(
        self,
        coordinator: SungrowIHomeManagerCoordinator,
        entity_description: SungrowSensorDescription,
        unique_prefix: str,
    ) -> None:
        """Initialize the sensor on the iHomeManager's device."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = f"{unique_prefix}_{entity_description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Whether the block this entity reads answered its last poll."""
        if not super().available:
            return False
        report = self.coordinator.data
        if report is None:
            return False
        return self.entity_description.component not in report.failed

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the device has none."""
        return as_reading(self.coordinator.device.field(self.entity_description.field))
