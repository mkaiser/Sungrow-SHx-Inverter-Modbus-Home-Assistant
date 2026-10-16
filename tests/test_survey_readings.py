"""What the survey reads and publishes, driven against in-memory devices.

`probe._async_decoded_readings` is every register the integration reads,
decoded through the library, and `probe._async_battery_readings` the SBR's
own blocks. A fingerprint's value is read by comparing it against other
fingerprints, so what these report -- and what they leave out -- is part of
the format: a component missed has to be said, a serial never.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "device-fingerprints" / "scripts" / "python"))

from probe import _async_decoded_readings  # noqa: E402

from sungrow_modbus.block_test import inverter_blocks  # noqa: E402
from sungrow_modbus.fingerprint import NEVER_PUBLISH  # noqa: E402

#: Every read the poll makes, recorded once: `_filled_unit` is also called
#: from inside a running loop, where recording again could not start one.
BLOCKS = asyncio.run(inverter_blocks())
SEED = json.loads((REPO / "scripts" / "dev" / "simulator_registers.json").read_text())


def _seeded_unit():
    """Return a mock unit answering like the simulator does.

    The same seed `scripts/dev/simulate.sh` serves, so this is the inverter both
    paths are compared against -- and it covers every ported address, because
    `generate_simulator_registers.py` derives it from the YAML package.
    """
    unit = MockModbusConnection().for_unit(1)
    unit.input = {int(a): v for a, v in SEED.get("input", {}).items()}
    unit.holding = {int(a): v for a, v in SEED.get("holding", {}).items()}
    return unit


def _filled_unit():
    """Return a unit that answers every address the poll reads.

    The mock refuses an address it was not seeded with, and the seed covers
    the addresses the YAML package ports rather than every address a *block*
    spans -- so on `_seeded_unit` every one of the 13 components misses as a
    whole and all 92 values come from the field-by-field salvage. That is a
    faithful reproduction of gerd's inverter and it is worth testing, but on
    its own it would leave the block path -- the normal one, and the one that
    has to slice a field out of a pooled read -- unexercised.
    """
    unit = _seeded_unit()
    for block in BLOCKS:
        store = unit.input if block.space == "input" else unit.holding
        for offset in range(block.count):
            store.setdefault(block.address + offset, 0)
    return unit


def test_a_gappy_device_still_yields_a_reading() -> None:
    """Every component misses on the seed, and salvage recovers the fields."""

    async def run() -> dict:
        return await _async_decoded_readings(_seeded_unit(), 1)

    readings = asyncio.run(run())
    answered = [v for v in readings["values"].values() if v is not None]
    assert len(answered) > 80, f"only {len(answered)} fields answered"


@pytest.mark.parametrize("device", [_seeded_unit, _filled_unit], ids=["gappy", "whole"])
def test_the_readings_never_report_a_serial(device) -> None:
    """The rule the whole document is built around.

    A sweep of the register map walks straight into a field that holds the
    real serial, so it is dropped by name -- from the values and from both
    lists of field names.
    """

    async def run() -> dict:
        return await _async_decoded_readings(device(), 1)

    readings = asyncio.run(run())
    named = [
        *readings["values"],
        *readings.get("fields_read_individually", []),
        *readings.get("fields_that_did_not_read", []),
    ]
    leaked = [name for name in named if any(w in name for w in NEVER_PUBLISH)]
    assert not leaked, leaked


def test_a_component_that_never_answers_is_reported_not_hidden() -> None:
    """A miss has to be visible: an empty field looks the same as a zero."""

    async def run() -> dict:
        unit = _seeded_unit()
        # A component that is not fitted refuses. The library's own
        # `ModbusError` and not a stand-in, because it derives from plain
        # `Exception` -- a handler written for `OSError` lets it escape.
        for address in range(13199, 13215):
            unit.fail_read(
                address,
                ModbusError("illegal data address"),
                register_type="input",
            )
        return await _async_decoded_readings(unit, 1)

    readings = asyncio.run(run())
    assert "meter_channel_2" in readings["components_that_did_not_answer"]
    assert readings["fields_that_did_not_read"], (
        "the field-by-field salvage should have recorded what it could not read"
    )


def test_a_device_that_answers_everything_reports_nothing_missed() -> None:
    """The regression that produced a wrong document from a healthy inverter.

    The loop kept `pending` from the pass it was entering rather than
    the pass's own failures, so a device that answered every component on the
    first attempt was reported as having missed **all of them** -- and then
    had all 104 fields re-read one at a time, which succeeded, so the values
    were right and only the two lists lied.

    That is the shape of bug this file exists for: it published a claim about
    somebody's inverter (gerd's direct-LAN fingerprint said no component
    answered as a whole) that came from this code and not from the wire.
    """
    report = asyncio.run(_async_decoded_readings(_filled_unit(), 1))
    assert report["components_that_did_not_answer"] == []
    assert "fields_read_individually" not in report
    assert "fields_that_did_not_read" not in report


def test_the_library_reads_without_printing_and_reports_through_callbacks(
    capsys,
) -> None:
    """The algorithm lives in the library, so it may say nothing itself.

    Home Assistant has no terminal, and a library that printed would put a
    survey's progress into a user's log. Everything a person sees comes back
    through the callbacks, for the caller to draw.
    """
    from sungrow_modbus.inverter.registers import COMPONENTS
    from sungrow_modbus.survey import async_decoded_readings

    components: list[str] = []
    done: list[tuple[int, int]] = []
    report = asyncio.run(
        async_decoded_readings(
            _filled_unit(),
            passes=1,
            on_component=components.append,
            on_passes_done=lambda answered, total: done.append((answered, total)),
        )
    )

    assert capsys.readouterr().out == ""
    assert components == list(COMPONENTS)
    assert done == [(len(COMPONENTS), len(COMPONENTS))]
    assert report["components_that_did_not_answer"] == []


#: What one SBR096 actually said, read on 2026-09-09 at unit 200 over the
#: inverter's own LAN port -- the only path that answers the cell block at
#: all. Used instead of the simulator seed because the seed has none of these
#: addresses and `scripts/dev/simulate.sh` serves a single unit id, so it cannot
#: stand in for a pack on unit 200 beside an inverter on unit 1. Real words
#: are the better fixture anyway: these are the numbers a document has to
#: come out of.
SBR_WORDS = {
    10740: 1993,  # 199.3 V
    10741: 4,  # 0.4 A, charging
    10742: 225,  # 22.5 C
    10743: 1000,  # 100.0 %
    10744: 96,  # 96 % state of health
    10745: 58021,  # total charge, low word first
    10746: 0,
    10747: 54275,  # total discharge
    10748: 0,
    10756: 33337,  # 3.3337 V highest cell
    10757: 780,  # module 3, cell 12
    10758: 33251,  # 3.3251 V lowest cell
    10759: 266,  # module 1, cell 10
    10760: 229,  # 22.9 C warmest module
    10761: 770,  # module 3, sensor 2
    10762: 219,  # 21.9 C coolest module
    10763: 257,  # module 1, sensor 1
    # The per-module block, same reading. Modules 1-3 are fitted; 4-8 are
    # not, and answer 0 rather than the 0xFFFF an inverter uses for
    # "unavailable" -- which is why none of these is an entity yet.
    10764: 33507,
    10765: 33484,
    10766: 33487,
    10772: 33436,
    10773: 33448,
    10774: 33449,
    10780: 66,
    10781: 66,
    10782: 66,
    10788: 2,
}
SBR_WORDS.update(
    dict.fromkeys([*range(10767, 10772), *range(10775, 10780), *range(10783, 10788)], 0)
)


def _pack_unit(unit_id: int = 200):
    """Return a mock unit answering as that SBR did."""
    unit = MockModbusConnection().for_unit(unit_id)
    unit.input = dict(SBR_WORDS)
    unit.holding = {}
    return unit


def test_the_battery_pack_decodes_to_what_the_pack_said() -> None:
    """Scales, sentinels and word order, against one SBR096's real words."""
    library = asyncio.run(_battery_via_library())

    assert library["components_that_did_not_answer"] == []
    values = library["values"]
    assert values["voltage"] == pytest.approx(199.3)
    assert values["current"] == pytest.approx(0.4)
    assert values["state_of_charge"] == pytest.approx(100.0)
    assert values["state_of_health"] == 96
    assert values["max_cell_voltage"] == pytest.approx(3.3337)
    assert values["min_cell_voltage"] == pytest.approx(3.3251)
    # Low word first, which is the mistake this fixture would catch: read the
    # other way round a 5.8 MWh counter reads as 3.8 GWh.
    assert values["total_charge"] == pytest.approx(5802.1)
    assert values["total_discharge"] == pytest.approx(5427.5)


