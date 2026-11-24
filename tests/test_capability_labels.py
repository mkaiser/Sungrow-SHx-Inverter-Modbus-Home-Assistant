"""Every check has a name a person can read, in English and German.

And the results view carries what it should: the same counts as the ledger,
what a missing check waits for, and whether everything was put back.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest

from sungrow_modbus.capability_test import labels, ledger, plausibility, results
from sungrow_modbus.capability_test.coverage import EFFECT_FIELDS
from sungrow_modbus.capability_test.labels import OUTCOMES, STEPS, label
from sungrow_modbus.capability_test.procedure import (
    CLAMPED,
    CODES,
    CONFIRMED,
    INCONCLUSIVE,
    NO_EFFECT,
    PROBES,
)
from sungrow_modbus.wallbox import (
    ledger as wallbox_ledger,
    plausibility as wallbox_plausibility,
)

NAMES = sorted(
    {
        *EFFECT_FIELDS,
        *(probe.field for probe in PROBES),
        *(check.name for check in plausibility.checks()),
        *(check.name for check in wallbox_plausibility.checks()),
        *(f"wallbox {name}" for name in wallbox_ledger.CHECKS),
    }
)


@pytest.mark.parametrize("name", NAMES)
def test_every_check_has_a_label(name: str) -> None:
    found = label(name)
    assert found is not None, f"{name} has no label (capability_test/labels.py)"
    assert set(found) == {"en", "de"}
    assert all(found.values())


def test_no_two_checks_share_a_label() -> None:
    for language in ("en", "de"):
        texts = [(label(name) or {})[language] for name in NAMES]
        assert len(texts) == len(set(texts))


@pytest.mark.parametrize(
    ("verdict", "said"),
    [
        (CONFIRMED, "are refused"),
        (CLAMPED, "are cut to it"),
        (NO_EFFECT, "are accepted"),
        (INCONCLUSIVE, "enforced?"),
        (None, "enforced?"),
    ],
)
def test_a_bound_is_named_by_what_was_found(verdict: str | None, said: str) -> None:
    found = label("upper bound of battery_max_charge_power", verdict)
    assert found is not None
    assert found["en"].endswith(said)


def test_every_step_a_test_names_is_a_check_or_none() -> None:
    """A renamed step would stop marking its check, without a word."""
    folder = Path(labels.__file__).parent.parent
    steps = [
        step
        for path in (*folder.glob("capability_test/*.py"), *folder.glob("wallbox/*.py"))
        for step in re.findall(
            r'_step\(\s*f?"([^"{]+)', path.read_text(encoding="utf-8")
        )
    ]
    assert len(steps) > 25
    #: Setting up, putting back and the inverter's restart: no check's own.
    none = {
        "reading the inverter",
        "the before-state is saved",
        "stopping the inverter; the restart may take some minutes",
        "starting the inverter; this may take some minutes",
        "identify the wallbox",
        "snapshot",
        "identify the wallbox and the inverter's block",
        "switch to user-defined mode",
    }
    starts = [start for start, _check in STEPS]
    for step in steps:
        own = any(step.startswith(name) for name in NAMES)
        assert own or step in none or any(step.startswith(s) for s in starts), step
    for start, check in STEPS:
        assert check in NAMES, check
        assert any(step.startswith(start) for step in steps), start


def test_every_outcome_has_a_label() -> None:
    assert set(OUTCOMES) == set(CODES)


def test_every_verdict_has_german() -> None:
    assert set(labels.VERDICTS_DE) == set(ledger.RANK)


def test_every_need_has_german() -> None:
    """A need reworded, or whose threshold moved, changes its row here."""
    needs = {
        ledger.FORCED_STARTUP_NEEDS,
        *(words for words, _due in ledger.NEEDS.values()),
        *(check.needs for check in plausibility.checks()),
        *(check.needs for check in wallbox_plausibility.checks()),
        *(words for words, _option in wallbox_ledger.CHECKS.values()),
    }
    assert set(labels.NEEDS_DE) == needs


def test_what_a_check_waits_for_is_said_in_german() -> None:
    row = {"kind": "effect"}
    why = "no forced discharge check: the battery is low"
    said = results._waits("forced discharge", row, why)
    assert said == {"en": why, "de": "Batterie über 30 %"}
    left = f"forced discharge: {ledger.NEEDS_LEAVE[0]}"
    said = results._waits("forced discharge", row, left)
    assert said is not None
    assert said["de"] == said["en"]
    said = results._waits(
        "wallbox phase", {"kind": "wallbox"}, "never ran: needs nothing flowing"
    )
    assert said is not None
    assert said["de"] == "kein Ladestrom"
    assert (
        labels.need("a midnight", "2 of 3 events")["de"] == "eine Mitternacht (2 von 3)"
    )


def test_an_unknown_check_has_none() -> None:
    assert label("something new") is None
    assert label("total_pv_generation against daily_exported_energy") is None


def _block(**more: Any) -> dict[str, Any]:
    return {
        "outcome": 0,
        "outcome_means": CODES[0],
        "conditions": {"direct_connection": True},
        "readback": [],
        "effects": [],
        "restored": [],
        "not_established": [],
        **more,
    }


def test_nothing_kept_is_an_empty_view() -> None:
    for nothing in (None, {}):
        view = results.view(nothing)
        assert (view["established"], view["total"]) == (0, 0)
        assert view["rows"] == view["runs"] == []


def test_a_view_says_what_was_measured_and_what_is_missing() -> None:
    folded = ledger.fold(
        [
            {
                "read_at": "2026-01-01T10:00:00+00:00",
                "block": _block(
                    effects=[
                        {
                            "check": "forced charge",
                            "observable": "battery charge power",
                            "commanded": 1250,
                            "commanded_unit": "W",
                            "before": 0,
                            "during": 1240,
                            "after": 0,
                            "verdict": "the inverter did as it was told",
                            "detail": None,
                        }
                    ],
                    restored=[
                        {"field": "battery_max_soc", "restored": True, "attempts": 0},
                        {"field": "ems_mode", "restored": False, "attempts": 3},
                    ],
                    not_established=["no forced discharge check: the battery is low"],
                ),
            }
        ]
    )
    folded = ledger.with_plausibility(
        folded,
        {
            "power balance": {
                "kind": "plausibility",
                "verdict": None,
                "detail": "2 of 20 observations",
                "needs": "any time",
                "established": False,
                "read_at": None,
            }
        },
    )
    view = results.view(folded)
    assert view["counts"] == ledger.counts(folded)
    assert (view["established"], view["total"]) == ledger.progress(folded)
    rows = {row["name"]: row for row in view["rows"]}
    charge = rows["forced charge"]
    assert charge["bucket"] == "passed"
    assert charge["label"]["de"] == "Zwangsladung"
    assert charge["evidence"]["during"] == 1240
    assert "detail" not in charge["evidence"]
    assert charge["waits_for"] is None
    assert "the battery is low" in rows["forced discharge"]["waits_for"]
    assert charge["verdict_label"]["de"] == labels.VERDICTS_DE[CONFIRMED]
    assert rows["power balance"]["waits_label"]["de"] == "any time (2 von 20)"
    assert rows["power balance"]["waits_for"] == "any time (2 of 20 observations)"
    (run,) = view["runs"]
    assert run["restored"] == 1
    assert run["not_restored"] == ["ems_mode"]
    assert run["label"]["en"]
    assert run["notes"] == [
        "forced charge: the inverter did as it was told",
        "no forced discharge check: the battery is low",
    ]
