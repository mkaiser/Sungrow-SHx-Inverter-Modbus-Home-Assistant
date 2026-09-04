"""Data update coordinator for the Sungrow SHx integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging

from modbus_connection import ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from sungrow_shx_modbus import MANUFACTURER, SungrowInverter, UpdateReport

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SungrowDataUpdateCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Poll one group of the inverter's registers."""

    config_entry: SungrowConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        device: SungrowInverter,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=interval,
        )
        self.device = device
        self._poll = poll
        self._failing: set[str] = set()

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Describe the inverter for the device registry."""
        serial = self.device.serial_number
        assert serial is not None
        identity = self.device.identity
        return dr.DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            model=self.device.model,
            serial_number=serial,
            sw_version=identity.arm_software or None,
        )

    async def _async_update_data(self) -> UpdateReport:
        """Poll the inverter."""
        try:
            report = await self._poll()
        except ModbusError as err:
            # A dead link or a timeout on the whole device lands here; a
            # single block that failed while the device is alive is reported
            # per component instead.
            raise UpdateFailed(f"Error communicating with the inverter: {err}") from err

        self._log_transitions(report)
        if not report.updated:
            raise UpdateFailed("No register block answered")
        return report

    def _log_transitions(self, report: UpdateReport) -> None:
        """Log a component going quiet, and coming back, exactly once."""
        for name, cause in report.failed.items():
            if name not in self._failing:
                self._failing.add(name)
                _LOGGER.warning(
                    "%s: %s did not answer and keeps its previous values: %s",
                    self.name,
                    name,
                    cause,
                )
        for name in report.updated & self._failing:
            self._failing.discard(name)
            _LOGGER.info("%s: %s is answering again", self.name, name)


@dataclass
class SungrowRuntimeData:
    """Everything a platform needs to build its entities."""

    readings: SungrowDataUpdateCoordinator

    @property
    def served_components(self) -> frozenset[str]:
        """Component names this entry polls, answered or not."""
        return frozenset(self.readings.device.readings_components)

    def coordinator_for(self, component: str) -> SungrowDataUpdateCoordinator:
        """Return the coordinator that owns a component's data."""
        return self.readings


type SungrowConfigEntry = ConfigEntry[SungrowRuntimeData]
