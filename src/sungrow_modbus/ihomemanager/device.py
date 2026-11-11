"""An iHomeManager as a device: its own entry's readings, read only.

Unit 247 on its own address, one connection per port (`registers.PORTS`).
`MappedDevice` holds the map; this adds the tiers and the poll.

**The hybrid's tier names**, so an entry's interval options mean the same on
every kind: the site's live flows and the meters on `fast`; the energy
counters and the settings, which an owner or iSolarCloud changes, on
`medium`; what it is and its software on `slowest`.

**What gets an entity is decided after the first poll** (`serves`): a field
that read nothing -- refused, or the document's "unavailable" -- gets none,
rather than one unavailable forever.

**A lost connection is the poll's**, as on an SG: one retry per component,
then the poll fails as a whole; a refused block costs only its component.
"""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import TYPE_CHECKING

from modbus_connection import ModbusConnectionError, ModbusError

from ..device import MappedDevice
from ..model import UpdateReport
from .registers import (
    COMPONENTS,
    UNIT,
    IHomeManagerCharger,
    IHomeManagerEnergy,
    IHomeManagerIdentity,
    IHomeManagerMeters,
    IHomeManagerPhaseVoltages,
    IHomeManagerSettings,
    IHomeManagerSoftware,
    IHomeManagerSystem,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

_LOGGER = logging.getLogger(__name__)

#: Which components each tier polls, keyed as `hybrid_inverter`'s are.
TIER_COMPONENTS: dict[str, tuple[str, ...]] = {
    "fast": ("system", "meters", "charger", "phase_voltages"),
    "medium": ("energy", "settings"),
    "slowest": ("identity", "software"),
}


class SungrowIHomeManager(MappedDevice):
    """An iHomeManager at unit 247."""

    # Declared for `mypy --strict`, as on `SungrowStringInverter`.
    identity: IHomeManagerIdentity
    system: IHomeManagerSystem
    energy: IHomeManagerEnergy
    software: IHomeManagerSoftware
    meters: IHomeManagerMeters
    charger: IHomeManagerCharger
    phase_voltages: IHomeManagerPhaseVoltages
    settings: IHomeManagerSettings

    def __init__(self, unit: ModbusUnit, unit_id: int = UNIT) -> None:
        """Bind every component to a unit handle."""
        super().__init__(unit, COMPONENTS, unit_id)

    def serves(self, field: str) -> bool:
        """Whether a field gets an entity: it read a value."""
        return self.field(field) is not None

    @property
    def software_version(self) -> str | None:
        """The application software version, or None until it has been read."""
        value = self.field("application_software_version")
        return str(value) if value else None

    async def async_update_tier(self, tier: str) -> UpdateReport:
        """Poll every component belonging to one tier."""
        return await self._async_update_components(TIER_COMPONENTS[tier])

    async def _async_update_components(
        self, attributes: Iterable[str] | None = None
    ) -> UpdateReport:
        """Refresh each component; a refusal costs it, a lost link the poll.

        One retry on a lost connection first: a session the device closed is
        not always a dead link, and the retry reconnects.
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
