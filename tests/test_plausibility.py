"""The readings' plausibility checks, on a synthetic house and on the corpus.

The house is made up: a bell of PV, a steady load, a battery that soaks up
surplus and covers the night. Every reading is derived from the same flows,
so a consistent house passes every check, and a decade put into one field
must turn up as that check's finding and nowhere else.

The last section is not synthetic. `lifetime battery counters contain each
other` judges one poll, so every committed diagnosis can be put through it,
and that is the only way to know what it does to eighty-nine real houses.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import json
import math
from typing import Any

import pytest

from sungrow_modbus.capability_test import ledger, plausibility
from sungrow_modbus.capability_test.plausibility import Plausibility
from sungrow_modbus.capability_test.procedure import (
    INCONCLUSIVE,
    MATCH,
    NO_EFFECT,
    OFF_BY,
    SCALED,
    SIGN_INVERTED,
)

from .corpus import INVERTER_DOCUMENTS

START = datetime(2026, 6, 1, 0, 1, tzinfo=UTC)
CAPACITY_KWH = 10.0
Values = dict[str, float | None]


def _house(
    minutes: int = 2 * 1440, start: datetime = START
) -> list[tuple[datetime, Values]]:
    """Return a poll a minute: two summer days, starting just after midnight."""
    polls = []
    daily = dict.fromkeys(plausibility.DAILY, 0.0)
    totals = dict.fromkeys(plausibility.TOTALS, 1000.0)
    soc = 50.0
    for minute in range(minutes):
        at = start + timedelta(minutes=minute)
        if minute and at.hour == 0 and at.minute == 0:
            daily = dict.fromkeys(plausibility.DAILY, 0.0)
        hour = at.hour + at.minute / 60
        pv = (
            max(0.0, 6000.0 * math.sin(math.pi * (hour - 6) / 14))
            if 6 < hour < 20
            else 0.0
        )
        load = 700.0 + 200.0 * math.sin(minute / 7)
        surplus = pv - load
        battery = -min(surplus, 3000.0) if surplus > 0 else min(-surplus, 300.0)
        if (soc >= 95 and battery < 0) or (soc <= 10 and battery > 0):
            battery = 0.0
        export = pv + battery - load
        hours = 1 / 60
        flows = {
            "daily_pv_generation": pv,
            "daily_imported_energy": max(-export, 0.0),
            "daily_exported_energy": max(export, 0.0),
            "daily_battery_charge": max(-battery, 0.0),
            "daily_battery_discharge": max(battery, 0.0),
            "daily_exported_energy_from_pv": max(export, 0.0),
            "daily_battery_charge_from_pv": max(-battery, 0.0),
            "daily_direct_energy_consumption": min(pv, load),
        }
        for (name, watts), total in zip(
            flows.items(), plausibility.TOTALS, strict=True
        ):
            daily[name] += watts * hours / 1000
            totals[total] += watts * hours / 1000
        soc -= battery * hours / 1000 / CAPACITY_KWH * 100
        output = pv + battery
        values: Values = {
            "running_state_raw": 0x0040,
            "load_power": load,
            "total_dc_power": pv,
            "battery_power": battery,
            "export_power_raw": export,
            "battery_voltage": 400.0,
            "battery_current": battery / 400.0,
            "battery_level": round(soc, 1),
            "mppt1_voltage": 350.0 if pv else 0.0,
            "mppt1_current": pv / 2 / 350.0,
            "mppt2_voltage": 350.0 if pv else 0.0,
            "mppt2_current": pv / 2 / 350.0,
            "mppt3_voltage": None,
            "mppt3_current": None,
            "total_active_power": output,
            "meter_active_power": -export,
            "meter_phase_a_active_power": -export / 3,
            "meter_phase_b_active_power": -export / 3,
            "meter_phase_c_active_power": -export / 3,
        }
        for phase in "abc":
            values[f"phase_{phase}_voltage"] = 230.0
            values[f"phase_{phase}_current"] = output / 3 / 230.0
        # The registers hold 0.1 kWh.
        values.update({k: math.floor(v * 10) / 10 for k, v in daily.items()})
        values.update({k: math.floor(v * 10) / 10 for k, v in totals.items()})
        polls.append((at, values))
    return polls


def _run(
    change: Callable[[datetime, Values], None] | None = None, **kwargs: Any
) -> dict[str, dict[str, Any]]:
    collection = Plausibility()
    for at, values in _house(**kwargs):
        if change is not None:
            change(at, values)
        collection.observe(values, at)
    return collection.summary()


def test_a_consistent_house_passes_every_check() -> None:
    """Every check that applies reaches a match, and nothing else."""
    summary = _run()
    verdicts = {name: row["verdict"] for name, row in summary.items()}
    assert set(verdicts.values()) == {MATCH}, verdicts
    # MPPT3 reads None throughout: absent, not waiting.
    assert "mppt3 carries a string" not in summary
    assert "power balance" in summary
    assert all(row["kind"] == plausibility.KIND for row in summary.values())


def test_the_kind_is_the_ledgers() -> None:
    """The ledger marks plausibility rows with this module's word."""
    assert plausibility.KIND == ledger.PLAUSIBILITY