async def _battery_via_library():
    """Drive `probe._async_battery_readings` against the same words."""
    from probe import _async_battery_readings

    class _Connection:
        def for_unit(self, unit_id):
            return _pack_unit(unit_id)

    return await _async_battery_readings(_Connection(), 200)


def test_the_position_words_are_unpacked() -> None:
    """The eight halves, which are the reason for carrying this at all.

    A document holding 780 makes a reader ask what cell 780 is; one holding
    module 3, cell 12 does not.
    """
    library = asyncio.run(_battery_via_library())
    values = library["values"]

    assert (values["max_cell_module"], values["max_cell_number"]) == (3, 12)
    assert (values["min_cell_module"], values["min_cell_number"]) == (1, 10)
    assert (
        values["max_module_temperature_module"],
        values["max_module_temperature_sensor"],
    ) == (3, 2)
    assert (
        values["min_module_temperature_module"],
        values["min_module_temperature_sensor"],
    ) == (1, 1)
    # And the raw word stays, so a reader who disputes the encoding can check.
    assert values["max_cell_position"] == 780


def test_a_cell_block_a_dongle_refuses_leaves_the_pack_summary_intact() -> None:
    """Measured at fwitten: through a WiNet-S the cells refuse 0x02.

    The two are separate components for this reason. Pooled into one read a
    refusal would take the state of charge with it, and a house on a dongle
    would get a document saying its battery was unreadable when only half of
    it was.
    """

    class _Refusing:
        """Answers the pack block and refuses the cell block, as it did."""

        def __init__(self, unit_id):
            self._inner = _pack_unit(unit_id)

        async def read_input_registers(self, address, count):
            if address >= 10756:
                raise ModbusError("Modbus Exception 0x02 for function code 0x04")
            return await self._inner.read_input_registers(address, count)

        async def read_holding_registers(self, address, count):
            raise ModbusError("Modbus Exception 0x02 for function code 0x04")

    class _Connection:
        def for_unit(self, unit_id):
            return _Refusing(unit_id)

    from probe import _async_battery_readings

    result = asyncio.run(_async_battery_readings(_Connection(), 2))

    assert result["values"]["state_of_charge"] == pytest.approx(100.0)
    assert result["values"]["state_of_health"] == 96
    assert "max_cell_voltage" not in result["values"]
    assert any(
        "sbr_battery_cells" in missed
        for missed in result["components_that_did_not_answer"]
    ), result["components_that_did_not_answer"]


