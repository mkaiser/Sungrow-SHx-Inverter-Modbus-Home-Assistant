"""The kept runs and the readings' checks, as a page shows them to a person.

Built from what `DiagnosisRunner.tests` folds; nothing is judged here. Every
row says what a check is called, how it came out, and either the evidence or
what it still waits for.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import ledger
from .labels import OUTCOMES, STEPS, Label, label, need, verdict_label

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
#: How the wallbox's ledger starts the reason of a check without a run.
_NEVER_RAN = "never ran: needs "
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


def _waits(name: str, row: Mapping[str, Any], why: str | None) -> Label | None:
    """Return what a check waits for, in both languages.

    The English is the ledger's own reason. The German says the need, where
    one is known and waiting answers it; a reason in free text, and one that
    only the owner's options change, stays as it was written.
    """
    if why is None:
        return None
    if row.get("needs"):
        return need(str(row["needs"]), row.get("detail"))
    en = why.removeprefix(f"{name}: ").removeprefix("waits for ")
    de = en
    if en.startswith(_NEVER_RAN):
        de = need(en.removeprefix(_NEVER_RAN))["de"]
    elif name in ledger.NEEDS and not ledger.needs_leave({"why": why}):
        de = need(ledger.NEEDS[name][0])["de"]
    return {"en": en, "de": de}


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
        waits = _waits(name, row, missing.get(name))
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
                "waits_for": waits["en"] if waits else None,
                "waits_label": waits,
                "verdict_label": verdict_label(row.get("verdict")),
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
