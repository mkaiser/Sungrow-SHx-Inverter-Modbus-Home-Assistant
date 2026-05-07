"""Switch platform for the Sungrow SHx Inverter integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptions import MODBUS_SWITCHES, ModbusSwitchDescription
from .entity import SungrowEntity

if TYPE_CHECKING:
    from . import SungrowConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sungrow SHx switches from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        SungrowModbusSwitch(coordinator, entry, desc) for desc in MODBUS_SWITCHES
    )


class SungrowModbusSwitch(SungrowEntity, SwitchEntity):
    """Modbus-native switch — read state from a verify register, write commands."""

    def __init__(
        self,
        coordinator,
        entry: SungrowConfigEntry,
        description: ModbusSwitchDescription,
    ) -> None:
        super().__init__(
            coordinator, entry, key=description.key, name=description.name
        )
        self._description = description

    def _read_verify_register(self) -> int | None:
        desc = self._description
        addr = desc.verify_address if desc.verify_address is not None else desc.address
        input_type = desc.verify_input_type or "holding"
        raw = self.coordinator.raw_registers(input_type, addr)
        if raw:
            return raw[0] & 0xFFFF
        return None

    @property
    def is_on(self) -> bool | None:
        value = self._read_verify_register()
        if value is None:
            return None
        if value == (self._description.verify_state_on or self._description.command_on):
            return True
        if value == (self._description.verify_state_off or self._description.command_off):
            return False
        return None

    async def _write(self, value: int) -> None:
        await self.coordinator.client.write_register(
            self._description.address,
            value,
            slave=self.coordinator.inverter_slave,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write(self._description.command_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(self._description.command_off)
