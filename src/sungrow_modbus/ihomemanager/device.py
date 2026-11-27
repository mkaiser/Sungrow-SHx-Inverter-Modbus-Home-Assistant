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

**A lost connection is the poll's** (`lost_link_fails_the_poll`), as on an
SG: one retry per component, then the poll fails as a whole; a refused block
costs only its component.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    lost_link_fails_the_poll = True

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
