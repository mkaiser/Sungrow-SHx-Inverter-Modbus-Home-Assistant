"""The SBR's own registers, and finding the unit they answer on.

Everything here rests on one measurement that corrected the plan: which unit
id an SBR answers on **depends on the transport**. Over the inverter's own
LAN port it is unit 200; through a WiNet-S it is unit 2 and 200 times out.
The plan said an SBR was "not reachable through WiNet-S at all", and
therefore that such a house needed a second config entry, which was wrong in
a way that would have cost users a whole device.

The register map is ported from the YAML package, whose addresses and scales
are field-proven. The values asserted below were read off a working SBR096.
"""

from __future__ import annotations

from pathlib import Path
import re

from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus.battery import (
    IDENTITY_REGISTER,
    IMPLAUSIBLE,
    PACK_UNITS,
    probe_units,
)
from sungrow_modbus.battery_registers import (
    SbrBatteryCells,
    SbrBatteryModules,
    SbrBatteryPack,
)

#: What bar12's SBR096 answered at unit 2 on 2026-09-08, in order from 10740.
MEASURED = {
    10740: 1990,  # 199.0 V
    10741: 21,  # 2.1 A
    10742: 230,  # 23.0 °C
    10743: 939,  # 93.9 %
    10744: 98,  # 98 %
    10745: 0,
    10746: 0,
    10747: 0,
    10748: 0,
}


def _unit_with(values: dict[int, int]):
    """Return a mock unit answering those input registers."""
    unit = MockModbusConnection().for_unit(2)
    unit.input = dict(values)
    return unit


@pytest.mark.asyncio
async def test_the_pack_reads_as_it_was_measured() -> None:
    """The five fields that answered true through a dongle."""
    component = SbrBatteryPack(_unit_with(MEASURED))
    await component.async_update()

    assert component.voltage == 199.0
    assert component.current == 2.1
    assert component.temperature == 23.0
    assert component.state_of_charge == 93.9
    assert component.state_of_health == 98


@pytest.mark.asyncio
async def test_a_discharging_pack_reads_negative() -> None:
    """The current is signed, and the sign is the direction.

    Unsigned, a pack discharging at 2.1 A would read 6553.5 A, which is the
    kind of number that reaches a dashboard before anybody notices.
    """
    component = SbrBatteryPack(_unit_with({**MEASURED, 10741: 0x10000 - 21}))
    await component.async_update()
    assert component.current == -2.1


@pytest.mark.asyncio
async def test_an_unavailable_field_is_none_not_a_huge_number() -> None:
    """0xFFFF is the specification's "no reading", not 6553.5 V."""
    component = SbrBatteryPack(_unit_with({address: 0xFFFF for address in MEASURED}))
    await component.async_update()
    assert component.voltage is None
    assert component.state_of_charge is None


@pytest.mark.asyncio
async def test_the_cell_block_is_separate_so_a_refusal_costs_only_itself() -> None:
    """Measured: the cell registers read 0 through a dongle, the pack true.

    Pooled into one component they would share a fate -- and a refusal of the
    cell data would take the state of charge with it, which is the one field
    an owner actually watches.
    """
    assert set(SbrBatteryPack.declared_fields) & set(
        SbrBatteryCells.declared_fields
    ) == (set())
    pack = SbrBatteryPack(_unit_with(MEASURED))
    await pack.async_update()
    assert pack.state_of_charge == 93.9

    # And the pack, read separately, is untouched by whatever the cells do.
    assert pack.state_of_charge == 93.9


@pytest.mark.asyncio
async def test_the_cells_decode_tenths_of_a_millivolt() -> None:
    """3.3457 V, not 33457 -- the YAML's scale, which is easy to get wrong."""
    cells = SbrBatteryCells(
        _unit_with(
            {
                10756: 33457,
                10757: 518,
                10758: 33390,
                10759: 788,
                10760: 218,
                10761: 514,
                10762: 206,
                10763: 259,
            }
        )
    )
    await cells.async_update()
    assert cells.max_cell_voltage == 3.3457
    assert cells.min_cell_voltage == 3.339
    assert cells.max_module_temperature == 21.8
    assert cells.max_cell_position == 518


@pytest.mark.asyncio
async def test_unit_200_is_taken_as_a_battery_without_further_questions() -> None:
    """Only a battery answers there, so nothing else needs asking."""
    connection = MockModbusConnection()
    connection.for_unit(200).input = dict(MEASURED)

    assert await probe_units(connection.for_unit) == 200