def test_a_cell_block_a_dongle_zeroes_becomes_nothing_not_module_zero() -> None:
    """Measured at bar12: the *other* dongle firmware answers zeros instead.

    Which is the more dangerous of the two, because a zero decodes to a
    value. The pack-level fields must still read true, and every cell field
    must come back as an absence rather than as "module 0, cell 0" -- an
    entity reporting module 0 forever is what `ZERO_MEANS_ABSENT` exists to
    prevent, and here it is the property of `_module`/`_index` that does it.
    """

    class _Connection:
        def for_unit(self, unit_id):
            unit = MockModbusConnection().for_unit(unit_id)
            # Zeros where the cell block is, real words for the pack.
            unit.input = {a: (w if a < 10756 else 0) for a, w in SBR_WORDS.items()}
            unit.holding = {}
            return unit

    from probe import _async_battery_readings

    result = asyncio.run(_async_battery_readings(_Connection(), 2))
    values = result["values"]

    assert values["state_of_charge"] == pytest.approx(100.0)
    assert values["voltage"] == pytest.approx(199.3)
    for name in (
        "max_cell_module",
        "max_cell_number",
        "min_cell_module",
        "min_cell_number",
        "max_module_temperature_module",
        "max_module_temperature_sensor",
    ):
        assert values[name] is None, f"{name} decoded a zero into a position"
