"""Data update coordinator for the Sungrow Modbus integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging

from modbus_connection import ModbusConnectionError, ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from sungrow_modbus import (
    COMPONENTS,
    MANUFACTURER,
    TIERS,
    Capability,
    SungrowInverter,
    UpdateReport,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

#: Register field name to the component holding it. Field names are unique
#: across components, which the library's tests assert.
FIELD_COMPONENTS: dict[str, str] = {
    name: attribute
    for attribute, component in COMPONENTS.items()
    for name in vars(component)
    if not name.startswith("_") and name not in {"register_space", "declared_fields"}
}

#: Component to how often it is polled, so the fastest can be picked.
COMPONENT_INTERVALS: dict[str, int] = {
    component: interval
    for interval, components in TIERS.items()
    for component in components
}


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
        except ModbusConnectionError as err:
            # Say what it usually is. A Sungrow accepts very few simultaneous
            # Modbus sessions, so by far the most common cause of a dropped
            # connection is a second client -- the YAML package still running,
            # another Home Assistant, EVCC, a logger -- rather than a fault.
            # The bare message ("Connection lost before response was
            # received") sends people looking at their network instead, which
            # is exactly what happened to the maintainer.
            raise UpdateFailed(
                f"Lost the connection to the inverter: {err}. A Sungrow "
                "inverter accepts very few Modbus connections at once, so "
                "check whether something else is polling it -- the "
                "modbus_sungrow.yaml package, another Home Assistant, or "
                "another tool."
            ) from err
        except ModbusError as err:
            # A timeout on the whole device lands here; a single block that
            # failed while the device is alive is reported per component
            # instead.
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
    """Everything a platform needs to build its entities.

    One coordinator per poll interval, so a 5-second reading is not dragged
    along by 38 slow-moving totals. Entities look theirs up by the component
    they read, which is the only thing an entity description knows.
    """

    coordinators: dict[str, SungrowDataUpdateCoordinator]
    """Component attribute name to the coordinator that polls it."""

    capabilities: frozenset[Capability] = frozenset()
    """What this device turned out to have, probed once after the first poll."""

    @property
    def served_components(self) -> frozenset[str]:
        """Component names this entry polls, answered or not."""
        return frozenset(self.coordinators)

    def coordinator_for(self, component: str) -> SungrowDataUpdateCoordinator:
        """Return the coordinator that owns a component's data."""
        return self.coordinators[component]

    def serves(self, description: object) -> bool:
        """Whether every component this description needs is being polled."""
        required = getattr(description, "requires", None)
        if required is not None and required not in self.capabilities:
            return False
        depends = getattr(description, "depends_on", ())
        if depends:
            return all(self.component_of(f) in self.coordinators for f in depends)
        return getattr(description, "component", None) in self.coordinators

    def component_of(self, field: str) -> str:
        """Return the component a register field lives in."""
        return FIELD_COMPONENTS[field]

    def fastest_component(self, fields: tuple[str, ...]) -> str:
        """Return the component polled most often among these fields.

        A derived value is written when its coordinator fires, so it follows
        the quickest thing it reads — otherwise it would lag the raw sensors
        it is computed from.
        """
        components = {self.component_of(field) for field in fields}
        return min(components, key=lambda c: COMPONENT_INTERVALS[c])


type SungrowConfigEntry = ConfigEntry[SungrowRuntimeData]