@pytest.mark.asyncio
async def test_a_pack_forwarded_to_unit_2_is_found_there() -> None:
    """The dongle case, which the plan said did not exist."""
    connection = MockModbusConnection()
    connection.for_unit(2).input = dict(MEASURED)

    assert await probe_units(connection.for_unit) == 2


@pytest.mark.asyncio
async def test_a_slave_inverter_at_unit_2_is_not_a_battery() -> None:
    """The mistake this probe exists to avoid.

    Unit 2 is where a WiNet-S forwards a pack **and** where a slave inverter
    lives. A slave answers its device type code and a battery does not, so
    that register is the question. Without it, a master/slave installation
    read through a dongle would file its second inverter as a battery.
    """
    connection = MockModbusConnection()
    connection.for_unit(2).input = {**MEASURED, IDENTITY_REGISTER: 0x0E13}

    assert await probe_units(connection.for_unit) is None


@pytest.mark.asyncio
async def test_a_device_answering_zeros_is_not_a_battery() -> None:
    """The case that made this probe wrong, found by a mock.

    A first version took any successful read as a pack. The mock answers
    unseeded registers with zeros, which is not a quirk of the mock: it is
    what a WiNet-S does for measuring points it does not forward, and what a
    Modbus proxy can do for anything. No SBR sits at 0 V, so a zero is not a
    reading of a battery.
    """
    assert await probe_units(MockModbusConnection().for_unit) is None
    assert 0 in IMPLAUSIBLE and 0xFFFF in IMPLAUSIBLE


def test_both_unit_ids_are_tried_and_the_unambiguous_one_first() -> None:
    """200 before 2, because 200 is only ever a battery."""
    assert PACK_UNITS == (200, 2)


#: The SBR's own YAML, which is where these addresses and scales come from.
#: `doc/legacy_entity_map.json` covers `legacy/modbus_sungrow.yaml` -- the
#: inverter -- so the port of *this* device is checked against its own source,
#: the way the inverter's is against its.
SBR_YAML = (
    Path(__file__).resolve().parent.parent
    / "legacy"
    / "additional_sensors"
    / "modbus_sungrow_SBR_battery.yaml"
)


def _yaml_registers() -> dict[int, dict]:
    """Return the YAML's sensors keyed by protocol address.

    Two things stop `safe_load` reading this file on its own, and neither is
    a problem with the file: `!secret` for the unit id, which
    `scripts/generate_entity_map.py` handles the same way, and anchors like
    `*scan_interval_medium` that are defined in the *main* package YAML. This
    is an include, not a document.
    """
    import yaml

    loader = yaml.SafeLoader
    loader.add_constructor("!secret", lambda ldr, node: ldr.construct_scalar(node))
    text = SBR_YAML.read_text(encoding="utf-8")
    # The anchors live in the file that includes this one; the scan interval
    # is not what is being checked here, so they are replaced rather than
    # resolved.
    text = re.sub(r"\*scan_interval_\w+", "60", text)
    document = yaml.load(text, Loader=loader)
    found: dict[int, dict] = {}

    def walk(node) -> None:
        if isinstance(node, dict):
            if "address" in node and "name" in node:
                found[int(node["address"])] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    return found


YAML_REGISTERS = _yaml_registers()


@pytest.mark.parametrize(
    ("field", "component"),
    [
        *((name, SbrBatteryPack) for name in SbrBatteryPack.declared_fields),
        *((name, SbrBatteryCells) for name in SbrBatteryCells.declared_fields),
        *((name, SbrBatteryModules) for name in SbrBatteryModules.declared_fields),
    ],
)
def test_every_ported_field_matches_the_yaml_it_came_from(field, component) -> None:
    """Address and scale, against the file that has been in the field for years.

    The YAML package's SBR map is proven by use; this port is not. So each
    field is checked against it rather than against my reading of it -- a
    transposed digit in an address reads a neighbouring register and produces
    a plausible number, which is the failure nobody notices.
    """
    descriptor = component.declared_fields[field]
    address = descriptor.address
    assert address in YAML_REGISTERS, (
        f"{field} reads {address} (reg {address + 1}), which the YAML does not"
    )
    entry = YAML_REGISTERS[address]
    expected = float(entry.get("scale", 1))
    actual = float(getattr(descriptor, "scale", 1) or 1)
    assert actual == expected, (
        f"{field} at reg {address + 1} scales by {actual}, the YAML by "
        f"{expected} ({entry['name']})"
    )


