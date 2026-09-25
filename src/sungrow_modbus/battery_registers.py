"""The SBR battery's own registers, which are not the inverter's.

Hand-written, and in its own module for a reason worth stating: `registers.py`
is **generated** from `doc/legacy_entity_map.json`, which is the inverter's
map. These components were added to that file by hand and the next run of
`scripts/generate_registers.py` deleted all eighty-one lines of them --
exactly the failure mode this project keeps meeting from both directions,
somebody's careful work written into a file whose contents are computed.

The source here is
`legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`, proven by years
of use, and `tests/test_sbr_pack.py` checks every address and scale against
it -- the same protection the generated modules get from `--check`, arrived at
the other way round.

**Not on the inverter's unit.** Which unit the pack answers on depends on the
transport: 200 over the inverter's own LAN port, 2 through a WiNet-S. See
`sungrow_modbus.battery.probe_units`.
"""

from __future__ import annotations

from modbus_connection.model import Component, gauge, uint32

from .addresses import reg


class SbrBatteryPack(Component):
    """The SBR's own registers, on the battery's own unit id.

    **Not the inverter's unit.** Which unit answers depends on the transport,
    measured 2026-09-08 on two houses: unit **200** over the inverter's own
    LAN port, and unit **2** through a WiNet-S, where 200 times out. Unit 2 is
    also where a slave inverter lives, so whoever probes it has to read the
    device type code alongside -- a slave answers that and a battery does not.
    See `sungrow_modbus.battery.probe_units`.

    Ported from `legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`,
    whose addresses and scales are field-proven; the values below were read
    off an SBR096 while it was working.
    """

    register_space = "input"

    voltage = gauge(reg(10741), 0.1, signed=False, nan=0xFFFF, unit="V")
    """Pack voltage. Read 199.0 V."""

    current = gauge(reg(10742), 0.1, nan=0xFFFF, unit="A")
    """Pack current, signed: negative while discharging."""

    temperature = gauge(reg(10743), 0.1, nan=0xFFFF, unit="°C")
    """Pack temperature. Read 23.0 °C."""

    state_of_charge = gauge(reg(10744), 0.1, signed=False, nan=0xFFFF, unit="%")
    """State of charge, in tenths of a percent. Read 93.9 %."""

    state_of_health = gauge(reg(10745), 1, signed=False, nan=0xFFFF, unit="%")
    """State of health, whole percent. Read 98 %."""

    total_charge = uint32(reg(10746), scale=0.1, word_order="little", unit="kWh")
    """Lifetime energy into the pack."""

    total_discharge = uint32(reg(10748), scale=0.1, word_order="little", unit="kWh")
    """Lifetime energy out of the pack."""


