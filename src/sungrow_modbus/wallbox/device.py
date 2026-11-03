"""A wallbox as a device, on whichever unit it answers on.

Same arrangement as `battery.device` and for the same reasons: separate
hardware on a different Modbus unit id, reached through the connection that is
already open, and its own device in the registry hung off the inverter.

**Two tiers, not one.** The pack has none because seventeen registers all move
slowly; a wallbox has one block that changes second to second -- power,
current, session energy, charging status -- and three that change when
somebody plugs a car in or reconfigures the unit. Polling those every ten
seconds would read some forty registers nobody is watching, on a link a
Sungrow inverter grants very few sessions on.

**Nothing here writes.** The write table in `scripts/generate/tables/writes.py` is the
only place a writable register is declared and no wallbox register is in it. That
is a decision, not an omission: the registers that would start and stop a
charge are known -- holding 21211 and 21212 -- and starting somebody's car
charging from a stale automation is not a thing to enable on one measurement
of one unit, on a map no manufacturer document covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..device import MappedDevice
from ..model import UpdateReport
from .registers import (
    COMPONENTS,
    WallboxIdentity,
    WallboxLive,
    WallboxRatings,
    WallboxSettings,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: Which components are worth reading often, and which are not.
#:
#: `live` is the twenty-three registers that move while a car is charging.
#: Everything else is identity, ratings and settings -- on the slow tier,
#: because a rated current does not change and a phase mode changes when a
#: person changes it.
FAST = ("wallbox_live",)
SLOW = tuple(name for name in COMPONENTS if name not in FAST)


class SungrowWallbox(MappedDevice):
    """An AC011E/AC22E wallbox on its own Modbus unit.

    Which unit is not a setting: **3** through a WiNet-S, and **248** at the
    wallbox's own LAN address, over TLS on port 516. Both are measured. A
    sweep for port 502 never finds a wallbox, so it is asked for behind an
    endpoint that already answered, or at the address its owner gives. See
    `sungrow_modbus.wallbox.probe_units`.
    """

    # Declared, not assigned: `MappedDevice` sets one attribute per entry in
    # COMPONENTS with `setattr`, which a type checker cannot see. Naming them
    # here is what lets `mypy --strict` check the code that reads them, and it
    # doubles as the list of what a wallbox actually holds.
    wallbox_identity: WallboxIdentity
    wallbox_ratings: WallboxRatings
    wallbox_live: WallboxLive
    wallbox_settings: WallboxSettings

    def __init__(self, unit: ModbusUnit, unit_id: int) -> None:
        """Bind every component; 3 and 248 are different paths, so the id is kept."""
        super().__init__(unit, COMPONENTS, unit_id)

    @property
    def model(self) -> str | None:
        """Name the model, from its type code where the code is known.

        Unlike the battery, a wallbox reports its own identity: the code at
        input register 21224 and the name as text at 21216. The code is
        preferred because `MODELS` recognises two models nobody here has
        measured -- the AC011E-01 and the AC007-00, from the community
        projects -- so a contributor plugging one in gets a named device on
        the first attempt.
        """
        return self.wallbox_identity.model

    @property
    def serial_hint(self) -> None:
        """Nothing: discovery identifies a wallbox by its model name.

        The serial sits at input registers 21201-21206, just below the name
        the identity probe reads at 21216. `async_read_serial` reads it for
        the device registry; a survey publishes only its stand-in.
        """
        return None

    async def async_read_serial(self) -> str | None:
        """Read the wallbox's own serial, or None where it does not read as text.

        For the device registry, which shows it to the owner. Never for a
        document: a survey masks these words and carries
        `wallbox.serial_stand_in` instead. Raises on a failed read, because
        only the caller can tell a refusal from a timeout.
        """
        from .discovery import _printable
        from .document import SERIAL_COUNT, SERIAL_SPACE, SERIAL_START

        words = await self.async_read_words(SERIAL_SPACE, SERIAL_START, SERIAL_COUNT)
        return _printable(words)

    async def async_update(self, only: tuple[str, ...] | None = None) -> UpdateReport:
        """Refresh the components in `only`, tolerating each failing alone.

        Per component, because they fail independently -- and unlike the
        battery, where that is about a dongle withholding a block, here it is
        mostly about *what is plugged in*: a wallbox with no car attached
        still answers, but a firmware that does not implement a register
        refuses only that block.
        """
        return await self._async_update_components(only or None)
