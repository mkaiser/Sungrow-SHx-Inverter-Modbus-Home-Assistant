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

from modbus_connection.model import Component

from ..model import UpdateReport, present
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


class SungrowWallbox:
    """An AC011E/AC22E wallbox on its own Modbus unit.

    Which unit is not a setting: **3** through a WiNet-S, and **248** at the
    wallbox's own LAN address, over TLS on port 516. Both are measured. A
    sweep for port 502 never finds a wallbox, so it is asked for behind an
    endpoint that already answered, or at the address its owner gives. See
    `sungrow_modbus.wallbox.probe_units`.
    """

    # Declared, not assigned: `__init__` sets one attribute per entry in
    # COMPONENTS with `setattr`, which a type checker cannot see. Naming them
    # here is what lets `mypy --strict` check the code that reads them, and it
    # doubles as the list of what a wallbox actually holds.
    wallbox_identity: WallboxIdentity
    wallbox_ratings: WallboxRatings
    wallbox_live: WallboxLive
    wallbox_settings: WallboxSettings

    def __init__(self, unit: ModbusUnit, unit_id: int) -> None:
        """Bind every component to a unit handle, remembering which id it is."""
        self._unit = unit
        #: Which unit id answered, kept because it is worth reporting: 3 and
        #: 248 mean different paths, which do not read alike, and somebody
        #: comparing two documents from one house needs to see which they are
        #: looking at.
        self.unit_id = unit_id
        for attribute, component in COMPONENTS.items():
            setattr(self, attribute, component(unit))
        self._fields = {
            name: attribute
            for attribute, component in COMPONENTS.items()
            for name in vars(component)
            if not name.startswith("_")
            and name not in {"register_space", "declared_fields"}
        }

    def component(self, attribute: str) -> Component:
        """Return one component by the name descriptions refer to it by."""
        return getattr(self, attribute)  # type: ignore[no-any-return]

    @property
    def field_names(self) -> frozenset[str]:
        """Every field name this device can be asked for, by `field()`.

        Public because callers outside the library need to enumerate what a
        device offers -- the survey publishes one value per field, and the
        diagnostics download does the same. Reading `_fields` instead would
        be worse here than it usually is: this library is pinned by version in
        the integration's manifest, so renaming a private attribute would ship
        as a perfectly good release and break the integration at runtime.
        """
        return frozenset(self._fields)

    def field(self, name: str) -> object:
        """Return one value by name, wherever it lives.

        Includes the decoded meanings, which are properties rather than
        registers -- `charging_status` is a word where `charging_status_raw`
        is a 6, and the word is the one worth showing.
        """
        attribute = self._fields.get(name)
        if attribute is not None:
            return present(getattr(self.component(attribute), name))
        for holder in COMPONENTS:
            component = self.component(holder)
            if isinstance(getattr(type(component), name, None), property):
                return getattr(component, name)
        raise AttributeError(f"no wallbox value named {name!r}")

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

    async def async_read_words(self, space: str, address: int, count: int) -> list[int]:
        """Read raw words at one address, for a survey's dump of this unit.

        The same seam `SungrowInverter` offers. Raises, because only the
        caller can tell a refusal from a timeout.
        """
        if space == "holding":
            return list(await self._unit.read_holding_registers(address, count))
        return list(await self._unit.read_input_registers(address, count))

    async def async_update(self, only: tuple[str, ...] | None = None) -> UpdateReport:
        """Refresh the components in `only`, tolerating each failing alone.

        Per component, because they fail independently -- and unlike the
        battery, where that is about a dongle withholding a block, here it is
        mostly about *what is plugged in*: a wallbox with no car attached
        still answers, but a firmware that does not implement a register
        refuses only that block.
        """
        from modbus_connection import ModbusError

        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for attribute in only or tuple(COMPONENTS):
            try:
                await self.component(attribute).async_update()
            except ModbusError as err:
                failed[attribute] = err
            else:
                updated.add(attribute)
        return UpdateReport(updated=frozenset(updated), failed=failed)
