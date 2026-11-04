"""An SBR pack as a device, on whichever unit it answers on.

Separate from `SungrowInverter` because it is separate hardware on a
different Modbus unit id, reached through the same connection. One config
entry is one endpoint, so the pack shares the inverter's serialized link and
gets its own device in the registry, linked to the inverter by `via_device`.

Which unit is not a setting. It moves with the transport -- 200 over the
inverter's own LAN port, 2 through a WiNet-S, measured at three houses -- and
`battery.probe_units` is what finds it. A contributor does not know their
battery's unit id and should never be asked.

**The components fail separately, and that is the whole reason there are
three.** Measured on one SBR096 read both ways within seconds: the cell and
module blocks refuse with exception 0x02 through a dongle while the pack block
answers identical values, and at a second house a different dongle firmware
answered the cell block with zeros instead. Pooled into one component a
refusal would take the state of charge with it, and a house on a dongle would
see its battery reported unreadable when half of it was fine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..device import MappedDevice
from ..model import UpdateReport
from .power import model_for_capacity
from .registers import SbrBatteryCells, SbrBatteryModules, SbrBatteryPack

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

#: The pack's polled components, by the name a description refers to them by.
COMPONENTS: dict[str, type] = {
    "pack": SbrBatteryPack,
    "cells": SbrBatteryCells,
}

#: Components a survey always reads and a poll only when asked to.
#:
#: The per-module block's entities are disabled by default, so polling it
#: for nobody would spend the shared link's session time on nothing:
#: `poll_modules` turns it on once somebody has enabled one.
SURVEY_COMPONENTS: dict[str, type] = {
    "modules": SbrBatteryModules,
}

#: The name a published document gives each component, the one
#: `addresses.device_components` uses.
PUBLISHED_NAMES = {
    "pack": "sbr_battery_pack",
    "cells": "sbr_battery_cells",
    "modules": "sbr_battery_modules",
}


class SungrowBattery(MappedDevice):
    """An SBR/SBH pack on its own Modbus unit.

    Deliberately small. The pack has no tiers -- seventeen polled registers
    in two reads -- so there is one interval and one coordinator.
    """

    # Declared, not assigned: `MappedDevice` sets one attribute per component
    # with `setattr`, which a type checker cannot see. Naming them here is
    # what lets `mypy --strict` check the code that reads them, and it
    # doubles as the list of what a pack actually holds.
    pack: SbrBatteryPack
    cells: SbrBatteryCells
    modules: SbrBatteryModules

    #: Whether a poll reads the per-module block too. A survey always does.
    poll_modules = False

    def __init__(self, unit: ModbusUnit, unit_id: int) -> None:
        """Bind every component, the survey's too, remembering which id it is.

        The id is worth reporting: the same pack is 200 on a cable and 2
        through a dongle.
        """
        super().__init__(unit, {**COMPONENTS, **SURVEY_COMPONENTS}, unit_id)

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
        None, and the zeros firmware leaves them all 0. Cell entities are
        granted only when this is true, because nothing ever removes an
        entity: granting on zeros would leave them reporting 0 V and module 0
        forever. The pack-level fields need no such guard -- a pack
        that answers 199 V is a pack. Checked on the two
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

    async def async_update(self, *, survey: bool = False) -> UpdateReport:
        """Refresh the components, tolerating any one failing alone.

        `survey` adds `SURVEY_COMPONENTS`, which a poll reads only with
        `poll_modules` set: otherwise their fields read None until a survey
        has asked.
        """
        extra = survey or self.poll_modules
        return await self._async_update_components(
            {**COMPONENTS, **(SURVEY_COMPONENTS if extra else {})}
        )
