"""Select platform for the Sungrow SHx Inverter integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptions import SELECTS, SelectDescription
from .entity import SungrowEntity

if TYPE_CHECKING:
    from . import SungrowConfigEntry

_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sungrow SHx select entities from a config entry."""
    coordinator = entry.runtime_data
    unsupported = coordinator.unsupported_keys
    entities = [
        SungrowSelect(coordinator, entry, desc)
        for desc in SELECTS
        if desc.source_key not in unsupported
    ]
    async_add_entities(entities)


class SungrowSelect(SungrowEntity, SelectEntity):
    """Select whose current value is the option whose write-value matches the source register."""

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: SelectDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description
        self._attr_options = list(description.options)
        # value -> option label, so register-value lookups are O(1).
        self._reverse: dict[int, str] = {
            action.value: option
            for option, action in description.option_writes.items()
        }

    @property
    def current_option(self) -> str | None:
        raw = self.coordinator.decoded.get(self._description.source_key)
        if raw is None:
            return None
        return self._reverse.get(int(raw))

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.coordinator.decoded.get(self._description.source_key) is not None

    async def async_select_option(self, option: str) -> None:
        """Write the register value that corresponds to ``option``."""
        action = self._description.option_writes.get(option)
        if action is None:
            _LOGGER.warning("Unknown option %r for %s", option, self._description.key)
            return
        await self.coordinator.client.write_register(
            action.address,
            action.value,
            slave=self.coordinator.inverter_slave,
        )
        await self.coordinator.async_request_refresh()