@pytest.mark.parametrize(
    ("field", "factor", "check"),
    [
        ("battery_voltage", 10.0, "battery voltage times current"),
        ("mppt1_current", 0.1, "tracker voltage times current"),
        ("phase_a_voltage", 10.0, "phase voltage times current"),
    ],
)
def test_a_decade_in_one_field_is_its_checks_finding(
    field: str, factor: float, check: str
) -> None:
    """A field off by ten shows as a factor on the check that reads it."""

    def scale(_at: datetime, values: Values) -> None:
        if values[field] is not None:
            values[field] = values[field] * factor  # type: ignore[operator]

    if field == "mppt1_current":
        # Both trackers, so the whole sum is a decade off.
        def scale(_at: datetime, values: Values) -> None:
            for name in ("mppt1_current", "mppt2_current"):
                values[name] = values[name] * factor  # type: ignore[operator]

    if field == "phase_a_voltage":

        def scale(_at: datetime, values: Values) -> None:
            for phase in "abc":
                name = f"phase_{phase}_voltage"
                values[name] = values[name] * factor  # type: ignore[operator]

    row = _run(scale)[check]
    assert row["verdict"] == SCALED
    assert f"a factor of {factor:g}" in row["detail"]


def test_a_daily_counter_a_decade_low_is_found_against_its_power() -> None:
    """Imported energy read at a tenth shows against the import power."""

    def scale(_at: datetime, values: Values) -> None:
        values["daily_imported_energy"] = values["daily_imported_energy"] * 10  # type: ignore[operator]

    summary = _run(scale)
    assert summary["daily_imported_energy against power"]["verdict"] == SCALED


def test_a_total_a_decade_off_is_found_against_its_daily_counter() -> None:
    """A lifetime counter read ten times too large."""

    def scale(_at: datetime, values: Values) -> None:
        values["total_pv_generation"] = values["total_pv_generation"] * 10  # type: ignore[operator]

    row = _run(scale)["total_pv_generation against daily_pv_generation"]
    assert row["verdict"] == SCALED


def test_a_meter_whose_phases_disagree_in_sign_is_a_finding() -> None:
    """Phases with the opposite sign to the total."""

    def flip(_at: datetime, values: Values) -> None:
        for phase in "abc":
            name = f"meter_phase_{phase}_active_power"
            values[name] = -values[name]  # type: ignore[operator]

    assert _run(flip)["meter phases add up"]["verdict"] == SIGN_INVERTED


def test_a_balance_that_is_merely_off_is_a_question_not_a_failure() -> None:
    """Losses of a third are not a decade: inconclusive, never a finding."""

    def lossy(_at: datetime, values: Values) -> None:
        values["load_power"] = values["load_power"] * 0.6  # type: ignore[operator]

    assert _run(lossy)["power balance"]["verdict"] == INCONCLUSIVE