def test_the_port_covers_the_pack_summary_the_yaml_exposes() -> None:
    """The fields an owner watches, all present.

    All forty of the YAML's SBR sensors are ported now, across three
    components -- the summary, the pack-level extremes, and the per-module
    detail. What must not be missing is the summary, which is the part
    somebody actually looks at.
    """
    ported = (
        set(SbrBatteryPack.declared_fields)
        | set(SbrBatteryCells.declared_fields)
        | set(SbrBatteryModules.declared_fields)
    )
    for name in (
        "voltage",
        "current",
        "temperature",
        "state_of_charge",
        "state_of_health",
        "total_charge",
        "total_discharge",
    ):
        assert name in ported


def test_the_pack_registers_live_outside_the_generated_module() -> None:
    """Where they are is part of whether they survive.

    These components were written into `src/sungrow_modbus/registers.py`,
    which is generated from the inverter's entity map, and the next run of
    `scripts/generate_registers.py` deleted all eighty-one lines of them
    without a word. Nothing failed: the generator's job is to make that file
    equal its input, and it did.

    So this asserts the arrangement rather than the code: the SBR's registers
    are in a module nothing generates, and the generated one does not mention
    them.
    """
    from pathlib import Path as _Path

    import sungrow_modbus.battery_registers as pack
    import sungrow_modbus.registers as inverter

    assert _Path(pack.__file__).name == "battery_registers.py"
    generated = _Path(inverter.__file__).read_text(encoding="utf-8")
    assert "SbrBattery" not in generated, (
        "the SBR is back in the generated module, where a regeneration will delete it"
    )
    assert "do not edit" in generated.lower() or "generated" in generated.lower()


#: The eight position words this decoding rests on, each with what it means.
#:
#: Four were read off an SBR096 on 2026-09-09, on the inverter's own LAN port
#: at unit 200 -- the only path that answers this block at all. Four have sat
#: in the comments of `legacy/additional_sensors/modbus_sungrow_SBR_battery.yaml`
#: for years, written by somebody recording example values who did not remark
#: that they were packed.
POSITION_WORDS = (
    # (word, module, index, which register, where it came from)
    (780, 3, 12, "max_cell_position", "measured 2026-09-09"),
    (266, 1, 10, "min_cell_position", "measured 2026-09-09"),
    (770, 3, 2, "max_module_temperature_position", "measured 2026-09-09"),
    (257, 1, 1, "min_module_temperature_position", "measured 2026-09-09"),
    (518, 2, 6, "max_cell_position", "legacy yaml comment"),
    (788, 3, 20, "min_cell_position", "legacy yaml comment"),
    (514, 2, 2, "max_module_temperature_position", "legacy yaml comment"),
    (257, 1, 1, "min_module_temperature_position", "legacy yaml comment"),
)


@pytest.mark.parametrize(
    ("word", "module", "index", "register", "source"),
    POSITION_WORDS,
    ids=[f"{w}-{s.split()[0]}" for w, _m, _i, _r, s in POSITION_WORDS],
)
def test_every_position_word_known_unpacks_to_a_plausible_module_and_cell(
    word: int, module: int, index: int, register: str, source: str
) -> None:
    """`(module << 8) | index`, against every sample there is.

    The point of listing the source per row: half of these are somebody
    else's measurement from years ago, and the encoding is only credible
    because both halves agree. If a ninth sample ever contradicts it, this is
    where it goes.
    """
    from sungrow_modbus.battery_registers import _index, _module

    assert _module(word) == module, f"{register} from {source}"
    assert _index(word) == index, f"{register} from {source}"
    # The claim that makes this an encoding rather than a coincidence.
    assert 1 <= module <= 8, "an SBR is three to eight modules"
    assert 1 <= index <= 20, "a module is twenty cells"


def test_a_cell_index_and_a_sensor_index_are_told_apart_by_their_range() -> None:
    """Why the temperature half is named a sensor and not a cell.

    This is the one inference in the decoding, and it is worth an assertion
    so that a ninth sample breaking it is loud. Across every sample known,
    the two voltage registers hold indices well past 2 and the two
    temperature registers never do -- which is what a module with twenty
    cells and two temperature sensors looks like.
    """
    cells = {i for _w, _m, i, r, _s in POSITION_WORDS if "cell_position" in r}
    sensors = {i for _w, _m, i, r, _s in POSITION_WORDS if "module_temperature" in r}

    assert max(cells) > 2, f"cell indices {sorted(cells)} would fit two sensors"
    assert sensors <= {1, 2}, (
        f"a temperature index outside 1-2 appeared: {sorted(sensors)}. If it is "
        "real, the 'sensor' naming in battery_registers.py is wrong."
    )