class SbrBatteryCells(Component):
    """The per-module cell data, which a dongle does not forward.

    Separate from `SbrBatteryPack` **because it fails separately**, and it is
    now known which way round that is. Measured on one SBR096 read both ways
    within seconds on 2026-09-09:

    * on the inverter's own LAN port at unit 200, every register here read
      true -- 3.3337 V highest cell, 3.3251 V lowest, module temperatures
      22.9 and 21.9 degrees;
    * through the same inverter's WiNet-S at unit 2, this block **refuses
      with exception 0x02** while `SbrBatteryPack` above answers with
      identical values.

    So the pack does populate these registers and the dongle is what loses
    them. That settles a question that had been open with one path's evidence:
    at another house a dongle answered this block with **zeros** rather than
    refusing, which is the same loss wearing the more dangerous face -- and
    the reason `capabilities.ZERO_MEANS_ABSENT` has to cover this block. Two
    dongle firmwares, two ways of not forwarding it.

    Splitting them also means the pack summary still updates when this block
    does not -- pooled into one component, a refusal would take the state of
    charge with it.

    **The four position fields are not plain numbers.** They pack a module and
    a cell into one word, `(module << 8) | cell`, which is why one reads 780
    rather than 12.

    That started as an inference from eight samples. It is now **proved from
    a single reading**, by reading the per-module registers alongside and
    checking the pack agrees with them. On this SBR096 at unit 200:

    | Module | Highest cell | Lowest cell |
    | --- | --- | --- |
    | 1 | 3.3507 V | 3.3436 V |
    | 2 | 3.3484 V | 3.3448 V |
    | 3 | 3.3487 V | 3.3449 V |

    The pack's own `max_cell_voltage` read 3.3507 V -- module 1's figure, the
    highest of the three -- and `max_cell_position` read 260, which is
    `0x0104`: **module 1**, cell 4. The pack's `min_cell_voltage` read
    3.3436 V, again module 1's, and `min_cell_position` read 275 = `0x0113`:
    **module 1**, cell 19. Both high bytes name the module whose extreme the
    pack quoted, in the same reading, with no appeal to a second house. Cell
    19 also puts a floor under the twenty-cell claim.

    The same reading counts the modules: 10767-10771 and 10775-10779 read 0
    and the cell types at 10783-10787 read 0, so this pack is **three**
    modules -- 9.6 kWh at 3.2 kWh each, which is what an SBR096 is.

    One thing still does not close: 60 cells at the measured 3.34 V is
    slightly more than the 200.0 V the pack reports for itself, consistently
    across two readings. Pack voltage is measured separately from cell
    voltage and 0.1 percent is inside a BMS's tolerance, so this is noted
    rather than explained. An SBR128 would add the last brick by showing a
    high byte of 4.

    Nothing here is an entity yet, so the encoding is a decision rather than a
    migration -- see `doc/integration_plan.md`. What must not happen is the
    legacy package's treatment, which publishes the raw word and leaves the
    reader to wonder what cell 780 is.
    """

    register_space = "input"

    max_cell_voltage = gauge(reg(10757), 0.0001, signed=False, nan=0xFFFF, unit="V")
    """Highest cell voltage, in tenths of a millivolt."""

    max_cell_position = gauge(reg(10758), 1, signed=False, nan=0xFFFF)
    """Which cell that was."""

    min_cell_voltage = gauge(reg(10759), 0.0001, signed=False, nan=0xFFFF, unit="V")
    """Lowest cell voltage."""

    min_cell_position = gauge(reg(10760), 1, signed=False, nan=0xFFFF)
    """Which cell that was."""

    max_module_temperature = gauge(reg(10761), 0.1, nan=0xFFFF, unit="°C")
    """Warmest module."""

    max_module_temperature_position = gauge(reg(10762), 1, signed=False, nan=0xFFFF)
    """Which module that was."""

    min_module_temperature = gauge(reg(10763), 0.1, nan=0xFFFF, unit="°C")
    """Coolest module."""

    min_module_temperature_position = gauge(reg(10764), 1, signed=False, nan=0xFFFF)
    """Which module that was."""

    # -- the position words, unpacked -------------------------------------
    #
    # The four fields above are the registers as the device sends them, kept
    # because they are what is read and what legacy mode reproduces. These
    # eight are what a person can use. See the class docstring for the
    # evidence; in short, `(module << 8) | index`, and the high byte is the
    # module in all eight samples known.

    @property
    def max_cell_module(self) -> int | None:
        """Which module holds the highest cell (reg 10758, high byte)."""
        return _module(self.max_cell_position)

    @property
    def max_cell_number(self) -> int | None:
        """Which cell in it (reg 10758, low byte). Seen 1-20."""
        return _index(self.max_cell_position)

    @property
    def min_cell_module(self) -> int | None:
        """Which module holds the lowest cell (reg 10760, high byte)."""
        return _module(self.min_cell_position)

    @property
    def min_cell_number(self) -> int | None:
        """Which cell in it (reg 10760, low byte). Seen 1-20."""
        return _index(self.min_cell_position)

    @property
    def max_module_temperature_module(self) -> int | None:
        """Which module is warmest (reg 10762, high byte)."""
        return _module(self.max_module_temperature_position)

    @property
    def max_module_temperature_sensor(self) -> int | None:
        """Which sensor in it (reg 10762, low byte).

        Named a sensor rather than a cell because the four samples of this
        register and its sibling only ever hold **1 or 2**, where the cell
        registers hold 6, 10, 12 and 20. A module with two temperature
        sensors fits that and nothing contradicts it -- but four samples of a
        two-valued field is thin, so this name is an inference and the raw
        word is kept beside it.
        """
        return _index(self.max_module_temperature_position)

    @property
    def min_module_temperature_module(self) -> int | None:
        """Which module is coolest (reg 10764, high byte)."""
        return _module(self.min_module_temperature_position)

    @property
    def min_module_temperature_sensor(self) -> int | None:
        """Which sensor in it (reg 10764, low byte). Seen 1 or 2."""
        return _index(self.min_module_temperature_position)