def test_a_lifetime_counter_that_falls_is_named() -> None:
    """One fall is enough, and the sentence says which counter and how far."""

    def fall(at: datetime, values: Values) -> None:
        if at == START + timedelta(hours=13):
            values["total_imported_energy"] = 1.0

    row = _run(fall)["lifetime counters never fall"]
    assert row["verdict"] == OFF_BY
    assert "total_imported_energy fell" in row["detail"]


def test_a_reset_at_noon_is_a_finding() -> None:
    """A daily counter that falls away from midnight."""

    def reset(at: datetime, values: Values) -> None:
        if at.date() == START.date() and at.hour >= 12:
            values["daily_pv_generation"] = 0.0

    row = _run(reset)["daily counters reset at midnight"]
    assert row["verdict"] == OFF_BY
    assert "12:00" in row["detail"]


def test_a_midnight_reset_records_every_counter_that_fell() -> None:
    """The passing check still says what it saw: all of them, at once."""
    row = _run()["daily counters reset at midnight"]
    assert row["verdict"] == MATCH
    detail = row["detail"]
    assert "the rest at zero" in detail
    for name in plausibility.DAILY:
        assert name.removeprefix("daily_") in detail, detail


def test_a_staggered_midnight_reset_names_what_had_not_reset_yet() -> None:
    """Two counters reset a poll late: the moment #708 reads as negative.

    What is measured here is the device's, not the integration's: whether a
    poll can fall between two of the eight resets. `daily_consumed_energy`
    adds five of them up, so such a poll is the one that reads deeply
    negative, and this sentence is the evidence that it happened.
    """
    late = ("daily_exported_energy", "daily_battery_charge")
    held: Values = {}

    def stagger(at: datetime, values: Values) -> None:
        if at.hour == 23 and at.minute == 59:
            held.update({name: values[name] for name in late})
        elif at.hour == 0 and at.minute == 0 and held:
            values.update(held)

    row = _run(stagger)["daily counters reset at midnight"]
    assert row["verdict"] == MATCH
    detail = row["detail"]
    assert "exported_energy" in detail and "battery_charge" in detail
    assert "did not" in detail, detail


def test_a_note_is_reported_behind_a_failure() -> None:
    """A check that has failed is where its measurement is worth most.

    The failure here is the one a clock mismatch produces at a real house:
    the row stays red for as long as the clocks differ, and the nightly
    reset would go unrecorded if a note only spoke on a pass.
    """

    def reset(at: datetime, values: Values) -> None:
        if at.date() == START.date() and at.hour >= 12:
            values["daily_pv_generation"] = 0.0

    row = _run(reset)["daily counters reset at midnight"]
    assert row["verdict"] == OFF_BY
    assert "fell at 12:00" in row["detail"]
    assert "reset at 00:00" in row["detail"], row["detail"]


def test_the_battery_level_running_backwards_is_a_finding() -> None:
    """A level that rises while the battery discharges."""

    def backwards(_at: datetime, values: Values) -> None:
        values["battery_level"] = 100 - values["battery_level"]  # type: ignore[operator]

    assert _run(backwards)["battery level follows its power"]["verdict"] == OFF_BY


def test_an_unknown_running_state_is_named() -> None:
    """A code the table does not have."""

    def odd(at: datetime, values: Values) -> None:
        if at.hour == 3:
            values["running_state_raw"] = 0x7777

    row = _run(odd)["running states"]
    assert row["verdict"] == OFF_BY
    assert "0x7777" in row["detail"]


def test_a_third_tracker_at_zero_in_daylight_has_no_string() -> None:
    """Granted on a voltage that is not 0xFFFF, and 0 V all day."""

    def empty(_at: datetime, values: Values) -> None:
        values["mppt3_voltage"] = 0.0
        values["mppt3_current"] = 0.0

    assert _run(empty)["mppt3 carries a string"]["verdict"] == NO_EFFECT


