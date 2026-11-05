"""How `doc/firmware_support.md` turns a survey into a mark.

The table pools every model on one firmware, so a wrong judgement for one
survey shows up as a **split** -- a claim that the models disagree. Each case
here is one that produced a false split, or would have, when the table was
first generated from the committed surveys.
"""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "generate"))

from generate_firmware_support import (
    FIELDS,
    NO,
    NOT_FITTED,
    UNTESTED,
    YES,
    ZERO,
    PackReading,
    Reading,
    _answer,
    _capabilities,
    _cell,
    _pack_answer,
    _silent,
    _written,
)

from sungrow_modbus import Capability


def _dump(**words: list[int | None]) -> dict[str, dict[str, int | None]]:
    """Return a register dump holding these fields' words, by field name."""
    dump: dict[str, dict[str, int | None]] = {"input": {}, "holding": {}}
    for name, values in words.items():
        space, field = FIELDS[name]
        for offset, value in enumerate(values):
            dump[space][str(field.address + offset)] = value
    return dump


def _reading(
    dump: dict[str, dict[str, int | None]],
    *,
    model: str = "SH10RT",
    granted: frozenset[Capability] = frozenset(),
    parts: frozenset[str] = frozenset(),
) -> Reading:
    return Reading(
        label="test",
        model=model,
        platform="SAPPHIRE-H",
        firmware="B001.V000.P023",
        dongle=False,
        dump=dump,
        capabilities=granted,
        parts=parts,
        written=frozenset(),
    )


def _entity(field: str, requires: Capability | None = None, **extra) -> object:
    return SimpleNamespace(field=field, requires=requires, depends_on=(), **extra)


def test_a_meterless_house_is_not_fitted_rather_than_absent() -> None:
    """A cluster slave answers "unavailable" for the meter its master owns.

    The meter registers carry no `requires`, so nothing but the house's
    parts tells that apart from a firmware without the block.
    """
    dump = _dump(meter_active_power=[0xFFFF, 0x7FFF])
    entity = _entity("meter_active_power")

    assert _answer(_reading(dump), entity) == NOT_FITTED
    assert _answer(_reading(dump, parts=frozenset({"meter"})), entity) == NO


def test_an_answer_from_a_part_the_house_lacks_still_counts() -> None:
    dump = _dump(meter_active_power=[1200, 0])
    assert _answer(_reading(dump), _entity("meter_active_power")) == YES


def test_a_single_phase_output_type_withdraws_three_phase() -> None:
    """Surveys publish 5002 as words; `resolve` needs the code.

    Read as anything else, an SH-RS's phase B and C -- which answer 0 -- were
    granted by the probe and marked supported.
    """
    dump = _dump(phase_b_voltage=[0], phase_c_voltage=[0])
    document = {"device": {"device_type_code": "0x0D1B", "output_type": "single phase"}}
    granted = _capabilities(document, dump, "SUNSTONE-H_B000.V002.P067")

    assert Capability.THREE_PHASE not in granted
    entity = _entity("phase_b_voltage", Capability.THREE_PHASE)
    assert _answer(_reading(dump, granted=granted), entity) == NO


def test_a_tracker_reading_zero_cannot_be_told_from_none() -> None:
    dump = _dump(mppt3_voltage=[0], mppt3_current=[0])
    entity = _entity("mppt3_voltage", Capability.MPPT3)
    assert _answer(_reading(dump), entity) == ZERO


def test_an_idle_battery_reading_zero_is_an_answer() -> None:
    """Zero is "cannot tell" only for a capability's own probe registers."""
    dump = _dump(battery_min_soc=[0])
    entity = _entity("battery_min_soc", Capability.BATTERY)
    granted = frozenset({Capability.BATTERY})

    assert _answer(_reading(dump, granted=granted), entity) == YES
    assert _answer(_reading(dump), entity) == NOT_FITTED


def test_what_a_dump_cannot_read_is_untested() -> None:
    """The masked serial and a padded frame are no evidence about the device."""
    serial = _dump(sungrow_inverter_serial=[None] * 10)
    padded = _dump(sungrow_version_3=[None] * 15)

    assert _answer(_reading(serial), _entity("sungrow_inverter_serial")) == UNTESTED
    assert _answer(_reading(padded), _entity("sungrow_version_3")) == UNTESTED
    assert _answer(_reading(_dump()), _entity("mppt3_voltage")) == UNTESTED


def test_a_cell_splits_only_on_evidence() -> None:
    def reading(model: str) -> Reading:
        return _reading(_dump(), model=model)

    agree = [(reading("SH10RT"), YES), (reading("SH8.0RT"), NOT_FITTED)]
    assert _cell(agree, write=False) == "✓"
    assert _cell(agree, write=True) == "✓ W"

    split = [(reading("SH10RT"), YES), (reading("SH8.0RT"), NO)]
    assert _cell(split, write=False) == "**split**: ✓ SH10RT; ✗ SH8.0RT"

    assert _cell([(reading("SH10RT"), UNTESTED)], write=False) == ""


def test_a_dongle_read_back_confirms_no_write() -> None:
    """Through a WiNet-S a read-back can be stale; only the effect is evidence."""
    document = {
        "control_test": {
            "conditions": {},
            "readback": [{"field": "battery_min_soc", "verdict": "matched"}],
        }
    }
    assert _written(document, dongle=False) == {"battery_min_soc"}
    assert _written(document, dongle=True) == frozenset()


def _pack(values: dict[str, object], silent: list[str] | None = None) -> PackReading:
    return PackReading(
        label="test",
        model="SBR096",
        platform="SBRBCU-S",
        firmware="22011.01.30",
        dongle=False,
        values=values,
        silent=_silent({"components_that_did_not_answer": silent or []}),
    )


def test_a_pack_refusal_is_absent_and_a_lost_link_is_untested() -> None:
    """A dongle's unit 2 refuses the cell block with an exception: an answer.

    A connection lost, or an older survey that recorded no exception type,
    says nothing about the register.
    """
    cell = SimpleNamespace(component="cells", field="max_cell_voltage")

    refused = _pack({}, ["sbr_battery_cells (IllegalDataAddressError)"])
    lost = _pack({}, ["sbr_battery_cells (ModbusConnectionError)"])
    busy = _pack({}, ["sbr_battery_cells (ServerDeviceBusyError)"])
    untyped = _pack({}, ["sbr_battery_cells"])

    assert _pack_answer(refused, cell) == NO
    assert _pack_answer(lost, cell) == UNTESTED
    assert _pack_answer(busy, cell) == UNTESTED
    assert _pack_answer(untyped, cell) == UNTESTED


def test_an_empty_module_slot_is_not_fitted() -> None:
    """A three-module pack reads 0 V in slot 4; its cell type names it empty."""
    values = {
        "max_cell_voltage_module_3": 3.30,
        "cell_type_module_3": 68,
        "max_cell_voltage_module_4": 0.0,
        "cell_type_module_4": 0,
    }

    def slot(n: int) -> object:
        return SimpleNamespace(
            component="modules", field=f"max_cell_voltage_module_{n}"
        )

    assert _pack_answer(_pack(values), slot(3)) == YES
    assert _pack_answer(_pack(values), slot(4)) == NOT_FITTED
    assert _pack_answer(_pack(values), slot(5)) == UNTESTED
