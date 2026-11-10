"""The fold of several capability test runs into one block."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest

from sungrow_modbus.capability_test import ledger
from sungrow_modbus.capability_test.coverage import (
    CHECK_REVISIONS,
    EFFECT_FIELDS,
    READBACK,
)
from sungrow_modbus.capability_test.procedure import (
    CODES,
    CONFIRMED,
    EFFECT_SCALED,
    INCONCLUSIVE,
    MATCH,
    OUT_OF_TIME,
    REFUSED,
    SCALED,
    STALE_READBACK,
    STOPPED,
    UNCHANGED,
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


@pytest.mark.parametrize("verdict", sorted(ledger.RANK))
def test_every_verdict_lands_in_the_bucket_its_rank_says(verdict: str) -> None:
    """A new verdict is counted by its rank, never left out of every count."""
    rank = ledger.RANK[verdict]
    expected = {
        ledger.FINDING: "failed",
        ledger.ANSWERED: "passed",
        ledger.ESTABLISHED: "not_supported",
    }.get(rank, "inconclusive" if verdict == INCONCLUSIVE else "not_run")
    assert ledger.bucket(verdict) == expected
    assert ledger.bucket(verdict) in ledger.BUCKETS


def test_the_counts_add_up_to_the_total() -> None:
    """Each check once, by its strongest verdict; a check never reached is not run."""
    folded = ledger.fold(
        [
            _run(
                "t1",
                _block(
                    readback=[
                        _probe("export_power_limit", MATCH),
                        _probe("battery_max_soc", SCALED),
                        _probe("battery_min_soc", REFUSED),
                        _probe("backup_reserve", OUT_OF_TIME),
                    ],
                    effects=[_effect("forced charge", INCONCLUSIVE)],
                    notes=[SUNNY_NOON_NOTE],
                ),
            ),
            _run("t2", _block(readback=[_probe("battery_min_soc", MATCH)])),
        ]
    )
    counts = ledger.counts(folded)
    assert counts == {
        "passed": 2,
        "failed": 1,
        "not_supported": 0,
        "inconclusive": 1,
        "not_run": 2,
    }
    assert sum(counts.values()) == ledger.progress(folded)[1]
    assert ledger.counts({}) == dict.fromkeys(ledger.BUCKETS, 0)


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
    total = len(set(EFFECT_FIELDS) - ledger.MODES)
    assert line.startswith(f"0/{total} established · 1 run · waiting for: ")
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


def test_established_names_what_a_run_may_leave_out() -> None:
    """Established checks, and never one two runs disagree on."""
    first = _block(
        readback=[
            _probe("battery_max_soc", MATCH),
            _probe("battery_min_soc", SCALED),
            _probe("export_power_limit", OUT_OF_TIME),
        ],
        effects=[_effect("forced charge", CONFIRMED)],
    )
    second = _block(readback=[_probe("battery_min_soc", MATCH)])
    folded = ledger.fold(
        [_run("2026-11-08T10:00Z", first), _run("2026-11-08T22:00Z", second)]
    )

    assert ledger.established(folded) == {"battery_max_soc", "forced charge"}
    assert ledger.established(None) == frozenset()


def test_a_restart_measured_once_is_established() -> None:
    """Auto repeat must not stop the inverter again for an answer it has."""
    block = _block(readback=[_probe("battery_max_soc", MATCH)])
    block["restart"] = {"running_after": 41.0, "verdict": "measured"}
    folded = ledger.fold([_run("2026-11-08T10:00Z", block)])

    assert ledger.RESTART in ledger.established(folded)

    block["restart"] = {"running_after": None, "verdict": "never came back"}
    folded = ledger.fold([_run("2026-11-08T10:00Z", block)])
    assert ledger.RESTART not in ledger.established(folded)


def test_every_check_has_a_revision() -> None:
    """A check missing from the table would never be measured again."""
    assert set(CHECK_REVISIONS) == {READBACK, ledger.RESTART, *EFFECT_FIELDS}


def test_a_check_whose_logic_changed_is_measured_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A run from an older revision establishes nothing for that check."""
    old = _block(
        readback=[_probe("battery_max_soc", MATCH)],
        effects=[
            _effect("forced charge", CONFIRMED),
            _effect("PV generation cut", EFFECT_SCALED),
        ],
    )
    old["restart"] = {"running_after": 41.0, "verdict": "measured"}
    runs = [_run("2026-11-08T10:00Z", old)]
    assert {"forced charge", "battery_max_soc", ledger.RESTART} <= (
        ledger.established(ledger.fold(runs))
    )

    monkeypatch.setitem(CHECK_REVISIONS, "PV generation cut", 2)
    monkeypatch.setitem(CHECK_REVISIONS, "forced charge", 2)
    monkeypatch.setitem(CHECK_REVISIONS, ledger.RESTART, 2)
    folded = ledger.fold(runs)
    assert ledger.established(folded) == {"battery_max_soc"}
    assert folded["summary"]["forced charge"]["outdated"]
    assert any("older revision" in item["why"] for item in folded["still_missing"])

    # A run on the new logic answers it, and the old finding no longer
    # contradicts it: it was measured by logic that has since changed.
    new = _block(effects=[_effect("PV generation cut", CONFIRMED)])
    new["revisions"] = dict(CHECK_REVISIONS)
    folded = ledger.fold([*runs, _run("2026-11-09T10:00Z", new)])
    assert "PV generation cut" in ledger.established(folded)
    assert folded["summary"]["PV generation cut"]["verdict"] == CONFIRMED
    assert not folded["contradictions"]
    assert "forced charge" not in ledger.established(folded)