def test_a_gap_breaks_the_trails_instead_of_bridging_them() -> None:
    """Polls missing for an hour (a capability test, a restart) count nothing."""
    collection = Plausibility()
    polls = _house(minutes=600)
    for at, values in polls[:300] + polls[360:]:
        collection.observe(values, at)
    # A trail across the gap would have integrated nothing for an hour and
    # reported the counter several times too high.
    row = collection.summary()["daily_pv_generation against power"]
    assert row["verdict"] in (None, MATCH)


def test_the_state_survives_a_round_trip() -> None:
    """What is kept is what was seen."""
    collection = Plausibility()
    for at, values in _house(minutes=1440):
        collection.observe(values, at)
    again = Plausibility.from_dict(collection.as_dict())
    assert again.summary() == collection.summary()
    assert again.observations == collection.observations


def test_a_state_of_another_schema_starts_again() -> None:
    """Nothing is half-loaded."""
    assert Plausibility.from_dict({"schema": 0, "observations": 5}).observations == 0
    assert Plausibility.from_dict(None).observations == 0


def test_the_document_carries_no_readings() -> None:
    """Verdicts and counts only."""
    collection = Plausibility()
    for at, values in _house(minutes=120):
        collection.observe(values, at)
    document = collection.document()
    assert set(document) == {"schema", "observations", "first", "last", "checks"}
    assert "ratios" not in str(document)


def test_rows_join_the_ledger_without_starting_runs() -> None:
    """Counted with the writes; never awaited by auto repeat."""
    rows = _run(minutes=60)
    unsettled = [name for name, row in rows.items() if not row["established"]]
    assert unsettled
    merged = ledger.with_plausibility(None, rows)
    assert merged is not None
    _, total = ledger.progress(merged)
    assert total == len(rows)
    assert sum(ledger.counts(merged).values()) == total
    assert ledger.awaited(merged) == []
    assert not ledger.established(merged)
    assert {item["name"] for item in merged["still_missing"]} == set(unsettled)
    assert "Still waiting for" in ledger.markdown(merged)


def test_every_field_a_check_reads_is_collected() -> None:
    """A driver collecting `FIELDS` gives every check what it reads."""
    for check in plausibility.checks():
        assert set(check.fields) <= set(plausibility.FIELDS), check.name


# -- lifetime battery counters contain each other ------------------------------

CONTAINMENT = "lifetime battery counters contain each other"


def test_a_lifetime_charge_below_what_it_contains_is_a_finding() -> None:
    """A whole that has fallen below its own part: the P067 fault's shape.

    `total_battery_charge`'s high word is a wrap short, so the counter reads
    far below the charge-from-PV and the discharge it has to contain. Here
    the whole is cut by a sixth, well past the 10 % margin.
    """

    def short(_at: datetime, values: Values) -> None:
        values["total_battery_charge"] = values["total_battery_charge"] / 1.2  # type: ignore[operator]

    row = _run(short)[CONTAINMENT]
    assert row["verdict"] == OFF_BY
    assert "total_battery_charge_from_pv reads" in row["detail"]
    assert "broken word" in row["detail"]


def test_a_counter_a_few_per_cent_out_is_not_a_finding() -> None:
    """Four honest machines in the corpus cross the line, none by more than 5 %.

    Sungrow's own bookkeeping puts `total_battery_charge_from_pv` above
    `total_battery_charge` by up to 2.06 % (icefest's), so anything inside the
    margin has to pass or the check would report four working houses.
    """

    def slightly(_at: datetime, values: Values) -> None:
        values["total_battery_charge"] = values["total_battery_charge"] / 1.05  # type: ignore[operator]

    assert _run(slightly)[CONTAINMENT]["verdict"] == MATCH


def test_counters_under_the_floor_are_not_judged() -> None:
    """A house in its first weeks, where a tenth of a kWh is a percentage.

    biergitkraft's reads 4.8 kWh charged against 5.0 discharged, which is
    4.17 % out and still nothing at all. The row stays, saying what it is
    waiting for -- the counters read, so the check applies to this house; it
    is the readings that are too small to judge.
    """

    def tiny(_at: datetime, values: Values) -> None:
        values["total_battery_charge"] = 4.8
        values["total_battery_charge_from_pv"] = 5.0
        values["total_battery_discharge"] = 5.0

    row = _run(tiny)[CONTAINMENT]
    assert row["verdict"] is None
    assert row["needs"] == "100 kWh through the battery"


