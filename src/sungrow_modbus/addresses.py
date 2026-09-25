"""Where things are, by name, so that no read carries a bare number.

Two sources, and the rule for choosing between them:

* **A register the map already knows is looked up, never re-typed.**
  `field_address("communication_module_firmware_version")` returns what
  `registers.py` says, so a field the map moves is followed everywhere it is
  read. `registers.py` is generated from the YAML package's entity map, and a
  second copy of an address anywhere else is a second thing to get wrong.
* **A register no component maps gets a constant here**, named for what it
  is for rather than where it is. There are only a few, and each is read as a
  *question* -- is a dongle in the path, is an iHomeManager at this unit --
  not as a value.

Every address is a **protocol** address, one below the register number in
Sungrow's document; `Address.register` gives the document's number, so a log
line or an error can say both.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit
    from modbus_connection.model import Component

Space = Literal["input", "holding"]


def reg(number: int) -> int:
    """Return the protocol address of a register, given Sungrow's number for it.

    Every register map here is written in the **document's** numbers, the ones
    in Sungrow's protocol tables and in the YAML package's comments, and this
    is the single place the two are one apart. Written as protocol addresses,
    the map said `power_flow_status = integer(13000)` -- and 13000 is what the
    specification calls the *running state*, the field one line above it.
    """
    if number < 1:
        raise ValueError(f"register numbers start at 1, not {number}")
    return number - 1


class Address(NamedTuple):
    """One block of registers: which table, where, and how many words."""

    space: Space
    address: int
    length: int

    @property
    def register(self) -> int:
        """The register number Sungrow's document uses, one above the address."""
        return self.address + 1

    def __str__(self) -> str:
        """Say it the way the specification does, which is how people look it up."""
        return f"{self.space} register {self.register} (address {self.address})"


async def read(unit: ModbusUnit, where: Address) -> list[int]:
    """Read one named block, raising like the unit does.

    Raises rather than returning nothing, because only the caller can tell a
    refusal from a lost read, and the difference is usually the point.
    """
    if where.space == "holding":
        return list(await unit.read_holding_registers(where.address, where.length))
    return list(await unit.read_input_registers(where.address, where.length))


#: Input register 6100, "PV power of today". Sungrow documents 6100-6195 as
#: **not forwarded by a WiNet-S, WiNet-S2 or Logger**, so an answer means
#: nothing of the kind is in the path. Counted over ten fingerprints it agrees
#: with the owner's own account every time; see `CLAUDE.md` on why register
#: 13265 cannot stand in for it.
DIRECT_ONLY_PROBE = Address("input", reg(6100), 2)

#: Input register 8000 on unit 247, the iHomeManager's device type. Mapped by
#: nothing yet -- no iHomeManager has ever been measured -- and read only to
#: say what answered.
IHOMEMANAGER_TYPE = Address("input", reg(8000), 1)

#: Input registers 8001-8002 on the same unit, its protocol number as text.
IHOMEMANAGER_PROTOCOL = Address("input", reg(8001), 2)

#: Input registers 21201-21206, a wallbox's serial number. **Deliberately not
#: mapped**: no component reads it, so no entity or capability probe can carry
#: it -- see `wallbox.MODEL_NAME` for what identifies a wallbox instead. Named
#: here only so the survey can say *that* something answers at a wallbox unit;
#: every published document masks what it answered.
WALLBOX_SERIAL = Address("input", reg(21201), 6)


Device = Literal["inverter", "battery", "wallbox"]


def device_components() -> dict[Device, dict[str, type[Component]]]:
    """Every component this library maps, by the device it lives on.

    The one list of them. The survey's plan generator records the same set,
    and a name lookup that searched a different one would find a field the
    survey cannot, or the other way round.
    """
    from .battery_registers import SbrBatteryCells, SbrBatteryModules, SbrBatteryPack
    from .components import InverterControl, InverterIdentity
    from .registers import COMPONENTS
    from .wallbox_registers import COMPONENTS as WALLBOX_COMPONENTS

    return {
        "inverter": {
            "identity": InverterIdentity,
            "control": InverterControl,
            **COMPONENTS,
        },
        "battery": {
            "sbr_battery_pack": SbrBatteryPack,
            "sbr_battery_cells": SbrBatteryCells,
            "sbr_battery_modules": SbrBatteryModules,
        },
        "wallbox": dict(WALLBOX_COMPONENTS),
    }


def field_address(name: str, device: Device = "inverter") -> Address:
    """Return where the map puts one field, on one device.

    The device is part of the question because names repeat across devices:
    an inverter and a wallbox both have a `device_type_code` and a
    `phase_a_voltage`, at different addresses. Within a device a name is
    expected to be unique; where it is not and the addresses differ, this
    refuses rather than picking one.
    """
    found: set[Address] = set()
    for klass in device_components()[device].values():
        field = klass.declared_fields.get(name)
        if field is not None:
            found.add(Address(klass.register_space, field.address, field.count))
    if not found:
        raise KeyError(f"no field named {name!r} on the {device}")
    if len(found) > 1:
        raise KeyError(
            f"{name!r} is at {len(found)} addresses on the {device}: "
            + ", ".join(str(where) for where in sorted(found))
        )
    return found.pop()