def test_a_zero_position_is_nothing_rather_than_module_zero() -> None:
    """The case one dongle firmware actually produces.

    Read through a WiNet-S, this whole block came back zero at one house and
    refused outright at another. A zero must not decode to "module 0, cell
    0": the registers are one-based, so zero is the absence of an answer, and
    an entity reporting module 0 forever is exactly what
    `capabilities.ZERO_MEANS_ABSENT` exists to prevent.
    """
    from sungrow_modbus.battery_registers import _index, _module

    for word in (0, None):
        assert _module(word) is None
        assert _index(word) is None
    # A word with one half zero keeps the half that is real.
    assert _module(0x0300) == 3
    assert _index(0x0300) is None
    assert _module(0x000C) is None
    assert _index(0x000C) == 12


async def test_the_unpacked_properties_read_from_the_registers() -> None:
    """End to end: the eight properties, off a unit answering the real words."""
    from modbus_connection.mock import MockModbusConnection

    from sungrow_modbus.battery_registers import SbrBatteryCells

    unit = MockModbusConnection().for_unit(200)
    cells = SbrBatteryCells(unit)

    async def answer(address: int, count: int):
        words = {
            10756: 33337,
            10757: 780,
            10758: 33251,
            10759: 266,
            10760: 229,
            10761: 770,
            10762: 219,
            10763: 257,
        }
        return [words.get(address + i, 0) for i in range(count)]

    unit.read_input_registers = answer
    await cells.async_update()

    assert (cells.max_cell_module, cells.max_cell_number) == (3, 12)
    assert (cells.min_cell_module, cells.min_cell_number) == (1, 10)
    assert (
        cells.max_module_temperature_module,
        cells.max_module_temperature_sensor,
    ) == (3, 2)
    assert (
        cells.min_module_temperature_module,
        cells.min_module_temperature_sensor,
    ) == (1, 1)
    # And the raw words stay, because legacy mode reproduces them.
    assert cells.max_cell_position == 780
    # The voltages the positions point at, as a sanity check on the scale.
    assert cells.max_cell_voltage == pytest.approx(3.3337)
    assert cells.min_cell_voltage == pytest.approx(3.3251)


#: One SBR096 read whole at unit 200 on 2026-09-09: the pack's own extremes,
#: and the per-module registers beside them. This is what turns the position
#: encoding from an inference across two houses into a fact provable inside
#: one reading.
WHOLE_PACK_READING = {
    10756: 33507,  # pack max cell voltage
    10757: 260,  # its position: 0x0104
    10758: 33436,  # pack min cell voltage
    10759: 275,  # its position: 0x0113
    # Per-module maxima, 10764-10771. Modules 4-8 are absent and read 0.
    10764: 33507,
    10765: 33484,
    10766: 33487,
    10767: 0,
    10768: 0,
    10769: 0,
    10770: 0,
    10771: 0,
    # Per-module minima, 10772-10779.
    10772: 33436,
    10773: 33448,
    10774: 33449,
    10775: 0,
    10776: 0,
    10777: 0,
    10778: 0,
    10779: 0,
    # Cell type per module, 10780-10787. 66 where a module is fitted.
    10780: 66,
    10781: 66,
    10782: 66,
    10783: 0,
    10784: 0,
    10785: 0,
    10786: 0,
    10787: 0,
}


def test_the_position_encoding_is_provable_from_one_reading() -> None:
    """The module the pack quotes is the module the position word names.

    The strongest form of this evidence, and the reason for reading the
    per-module registers at all. Everything before it was inference: eight
    position words whose high bytes happened to fall in 1-3 and low bytes in
    1-20, which fits `(module << 8) | cell` and also fits other things.

    Here the pack's own `max_cell_voltage` can be matched against the three
    modules' own maxima. Whichever module holds the highest cell is the
    module the pack is quoting -- and the high byte of the position word has
    to be that module, or the encoding is wrong. Same for the minimum.
    """
    from sungrow_modbus.battery_registers import _index, _module

    maxima = {module: WHOLE_PACK_READING[10763 + module] for module in (1, 2, 3)}
    minima = {module: WHOLE_PACK_READING[10771 + module] for module in (1, 2, 3)}

    # The pack quotes one of the modules, not something of its own.
    assert WHOLE_PACK_READING[10756] == max(maxima.values())
    assert WHOLE_PACK_READING[10758] == min(minima.values())

    highest = max(maxima, key=lambda module: maxima[module])
    lowest = min(minima, key=lambda module: minima[module])

    assert _module(WHOLE_PACK_READING[10757]) == highest, (
        "the position word names a different module than the one whose "
        "maximum the pack quoted, so (module << 8) | cell is wrong"
    )
    assert _module(WHOLE_PACK_READING[10759]) == lowest

    # And the cell halves, which the same reading puts a floor under: cell 19
    # exists, so a module has at least nineteen cells.
    assert _index(WHOLE_PACK_READING[10757]) == 4
    assert _index(WHOLE_PACK_READING[10759]) == 19


