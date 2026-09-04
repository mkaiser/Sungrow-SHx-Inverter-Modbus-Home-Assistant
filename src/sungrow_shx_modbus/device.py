"""The top-level Sungrow SHx inverter object.

Consumers construct one of these from a ``ModbusUnit`` and then read plain
Python attributes; nothing here knows about Home Assistant.
"""

from __future__ import annotations

import logging

from modbus_connection import ModbusConnectionError, ModbusError, ModbusUnit

from .components import InverterIdentity, InverterReadings
from .const import model_for
from .model import UpdateReport

_LOGGER = logging.getLogger(__name__)

#: Components refreshed by the fast poll.
READINGS_COMPONENTS: tuple[str, ...] = ("readings",)


class SungrowInverter:
    """A Sungrow SHx hybrid inverter on one Modbus unit."""

    def __init__(self, unit: ModbusUnit) -> None:
        """Bind the inverter's components to a unit handle."""
        self._unit = unit
        self.identity = InverterIdentity(unit)
        self.readings = InverterReadings(unit)

    @property
    def serial_number(self) -> str | None:
        """Serial number, or None until the identity has been read."""
        return self.identity.serial_number or None

    @property
    def device_type_code(self) -> int | None:
        """Raw model code, or None until the identity has been read."""
        return self.identity.device_type_code

    @property
    def model(self) -> str | None:
        """Model name, or None if the code is unknown to this library."""
        return model_for(self.device_type_code)

    @property
    def readings_components(self) -> tuple[str, ...]:
        """Component names covered by :meth:`async_update_readings`."""
        return READINGS_COMPONENTS

    async def async_update_identity(self) -> None:
        """Read the identity block. Raises on failure; the caller decides."""
        await self.identity.async_update()

    async def async_update_readings(self) -> UpdateReport:
        """Poll the live measurements."""
        return await self._async_update_components(READINGS_COMPONENTS)

    async def async_update(self) -> UpdateReport:
        """Read identity and readings in one go, as a config flow probe does."""
        await self.async_update_identity()
        return await self.async_update_readings()

    async def _async_update_components(self, names: tuple[str, ...]) -> UpdateReport:
        """Refresh each named component, collecting per-component failures.

        A dead link fails the whole poll, because retrying the remaining
        components would only multiply the timeout. Anything else is recorded
        against the one component that raised it and the poll carries on.
        """
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for name in names:
            try:
                await getattr(self, name).async_update()
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                _LOGGER.debug("%s failed to refresh: %s", name, err)
                failed[name] = err
            else:
                updated.add(name)
        return UpdateReport(frozenset(updated), failed)
