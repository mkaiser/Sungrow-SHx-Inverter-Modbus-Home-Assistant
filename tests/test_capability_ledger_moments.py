"""A check established at one moment of the day is measured once at the other."""

from __future__ import annotations

from typing import Any

from sungrow_modbus.capability_test import CONFIRMED, ledger


def _run(read_at: str, pv: float, check: str = "forced charge") -> dict[str, Any]:
    return {
        "read_at": read_at,
        "block": {
            "outcome": 0,
            "conditions": {"pv_w": pv},
            "readback": [],
            "effects": [{"check": check, "verdict": CONFIRMED}],
            "not_established": [],
        },
    }


def test_the_moment_is_named_by_pv() -> None:
    assert ledger.moment_of({"pv_w": 2500.0}) == "day"
    assert ledger.moment_of({"pv_w": 0.0}) == "night"
    assert ledger.moment_of({}) is None
    assert ledger.live_moment(ledger.Live(None, None, None, None)) is None


def test_a_check_established_by_day_is_measured_again_at_night() -> None:
    folded = ledger.fold([_run("t1", 3000.0)])
    assert folded["summary"]["forced charge"]["moments"] == ["day"]
    assert "forced charge" in ledger.established(folded)
    assert "forced charge" in ledger.established(folded, moment="day")
    assert "forced charge" not in ledger.established(folded, moment="night")


def test_two_moments_end_it() -> None:
    folded = ledger.fold([_run("t1", 3000.0), _run("t2", 0.0)])
    assert folded["summary"]["forced charge"]["moments"] == ["day", "night"]
    assert "forced charge" in ledger.established(folded, moment="night")
    assert "forced charge" in ledger.established(folded, moment="day")


def test_a_check_outside_the_set_is_never_measured_twice() -> None:
    folded = ledger.fold([_run("t1", 3000.0, check="PV generation cut")])
    assert "PV generation cut" in ledger.established(folded, moment="night")


def test_the_other_moment_starts_no_run_of_its_own() -> None:
    """Measured when a run happens anyway; never awaited."""
    folded = ledger.fold([_run("t1", 3000.0)])
    assert "forced charge" not in {name for name, _ in ledger.awaited(folded)}