#: How a position word is packed: the module in the high byte, an index
#: within that module in the low byte.
#:
#: Both halves are one-based, which is why nothing here subtracts. Sungrow
#: documents none of it -- see `SbrBatteryCells` for the eight samples this
#: rests on.
MODULE_SHIFT = 8
INDEX_MASK = 0xFF


def _module(word: float | None) -> int | None:
    """Return the module a position word names, or None.

    Takes a float because the position registers are declared as scale-1
    `gauge` fields, which decode to a float even though the register holds a
    word. The `int()` below is what makes that harmless, and stating the
    parameter honestly is cheaper than restating fourteen field declarations.

    Zero is None rather than module 0. The registers are one-based, so a zero
    word is not "module 0, cell 0" -- it is a pack that has not answered
    with anything, which is exactly what a WiNet-S returns for this block on
    one of the two dongle firmwares measured.
    """
    if not word:
        return None
    return int(word) >> MODULE_SHIFT or None


def _index(word: float | None) -> int | None:
    """Return the cell or sensor a position word names, or None.

    A float for the same reason as `_module` above.
    """
    if not word:
        return None
    return int(word) & INDEX_MASK or None


class SbrBatteryModules(Component):
    """Per-module cell voltages and cell type, for up to eight modules.

    Its own component, and the third of three, because it fails third: a
    WiNet-S refuses this block exactly as it refuses `SbrBatteryCells`, and
    an SBR096 answers **0** for modules 4 to 8 because they are not there.
    Pooled with the pack summary, either of those would take the state of
    charge down with it.

    Ported from `legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`,
    whose addresses are right and whose *comments* are not -- four
    consecutive entries there are all labelled "reg 10777, Min. Cell Voltage
    of Module 5" and three more all say "Cell Type of Module 5". Every
    address below was read back off an SBR096 at unit 200 on 2026-09-09
    rather than trusted:

    | Module | Highest cell | Lowest cell | Cell type |
    | --- | --- | --- | --- |
    | 1 | 3.3507 V | 3.3436 V | 66 |
    | 2 | 3.3484 V | 3.3448 V | 66 |
    | 3 | 3.3487 V | 3.3449 V | 66 |
    | 4-8 | 0 | 0 | 0 |

    That reading is also what **proves** the position encoding in
    `SbrBatteryCells`: the pack quotes module 1's 3.3507 V as its own
    maximum and names module 1 in the high byte of its position word,
    checkable inside one reading.

    **Eight explicit fields per family rather than a `repeating_group`.**
    The shape is a repeating group and declaring it as one would be shorter,
    but `scripts/generate_scan_plan.py` records the library's block reads
    into a committed artefact that a contributor's zip decodes from, and that
    agreement currently holds partly because this map has no repeating
    groups. Twenty-four declarations is the cheaper price.

    **Nothing here becomes an entity yet.** A module that is not fitted reads
    0, and a cell voltage of 0 V is indistinguishable from a fault -- so
    something has to establish how many modules there are before these can be
    granted, and that is a separate question from reading them. The survey
    carries them meanwhile, which is where the next SBR128 will settle the
    module count.
    """

    register_space = "input"

    max_cell_voltage_module_1 = gauge(
        reg(10765), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 1. Read 3.3507 V."""

    max_cell_voltage_module_2 = gauge(
        reg(10766), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 2. Read 3.3484 V."""

    max_cell_voltage_module_3 = gauge(
        reg(10767), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 3. Read 3.3487 V."""

    max_cell_voltage_module_4 = gauge(
        reg(10768), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 4.

    Absent on the pack measured, which has three modules: read 0.
    """

    max_cell_voltage_module_5 = gauge(
        reg(10769), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 5.

    Absent on the pack measured, which has three modules: read 0.
    """

    max_cell_voltage_module_6 = gauge(
        reg(10770), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 6.

    Absent on the pack measured, which has three modules: read 0.
    """

    max_cell_voltage_module_7 = gauge(
        reg(10771), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 7.

    Absent on the pack measured, which has three modules: read 0.
    """

    max_cell_voltage_module_8 = gauge(
        reg(10772), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Highest cell in module 8.

    Absent on the pack measured, which has three modules: read 0.
    """

    min_cell_voltage_module_1 = gauge(
        reg(10773), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 1. Read 3.3436 V."""

    min_cell_voltage_module_2 = gauge(
        reg(10774), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 2. Read 3.3448 V."""

    min_cell_voltage_module_3 = gauge(
        reg(10775), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 3. Read 3.3449 V."""

    min_cell_voltage_module_4 = gauge(
        reg(10776), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 4.

    Absent on the pack measured, which has three modules: read 0.
    """

    min_cell_voltage_module_5 = gauge(
        reg(10777), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 5.

    Absent on the pack measured, which has three modules: read 0.
    """

    min_cell_voltage_module_6 = gauge(
        reg(10778), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 6.

    Absent on the pack measured, which has three modules: read 0.
    """

    min_cell_voltage_module_7 = gauge(
        reg(10779), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 7.

    Absent on the pack measured, which has three modules: read 0.
    """

    min_cell_voltage_module_8 = gauge(
        reg(10780), 0.0001, signed=False, nan=0xFFFF, unit="V"
    )
    """Lowest cell in module 8.

    Absent on the pack measured, which has three modules: read 0.
    """

    cell_type_module_1 = gauge(reg(10781), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 1 reports.

    Read 66.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_2 = gauge(reg(10782), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 2 reports.

    Read 66.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_3 = gauge(reg(10783), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 3 reports.

    Read 66.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_4 = gauge(reg(10784), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 4 reports.

    Read 0, this module not being fitted.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_5 = gauge(reg(10785), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 5 reports.

    Read 0, this module not being fitted.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_6 = gauge(reg(10786), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 6 reports.

    Read 0, this module not being fitted.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_7 = gauge(reg(10787), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 7 reports.

    Read 0, this module not being fitted.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    cell_type_module_8 = gauge(reg(10788), 1, signed=False, nan=0xFFFF)
    """What cell chemistry module 8 reports.

    Read 0, this module not being fitted.
    Sungrow documents no code table for this. 66 is what all three
    fitted modules of one SBR096 answered and 0 is what the five
    absent ones did, so the only reading this rests on is
    "non-zero means fitted".
    """

    dc_contactor_state = gauge(reg(10789), 1, signed=False, nan=0xFFFF)
    """State of the pack's DC contactor. Read 2.

    The legacy package calls this "State of DC Switch", from a German
    comment reading *Zustand DC-Schuetz*. Its code table is undocumented,
    and a single reading of 2 says nothing about what the other values are,
    so this stays a library field with no entity until somebody has watched
    it change.
    """