def test_the_check_is_settled_by_one_run_of_a_diagnosis() -> None:
    """Three polls a minute apart, which is what a diagnosis takes.

    Every other check here wants hours or days. This one is arithmetic
    between registers read together, so a diagnosis settles it where it
    stands -- which is how the corpus answered it for three machines nobody
    can visit.
    """
    collection = Plausibility()
    for minute in range(3):
        at = START + timedelta(minutes=minute)
        collection.observe(
            {
                "total_battery_charge": 6374.1,
                "total_battery_charge_from_pv": 12574.5,
                "total_battery_discharge": 12708.0,
            },
            at,
        )
    assert collection.summary()[CONTAINMENT]["verdict"] == OFF_BY


# -- the same check, over every committed diagnosis ----------------------------


def _containment_verdict(values: dict[str, Any]) -> tuple[str | None, str]:
    """Return what the check makes of one document's readings."""
    collection = Plausibility()
    for minute in range(3):
        collection.observe(values, START + timedelta(minutes=minute))
    row = collection.summary().get(CONTAINMENT)
    return (None, "") if row is None else (row["verdict"], row["detail"])


def _corpus_verdicts() -> dict[str, tuple[str | None, str]]:
    """Run the check over every inverter document in the corpus."""
    out: dict[str, tuple[str | None, str]] = {}
    for path in INVERTER_DOCUMENTS:
        document = json.loads(path.read_text(encoding="utf-8"))
        values = (document.get("readings") or {}).get("values") or {}
        out[path.name] = _containment_verdict(
            {
                name: value
                for name, value in values.items()
                if value is None or isinstance(value, (int, float))
            }
        )
    return out


def test_the_check_finds_exactly_the_two_machines_that_read_plausibly() -> None:
    """bigz2012's and brendan's, and no honest house anywhere in the corpus.

    Both are SH-RS on SUNSTONE-H_B000.V002.P067, both read a counter a house
    could have -- 14,844.2 and 6,374.1 kWh -- and both are a whole wrap of
    6,553.6 kWh short at 13042. Nothing in either reading says so on its own;
    standing it beside the discharge total it has to contain does.
    """
    found = {
        name: detail
        for name, (verdict, detail) in _corpus_verdicts().items()
        if verdict not in (MATCH, None)
    }
    assert sorted(found) == [
        "sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan.json",
        "sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan.json",
    ], found


def test_maximo101_is_the_ceilings_to_catch_and_not_this_checks() -> None:
    """The third machine on that firmware, and the division of labour.

    Its high word reads 0xFFFF, so `total_battery_charge` comes out
    *larger* than everything it contains and the relation is satisfied. A
    containment cannot see it, and no upper bound could: the corpus has an
    honest house reading 9,290 kWh charged against 0.0 from PV. That reading
    is `model.ENERGY_CEILING_KWH`'s to refuse (`tests/test_energy_ceiling.py`),
    and in a live house the field decodes it as None, which drops this row
    altogether rather than passing it.
    """
    verdicts = _corpus_verdicts()
    maximo = {
        name: verdict
        for name, (verdict, _detail) in verdicts.items()
        if "maximo101" in name
    }
    assert maximo and set(maximo.values()) == {MATCH}
    # And with the ceiling applied, as the integration reads it: no row.
    assert _containment_verdict(
        {
            "total_battery_charge": None,
            "total_battery_charge_from_pv": 13540.5,
            "total_battery_discharge": 16668.7,
        }
    ) == (None, "")


def test_most_of_the_corpus_is_judged_and_matches() -> None:
    """Otherwise the two tests above would pass on a check that never fires."""
    verdicts = _corpus_verdicts()
    matched = sum(1 for verdict, _ in verdicts.values() if verdict == MATCH)
    assert matched > 75, verdicts
