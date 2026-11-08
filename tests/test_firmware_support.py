"""How `doc/firmware_support.md` turns a diagnosis into a mark.

The table pools every model on one firmware, so a wrong judgement for one
diagnosis shows up as a **split** -- a claim that the models disagree. Each case
here is one that produced a false split, or would have, when the table was
first generated from the committed diagnoses.
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
    READ,
    TIMES_TEN,
    UNTESTED,
    WATCHED,
    WRITABLE,
    WRITTEN,
    YES,
    ZERO,
    PackReading,
    Reading,
    _agreed,
    _answer,
    _capabilities,
    _cell,
    _columns,
    _coverage,
    _export_factor,
    _pack_answer,
    _readings,
    _rows,
    _silent,
    _tally,
    _written,
)

from sungrow_modbus import Capability
from sungrow_modbus.capability_test import coverage
from sungrow_modbus.capability_test.procedure import NOT_PROBED


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
    """Diagnoses publish 5002 as words; `resolve` needs the code.

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
        "capability_test": {
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

    A connection lost, or an older diagnosis that recorded no exception type,
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


def test_the_diagnosis_column_follows_the_capability_tests_own_tables() -> None:
    """A writable entity is written, watched, or deliberately left out.

    The column reads `PROBES` and `EFFECT_FIELDS` themselves, so a control the
    procedure starts writing shows up here without anybody editing the page.
    """
    by_field = {
        getattr(description, "field", None): (domain, description)
        for _topic, domain, _name, description in _rows()
        if domain in WRITABLE
    }
    for field in coverage.WRITTEN:
        domain, description = by_field[field]
        assert WRITTEN in _coverage(domain, description).split(" + "), field
    for field, (domain, description) in by_field.items():
        levels = _coverage(domain, description).split(" + ")
        assert levels[0] == READ, field
        if field in coverage.WATCHED:
            assert WATCHED in levels, field
        assert field in coverage.WRITTEN | coverage.WATCHED | set(NOT_PROBED), field


def test_every_behavioural_check_named_is_one_the_procedure_runs() -> None:
    """`EFFECT_FIELDS` is keyed by `EffectResult.check`; a typo would hide a row."""
    source = (REPO / "src/sungrow_modbus/capability_test/effects.py").read_text(
        encoding="utf-8"
    )
    for check in coverage.EFFECT_FIELDS:
        assert f'"{check}"' in source, check


def test_a_padded_or_masked_field_is_not_read_by_the_dump() -> None:
    assert _coverage("sensor", _entity("sungrow_version_3")) == ""
    assert _coverage("sensor", _entity("sungrow_inverter_serial")) == ""
    assert _coverage("sensor", _entity("meter_active_power")) == READ
    assert (
        _coverage("sensor", _entity("site_import_power_limit")) == f"{READ} + {WATCHED}"
    )


def test_the_export_write_scale_is_taken_from_either_block() -> None:
    reading = _reading(_dump())
    asked = Reading(**{**vars(reading), "export_scale": {"write_units_per_count": 10}})
    carried = Reading(
        **{
            **vars(reading),
            "capability_test": {
                "conditions": {"export_write_scale": {"write_units_per_count": 1}}
            },
        }
    )
    unknown = Reading(
        **{**vars(reading), "export_scale": {"write_units_per_count": None}}
    )
    assert _export_factor(asked) == 10
    assert _export_factor(carried) == 1
    assert _export_factor(unknown) is None
    assert _agreed([(asked, TIMES_TEN), (carried, TIMES_TEN)]) == TIMES_TEN
    assert _agreed([]) == ""


def test_a_behaviour_cell_counts_each_verdict() -> None:
    verdicts = [
        "the inverter did as it was told",
        "could not tell",
        "the inverter did as it was told",
    ]
    assert _tally(verdicts) == "✓ 2, ? 1"
    assert _tally([]) == ""


def test_13074_writes_x10_on_b001_and_as_handed_on_the_older_firmware() -> None:
    """The measurement the page carries, against the published diagnoses.

    `.wiki/wiki/entities/register-13074.md`: x10 on B001 firmware, 1:1 on
    `SAPPHIRE-H_01011.95.03`.
    """
    readings, _skipped = _readings()
    factors: dict[str, set[int]] = {}
    for column, members in _columns(readings).items():
        if column.platform != "SAPPHIRE-H":
            continue
        found = {f for r in members if (f := _export_factor(r)) is not None}
        if found:
            factors.setdefault(column.firmware, set()).update(found)
    assert factors["01011.95.03"] == {1}
    for firmware in ("B001.V000.P020", "B001.V000.P022", "B001.V000.P023"):
        assert factors[firmware] == {10}, firmware