def test_a_stopped_check_still_waits() -> None:
    """Stopped is not answered: it counts as not run, and a later run is due."""
    folded = ledger.fold(
        [
            _run(
                "2026-11-08T10:00Z",
                _block(readback=[_probe("battery_max_soc", STOPPED)]),
            )
        ]
    )

    assert ledger.bucket(STOPPED) == "not_run"
    assert "battery_max_soc" not in ledger.established(folded)


def test_the_fold_lists_only_restores_that_did_something() -> None:
    """Already original is a count; written back or not put back is a row.

    Every run in `runs` keeps every row, so `unfold` gives them back whole.
    """
    block = _block()
    block["restored"] = [
        {"field": "a", "restored": True, "attempts": 0, "detail": "already holding"},
        {"field": "b", "restored": True, "attempts": 1, "detail": None},
        {"field": "c", "restored": False, "attempts": 3, "detail": "refused"},
    ]
    folded = ledger.fold([_run("2026-11-08T10:00Z", block)])

    assert [row["field"] for row in folded["restored"]] == ["b", "c"]
    assert folded["restored_already_original"] == 1
    assert len(folded["runs"][0]["restored"]) == 3
    assert (
        ledger.unfold(folded, read_at=None)[0]["block"]["restored"] == block["restored"]
    )


@pytest.mark.parametrize("direct", [True, False])
def test_a_kept_dongle_readback_of_the_old_value_settles_nothing(
    direct: bool,
) -> None:
    """A run kept before the probe knew better is read as the probe now records it.

    Through a WiNet-S the old value is the dongle's cache, so the check stays
    missing, counted inconclusive rather than not supported, and auto repeat
    does not wait for it: no moment of the day makes the dongle's answer
    fresh. Over a cable the old value is the register refusing, and settles it.
    """
    block = _block(
        readback=[_probe("battery_max_charge_power", UNCHANGED)], direct=direct
    )

    folded = ledger.fold([_run("2026-11-10T09:54:00+01:00", block)])

    row = folded["summary"]["battery_max_charge_power"]
    missing = {item["name"]: item for item in folded["still_missing"]}
    if direct:
        assert row["verdict"] == UNCHANGED and row["established"]
        assert ledger.counts(folded)["not_supported"] == 1
        assert "battery_max_charge_power" not in missing
    else:
        assert row["verdict"] == INCONCLUSIVE and not row["established"]
        assert ledger.counts(folded)["not_supported"] == 0
        assert ledger.counts(folded)["inconclusive"] == 1
        assert missing["battery_max_charge_power"]["why"] == STALE_READBACK
        assert "battery_max_charge_power" not in dict(ledger.awaited(folded))
        # The run itself is kept as it was recorded.
        assert folded["runs"][0]["readback"][0]["verdict"] == UNCHANGED