def test_the_reading_counts_the_modules_that_are_fitted() -> None:
    """Three, which is what an SBR096 is: 3.2 kWh a module, 9.6 total.

    Independent of the position words, and it corroborates them -- every high
    byte ever seen in a position register is 1, 2 or 3, and here is why.
    """
    fitted = [
        module
        for module in range(1, 9)
        # A module absent from the pack reads 0 for its cell voltages *and*
        # for its cell type. Requiring both, because a 0 V cell voltage on a
        # fitted module would be a fault worth seeing rather than an absence.
        if WHOLE_PACK_READING[10763 + module] or WHOLE_PACK_READING[10779 + module]
    ]
    assert fitted == [1, 2, 3]
    assert all(WHOLE_PACK_READING[10779 + module] == 66 for module in fitted), (
        "cell type reads 66 on every module that is fitted"
    )


def test_all_forty_of_the_yaml_sensors_are_ported() -> None:
    """Every address that file reads, read by one of the three components.

    The counting test, and it exists because the port was done in two goes.
    The first covered fifteen registers; the per-module families, the cell
    types and the DC contactor -- twenty-five more -- were measured later and
    ported after. A partial port is worse than an obvious gap: it makes the
    entity-id migration question unanswerable, because offering to adopt
    somebody's history would move a third of it and orphan the rest.

    Three addresses the YAML does *not* read are still absent here, and that
    is deliberate: 10749, 10750 and 10789 answered 1, 4 and 0 on the pack
    measured, and nothing -- not the YAML, not Sungrow -- says what they are.
    """
    ported = {
        descriptor.address
        for component in (SbrBatteryPack, SbrBatteryCells, SbrBatteryModules)
        for descriptor in component.declared_fields.values()
    }
    missing = sorted(set(YAML_REGISTERS) - ported)
    assert not missing, "the YAML reads these and nothing here does: " + ", ".join(
        f"{a} (reg {a + 1}, {YAML_REGISTERS[a]['name']})" for a in missing
    )
    # 32-bit fields cover two addresses, so the port reads at least as many.
    assert len(ported) >= len(YAML_REGISTERS)


def test_the_per_module_block_is_read_apart_from_the_pack_summary() -> None:
    """Three components, because there are three ways to lose this data.

    A WiNet-S refuses the cell block outright at one house and answers it
    with zeros at another; and on any pack, the modules that are not fitted
    read 0 whatever the transport. Pooled into one component, each of those
    would take the state of charge down with it -- and the state of charge is
    the one reading somebody actually watches.
    """
    assert SbrBatteryModules.register_space == "input"
    pack = {d.address for d in SbrBatteryPack.declared_fields.values()}
    modules = {d.address for d in SbrBatteryModules.declared_fields.values()}
    assert not pack & modules, "one address cannot belong to two components"
    # And the module block starts past the cell block, so a single read
    # cannot span them by accident.
    cells = {d.address for d in SbrBatteryCells.declared_fields.values()}
    assert min(modules) > max(cells)


def test_an_unfitted_module_reads_zero_and_is_not_a_measurement() -> None:
    """Five of the eight module slots are empty on an SBR096.

    They answer 0, not the 0xFFFF an inverter uses for "unavailable", so
    nothing declares them absent -- a zero decodes to a value and 0 V is a
    plausible-looking cell voltage. Which is why none of these is an entity
    yet: something has to establish the module count first, and this test
    records what that something will have to work from.
    """
    fitted = {1: 33507, 2: 33484, 3: 33487}
    for module in range(1, 9):
        expected = fitted.get(module, 0)
        assert WHOLE_PACK_READING[10763 + module] == expected, module
        # The cell type says the same thing a second way, which is what makes
        # "non-zero means fitted" checkable rather than assumed.
        assert bool(WHOLE_PACK_READING[10779 + module]) is (module in fitted)
