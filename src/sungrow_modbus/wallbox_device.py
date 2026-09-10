"""A wallbox as a device, on whichever unit it answers on.

Same arrangement as `battery_device.py` and for the same reasons: separate
hardware on a different Modbus unit id, reached through the connection that is
already open, and its own device in the registry hung off the inverter.

**Two tiers, not one.** The pack has none because seventeen registers all move
slowly; a wallbox has one block that changes second to second -- power,
current, session energy, charging status -- and three that change when
somebody plugs a car in or reconfigures the unit. Polling the ratings every
ten seconds would read thirty registers nobody is watching, on a link a
Sungrow inverter grants very few sessions on.

**Nothing here writes.** The write table in `scripts/writes.py` is the only
place a writable register is declared and no wallbox register is in it. That
is a decision, not an omission: the registers that would start and stop a
charge are known -- holding 21211 and 21212 -- and starting somebody's car
charging from a stale automation is not a thing to enable on one measurement
of one unit, on a map no manufacturer document covers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .model import UpdateReport, present
from .wallbox_registers import COMPONENTS

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: Which components are worth reading often, and which are not.
#:
#: `live` is the twenty-three registers that move while a car is charging.
#: Everything else is identity, ratings and settings -- read once at setup and
#: then on the slow tier, because a rated current does not change and a phase
#: mode changes when a person changes it.
FAST = ("wallbox_live",)
SLOW = tuple(name for name in COMPONENTS if name not in FAST)


class SungrowWallbox:
    """An AC011E/AC22E wallbox on its own Modbus unit.

    Which unit is not a setting: **3** through a WiNet-S and **248** where an
    RS485-to-TCP adapter puts it on the network directly. Only 3 has been
    measured. See `sungrow_modbus.wallbox.probe_units`, and note that a
    wallbox cannot be found by sweeping for one at all -- at the one site with
    a wallbox, a full /24 found Modbus on the inverter and its dongle and
    nothing else.
    """

    def __init__(self, unit: ModbusUnit, unit_id: int) -> None:
        """Bind every component to a unit handle, remembering which id it is."""
        self._unit = unit
        #: Which unit id answered, kept because it is worth reporting: 3 and
        #: 248 mean different wiring, and somebody comparing two documents
        #: from one house needs to see which they are looking at.
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

    def component(self, attribute: str):
        """Return one component by the name descriptions refer to it by."""
        return getattr(self, attribute)

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
        input 21224 and the name as text at 21216. The code is preferred
        because `MODELS` recognises two models nobody here has measured --
        the AC011E-01 and the AC007-00, from the community projects -- so a
        contributor plugging one in gets a named device on the first attempt.
        """
        return self.wallbox_identity.model

    @property
    def serial_hint(self) -> None:
        """Nothing. A wallbox's serial is deliberately never read.

        It sits at input 21200-21205, immediately before the model name this
        library probes, and it is a serial like any other: one was published
        in a fingerprint as the words `[16690, 13633]` -- which decode to
        `A25A` -- before anybody thought about the second device in the house.
        So the identity probe reads the *name* at 21215, the serial is masked
        at the survey's publishing boundary, and nothing here reads it at all.

        The device is identified by the inverter's serial plus a suffix,
        exactly as the battery is.
        """
        return None

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
