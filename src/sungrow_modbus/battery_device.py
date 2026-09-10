"""An SBR pack as a device, on whichever unit it answers on.

Separate from `SungrowInverter` because it is separate hardware on a
different Modbus unit id, reached through the same connection. One config
entry is one endpoint, so the pack shares the inverter's serialized link and
gets its own device in the registry, linked to the inverter by `via_device`.

Which unit is not a setting. It moves with the transport -- 200 over the
inverter's own LAN port, 2 through a WiNet-S, measured at three houses -- and
`battery.probe_units` is what finds it. A contributor does not know their
battery's unit id and should never be asked.

**The two components fail separately, and that is the whole reason they are
two.** Measured on one SBR096 read both ways within seconds: the cell block
refuses with exception 0x02 through a dongle while the pack block answers
identical values, and at a second house a different dongle firmware answered
the cell block with zeros instead. Pooled into one component a refusal would
take the state of charge with it, and a house on a dongle would see its
battery reported unreadable when half of it was fine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .battery import model_for_capacity
from .battery_registers import SbrBatteryCells, SbrBatteryPack
from .model import UpdateReport, present

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: The pack's components, by the name a description refers to them by.
COMPONENTS: dict[str, type] = {
    "pack": SbrBatteryPack,
    "cells": SbrBatteryCells,
}

#: Cell-level fields are granted only on a reading that is not zero.
#:
#: One dongle firmware answers this whole block with zeros rather than
#: refusing it, and a zero decodes to a value. Granting on that would create
#: eight entities reporting 0 V and module 0 forever, with no recovery --
#: nothing ever removes an entity. So the same rule the inverter's optional
#: trackers get applies here: an answer of zero is not evidence of hardware.
#:
#: The pack-level fields need no such guard. A pack that answers 199 V for
#: its voltage is a pack; the sentinel and the refusal are both handled by
#: the component raising or the field decoding to None.
CELLS_NEED_A_NONZERO_READING = True


class SungrowBattery:
    """An SBR/SBH pack on its own Modbus unit.

    Deliberately small. The pack has no tiers -- seventeen registers in two
    reads -- so there is one interval and one coordinator, unlike the
    inverter's four.
    """

    def __init__(self, unit: ModbusUnit, unit_id: int) -> None:
        """Bind both components to a unit handle, remembering which id it is."""
        self._unit = unit
        #: Which unit id answered, kept because it is worth reporting: the
        #: same pack is 200 on a cable and 2 through a dongle, and somebody
        #: comparing two documents from one house needs to see that.
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

        Includes the unpacked halves of the position words, which are
        properties on `SbrBatteryCells` rather than registers -- a reader
        wants module 3, cell 12, not 780.
        """
        attribute = self._fields.get(name)
        if attribute is not None:
            return present(getattr(self.component(attribute), name))
        for holder in COMPONENTS:
            component = self.component(holder)
            if isinstance(getattr(type(component), name, None), property):
                return getattr(component, name)
        raise AttributeError(f"no battery value named {name!r}")

    @property
    def capacity_kwh(self) -> float | None:
        """Nothing: the pack does not report its own capacity.

        Worth stating rather than leaving to be discovered. The capacity that
        names the model is register **5639 on the inverter**, not anything
        here, so `model` takes it as an argument. Measured: this pack's own
        registers carry voltage, current, temperature, charge and health, and
        no size at all.
        """
        return None

    def model(self, capacity_kwh: float | None) -> str | None:
        """Name the pack from the capacity the *inverter* reports for it."""
        found = model_for_capacity(capacity_kwh)
        return found.name if found is not None else None

    @property
    def has_cell_data(self) -> bool:
        """Whether the cell block gave a reading worth building entities on.

        False for both ways a dongle loses it: a refusal leaves every field
        None, and the zeros firmware leaves them all 0. Checked on the two
        voltages rather than on the positions, because a position of zero is
        already mapped to None and would hide a real reading of cell 0 --
        which cannot happen, the registers being one-based, but the voltage
        is the value a person would actually look at.
        """
        readings = [
            getattr(self.cells, name)
            for name in ("max_cell_voltage", "min_cell_voltage")
        ]
        return any(value for value in readings)

    async def async_update(self) -> UpdateReport:
        """Refresh both components, tolerating either one failing alone."""
        from modbus_connection import ModbusError

        updated: set[str] = set()
        failed: dict[str, ModbusError] = {}
        for attribute in COMPONENTS:
            try:
                await self.component(attribute).async_update()
            except ModbusError as err:
                failed[attribute] = err
            else:
                updated.add(attribute)
        return UpdateReport(updated=frozenset(updated), failed=failed)
