"""An SG string inverter as a device: the entry's own inverter, read only.

Not a sub-device: where input 5000 names an SG (`identity.inverter_kind`), it
takes the place `SungrowInverter` takes for a hybrid, on unit 1 of the
entry's endpoint. It reads the identity block both inverters share
(`identity.InverterIdentity`) as the hybrid does, once and outside the tiers,
so the device registry is built from it alike; the rest is `MappedDevice`.

**The hybrid's tier names**, so an entry's interval options mean the same on
both: `realtime` moves second to second; the meter and the trackers past
three move with it but cost a read each, so they go on `fast` and `medium`;
the precise totals and the power limitation as set change rarely
(`slowest`).

**A lost connection is the hybrid's case too**: one retry per component,
then the poll fails as a whole, because as an entry's own inverter "the
link is gone" is the one thing worth telling apart from a refused block.
"""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import TYPE_CHECKING

from modbus_connection import ModbusConnectionError, ModbusError

from ..device import MappedDevice
from ..identity import InverterIdentity
from ..model import UpdateReport
from .registers import (
    COMPONENTS,
    SgMeter,
    SgPowerLimit,
    SgPrecision,
    SgRealtime,
    SgTrackers,
    model_for,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)

#: Which components each tier polls, keyed as `hybrid_inverter`'s are.
TIER_COMPONENTS: dict[str, tuple[str, ...]] = {
    "realtime": ("sg_realtime",),
    "fast": ("sg_meter",),
    "medium": ("sg_trackers",),
    "slowest": ("sg_precision", "sg_power_limit"),
}


class SungrowStringInverter(MappedDevice):
    """An SG on its own Modbus unit, normally 1."""

    # Declared for `mypy --strict`, as on `SungrowWallbox`.
    sg_realtime: SgRealtime
    sg_meter: SgMeter
    sg_trackers: SgTrackers
    sg_precision: SgPrecision
    sg_power_limit: SgPowerLimit

    def __init__(self, unit: ModbusUnit, unit_id: int = 1) -> None:
        """Bind the identity and every component to a unit handle."""
        super().__init__(unit, COMPONENTS, unit_id)
        self.identity = InverterIdentity(unit)

    @property
    def serial_number(self) -> str | None:
        """Serial number, or None until the identity has been read."""
        return self.identity.serial_number or None

    @property
    def device_type_code(self) -> int | None:
        """Raw model code, or None until the identity has been read."""
        return self.identity.device_type_code

    @property
    def output_type(self) -> int | None:
        """0 single phase, 1 three-phase 3P4L, 2 three-phase 3P3L, or None."""
        return self.identity.output_type

    @property
    def model(self) -> str | None:
        """Name the SG from input 5000, or None for a code nobody mapped."""
        return model_for(self.device_type_code)

    async def async_update_identity(self) -> None:
        """Read the identity block. Raises on failure; the caller decides."""
        await self.identity.async_update()

    async def async_update_tier(self, tier: str) -> UpdateReport:
        """Poll every component belonging to one tier."""
        return await self._async_update_components(TIER_COMPONENTS[tier])

    async def async_update(self, only: tuple[str, ...] | None = None) -> UpdateReport:
        """Refresh the components in `only`, each failing alone.

        Without `only`, the identity first, as a config flow probe reads a
        hybrid; a refused identity is a failure like any component's.
        """
        report = UpdateReport()
        if only is None:
            try:
                await self.async_update_identity()
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                report = UpdateReport(failed={"identity": err})
            else:
                report = UpdateReport(updated=frozenset({"identity"}))
        return report | await self._async_update_components(only)

    async def _async_update_components(
        self, attributes: Iterable[str] | None = None
    ) -> UpdateReport:
        """Refresh each component; a refusal costs it, a lost link the poll.

        One retry on a lost connection first, as on the hybrid: a session a
        Sungrow closed is not always a dead link, and the retry reconnects.
        """
        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for attribute in self._components if attributes is None else attributes:
            component = self.component(attribute)
            try:
                try:
                    await component.async_update()
                except ModbusConnectionError as err:
                    _LOGGER.debug("%s lost the link, retrying: %s", attribute, err)
                    await component.async_update()
            except ModbusConnectionError:
                raise
            except ModbusError as err:
                failed[attribute] = err
            else:
                updated.add(attribute)
        return UpdateReport(updated=frozenset(updated), failed=failed)
