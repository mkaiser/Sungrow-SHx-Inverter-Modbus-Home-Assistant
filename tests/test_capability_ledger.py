"""The fold of several capability test runs into one block."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest

from sungrow_modbus.capability_test import ledger
from sungrow_modbus.capability_test.coverage import EFFECT_FIELDS
from sungrow_modbus.capability_test.procedure import (
    CODES,
    CONFIRMED,
    EFFECT_SCALED,
    INCONCLUSIVE,
    MATCH,
    SCALED,
)

EFFECTS = Path(ledger.__file__).with_name("effects.py")

SUNNY_NOON_NOTE = (
    "no import limit check: the forced charge drew only 120 W from the grid, "
    "too little for a cap under it to be told from the house moving; PV was "
    "covering it, and a run after dark measures it"
)


def _block(
    *,
    outcome: int = 0,
    readback: list[dict[str, Any]] | None = None,
    effects: list[dict[str, Any]] | None = None,
    notes: list[str] | None = None,
    direct: bool = True,
    simulated: bool = False,
) -> dict[str, Any]:
    return {
        "schema": 2,
        "outcome": outcome,
        "outcome_means": CODES[outcome],
        "conditions": {"direct_connection": direct, "simulated": simulated},
        "readback": readback or [],
        "effects": effects or [],
        "restored": [],
        "restart": None,
        "not_established": notes or [],
    }


def _run(when: str, block: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {"read_at": when, "block": block, **extra}


def _effect(check: str, verdict: str) -> dict[str, Any]:
    return {"check": check, "verdict": verdict, "detail": None}


def _probe(field: str, verdict: str) -> dict[str, Any]:
    return {"field": field, "verdict": verdict, "detail": None}


def test_a_check_missing_at_noon_is_established_at_night() -> None:
    noon = _block(
        outcome=3,
        readback=[_probe("battery_max_soc", MATCH)],
        effects=[_effect("forced charge", CONFIRMED)],
        notes=[SUNNY_NOON_NOTE],
    )
    night = _block(effects=[_effect("site import limit", CONFIRMED)])

    first = ledger.fold([_run("2026-11-08T12:00:00+00:00", noon)])
    assert [item["name"] for item in first["still_missing"]] == ["site import limit"]
    assert first["still_missing"][0]["why"] == SUNNY_NOON_NOTE
    assert ledger.progress(first) == (2, 3)

    both = ledger.fold(
        [
            _run("2026-11-08T12:00:00+00:00", noon),
            _run("2026-11-08T22:00:00+00:00", night),
        ]
    )
    assert both["still_missing"] == []
    assert ledger.progress(both) == (3, 3)
    assert both["summary"]["site import limit"]["run"] == 1
    assert (
        both["summary"]["site import limit"]["read_at"] == "2026-11-08T22:00:00+00:00"
    )
    assert [run["read_at"] for run in both["runs"]] == [
        "2026-11-08T12:00:00+00:00",
        "2026-11-08T22:00:00+00:00",
    ]
    # The schema-2 keys every reader of a block uses are still there.
    assert {row["check"] for row in both["effects"]} == {
        "forced charge",
        "site import limit",
    }
    assert both["schema"] == ledger.LEDGER_SCHEMA


def test_a_later_inconclusive_does_not_undo_a_confirmation() -> None:
    folded = ledger.fold(
        [
            _run("t1", _block(effects=[_effect("forced charge", CONFIRMED)])),
            _run(
                "t2",
                _block(outcome=3, effects=[_effect("forced charge", INCONCLUSIVE)]),
            ),
        ]
    )
    assert folded["summary"]["forced charge"]["verdict"] == CONFIRMED
    assert folded["summary"]["forced charge"]["run"] == 0


def test_a_finding_against_a_match_is_shown_and_flagged() -> None:
    folded = ledger.fold(
        [
            _run("t1", _block(readback=[_probe("export_power_limit", MATCH)])),
            _run(
                "t2", _block(outcome=4, readback=[_probe("export_power_limit", SCALED)])
            ),
            _run("t3", _block(effects=[_effect("forced charge", EFFECT_SCALED)])),
            _run("t4", _block(effects=[_effect("forced charge", CONFIRMED)])),
        ]
    )
    assert folded["readback"][0]["verdict"] == SCALED
    assert {item["name"] for item in folded["contradictions"]} == {
        "export_power_limit",
        "forced charge",
    }
    assert folded["outcome"] == 4


def test_any_run_left_unrestored_marks_the_whole_fold() -> None:
    folded = ledger.fold([_run("t1", _block(outcome=5)), _run("t2", _block(outcome=0))])
    assert folded["outcome"] == 5
    assert folded["outcome_means"] == CODES[5]


@pytest.mark.parametrize(
    "other", [_block(direct=False), _block(simulated=True)], ids=["dongle", "simulator"]
)
def test_runs_that_speak_for_different_things_are_not_folded(
    other: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="cannot be folded"):
        ledger.fold([_run("t1", _block()), _run("t2", other)])


def test_each_run_carries_only_the_readings_that_moved() -> None:
    folded = ledger.fold(
        [
            _run("t1", _block(), readings={"soc": 40, "max_soc": 100}),
            _run("t2", _block(), readings={"soc": 75, "max_soc": 100}),
        ],
        readings={"soc": 75, "max_soc": 100},
    )
    assert folded["runs"][0]["readings_changed"] == {"soc": 40}
    assert folded["runs"][1]["readings_changed"] == {}


def test_a_note_that_stops_every_behavioural_check_marks_them_all() -> None:
    folded = ledger.fold(
        [
            _run(
                "t1",
                _block(
                    outcome=3,
                    notes=["no behavioural checks: a simulator has no power flows"],
                ),
            )
        ]
    )
    missing = {item["name"] for item in folded["still_missing"]}
    assert missing == set(EFFECT_FIELDS) - ledger.MODES


def test_the_status_line_fits_a_state() -> None:
    folded = ledger.fold(
        [
            _run(
                "t1",
                _block(
                    outcome=3,
                    notes=["no behavioural checks: a simulator has no power flows"],
                ),
            )
        ]
    )
    line = ledger.status_line(folded)
    assert line.startswith("0/8 established · 1 run · waiting for: ")
    assert len(ledger.status_line(folded, limit=40)) == 40
    assert "Still waiting for" in ledger.markdown(folded)


def test_every_skip_note_names_a_check_the_fold_knows() -> None:
    """The prefixes are read from sentences; hold them to the sentences."""
    source = EFFECTS.read_text(encoding="utf-8")
    prefixes = set(re.findall(r'"(no [A-Za-z{}\- ]+? checks?)[: ]', source))
    assert prefixes, "found no skip notes in effects.py"
    for prefix in prefixes:
        if prefix.startswith("no behavioural check"):
            continue
        if "{direction}" in prefix:
            for direction in ("charge", "discharge"):
                name = prefix.replace("{direction}", direction)
                assert ledger.note_check(name) in EFFECT_FIELDS, name
            continue
        assert ledger.note_check(prefix) in EFFECT_FIELDS, prefix
    for _prefix, check in ledger.NOTE_PREFIXES:
        assert check in EFFECT_FIELDS


# -- when to come back -------------------------------------------------------

NOON = ledger.Live(pv=3000.0, battery=-1500.0, export=800.0, soc=70.0)
NIGHT = ledger.Live(pv=0.0, battery=400.0, export=-400.0, soc=60.0)


def _missing(*checks: str, why: str = "no {} check: not this moment") -> dict:
    return ledger.fold(
        [_run("t1", _block(outcome=3, notes=[why.format(c) for c in checks]))]
    )


def test_the_import_limit_is_due_after_dark_and_not_at_noon() -> None:
    folded = _missing("import limit")
    assert ledger.awaited(folded) == [
        ("site import limit", "dark (PV under 200 W), the battery under 85 %")
    ]
    assert ledger.due(folded, NOON) == []
    assert ledger.due(folded, NIGHT) == ["site import limit"]


def test_the_pv_cut_is_due_in_sun() -> None:
    folded = _missing("PV cut")
    assert ledger.due(folded, NOON) == ["PV generation cut"]
    assert ledger.due(folded, NIGHT) == []


def test_a_reading_not_polled_yet_starts_nothing() -> None:
    folded = _missing("import limit")
    assert ledger.due(folded, ledger.Live(None, None, None, None)) == []


def test_a_check_refused_by_the_options_is_not_waited_for() -> None:
    folded = _missing(
        "PV cut", why="no {} check: this run was not given leave to cut PV"
    )
    assert ledger.awaited(folded) == []
    assert ledger.due(folded, NOON) == []


def test_with_nothing_kept_a_first_run_is_due() -> None:
    assert ledger.due(None, NIGHT) == ["every check"]


def test_every_behavioural_check_says_what_it_needs() -> None:
    assert set(ledger.NEEDS) == set(EFFECT_FIELDS) - ledger.MODES


def test_unfold_gives_back_what_fold_took() -> None:
    runs = [
        _run(
            "t1",
            _block(effects=[_effect("forced charge", CONFIRMED)]),
            readings={"soc": 40},
        ),
        _run("t2", _block(), readings={"soc": 75}),
    ]
    folded = ledger.fold(runs, readings={"soc": 75})

    again = ledger.unfold(folded, read_at=None, readings={"soc": 75})

    assert [run["read_at"] for run in again] == ["t1", "t2"]
    assert [run["readings"] for run in again] == [{"soc": 40}, {"soc": 75}]
    assert ledger.fold(again, readings={"soc": 75}) == folded


def test_unfold_dates_a_single_run_by_the_document() -> None:
    assert ledger.unfold(_block(), read_at="t0") == [
        {"read_at": "t0", "block": _block()}
    ]
