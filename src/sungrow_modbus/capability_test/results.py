"""The kept runs and the readings' checks, as a page shows them to a person.

Built from what `DiagnosisRunner.tests` folds; nothing is judged here. Every
row says what a check is called, how it came out, and either the evidence or
what it still waits for.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import ledger
from .labels import OUTCOMES, STEPS, label

#: What of an effect's or a readback's row is evidence, in this order.
_EFFECT_FIELDS = (
    "observable",
    "commanded",
    "commanded_unit",
    "before",
    "during",
    "after",
    "detail",
)
_READBACK_FIELDS = ("original", "written", "library_read", "unit", "detail")


def _evidence(row: Mapping[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any]:
    if row is None:
        return {}
    return {key: row[key] for key in fields if row.get(key) is not None}


def _notes(run: Mapping[str, Any]) -> list[str]:
    """Return what a run did and left out: `ledger.run_lines`, for one run."""
    return [
        *(
            f"{row.get('check')}: {row.get('verdict')}"
            for row in run.get("effects") or []
        ),
        *(
            f"{row.get('field')}: {row.get('verdict')}"
            for row in run.get("readback") or []
        ),
        *(str(note) for note in run.get("not_established") or []),
    ]


def _run(index: int, run: Mapping[str, Any]) -> dict[str, Any]:
    """Return one kept run's line: when, what it came to, what it put back."""
    outcome = run.get("outcome")
    restored = run.get("restored") or []
    return {
        "number": index + 1,
        "read_at": run.get("read_at"),
        "outcome": outcome,
        "label": OUTCOMES.get(outcome) if isinstance(outcome, int) else None,
        "means": run.get("outcome_means"),
        "restored": sum(1 for row in restored if row.get("restored")),
        "not_restored": sorted(
            str(row.get("field")) for row in restored if not row.get("restored")
        ),
        "notes": _notes(run),
    }


def view(folded: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return the results of a fold, or an empty view where nothing is kept."""
    folded = folded or {}
    summary: Mapping[str, Mapping[str, Any]] = folded.get("summary") or {}
    established, total = ledger.progress(folded) if summary else (0, 0)
    missing = {item["name"]: item["why"] for item in folded.get("still_missing") or []}
    disputed = {item["name"] for item in folded.get("contradictions") or []}
    effects = {row.get("check"): row for row in folded.get("effects") or []}
    readback = {row.get("field"): row for row in folded.get("readback") or []}
    rows = []
    for name, row in summary.items():
        why = missing.get(name)
        run = row.get("run")
        evidence = (
            _evidence(effects.get(name), _EFFECT_FIELDS)
            if row.get("kind") == "effect"
            else _evidence(readback.get(name), _READBACK_FIELDS)
        )
        if row.get("detail"):
            evidence.setdefault("detail", row["detail"])
        rows.append(
            {
                "name": name,
                "label": label(name, row.get("verdict")) or {"en": name, "de": name},
                "kind": row.get("kind"),
                "bucket": ledger.bucket(row.get("verdict")),
                "verdict": row.get("verdict"),
                "established": bool(row.get("established")),
                "disputed": name in disputed,
                # A readings' check says "waits for" itself.
                "waits_for": (
                    why.removeprefix(f"{name}: ").removeprefix("waits for ")
                    if why
                    else None
                ),
                "run": run + 1 if isinstance(run, int) else None,
                "read_at": row.get("read_at"),
                "evidence": evidence,
            }
        )
    return {
        "established": established,
        "total": total,
        "counts": ledger.counts(folded),
        "rows": rows,
        "steps": [list(step) for step in STEPS],
        "runs": [_run(i, run) for i, run in enumerate(folded.get("runs") or [])],
    }
