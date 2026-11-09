"""Every wallbox capability test run, folded into what is established.

The inverter's ledger (`capability_test.ledger`) for a wallbox: one run
answers only the checks its moment allowed -- a car charging, or not -- so
runs are kept and folded, the strongest verdict per check wins, and what is
still missing says why. A finding outranks a pass, as on the inverter: once a
run has seen the car stop at 6 A the setting is read a decade too low, whatever
a later run matched.

Nothing here talks to a device, Home Assistant or a file. A run is the plain
block `block` returns; the driver keeps the list and folds it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, NamedTuple

from ..capability_test import procedure as inverter
from . import capability_test as wct

#: Bumped when the shape of a folded ledger changes.
LEDGER_SCHEMA = 1

#: The document block's name.
DOCUMENT = "wallbox_capability_test"

#: A check whose need was met and still did not settle is tried this many
#: times in all, then reported as not settled.
MAX_ATTEMPTS = 3

FINDING, ANSWERED, ESTABLISHED = 5, 4, 3
RANK: dict[str, int] = {
    wct.DECADE: FINDING,
    wct.MISMATCH: FINDING,
    wct.CONFIRMED: ANSWERED,
    wct.CLAMPED: ANSWERED,
    wct.NOT_CLAMPED: ANSWERED,
    wct.REFUSED: ESTABLISHED,
    wct.MATCHED: 2,
    wct.INCONCLUSIVE: 2,
    wct.DROPPED: 1,
    wct.SKIPPED: 0,
}

#: Which step names are one check, and the check's name.
_ALIASES = {"stop": "start/stop", "start": "start/stop"}
_ALIASES |= {"disable": "enable"}

CHARGING_NEED = "a car charging (status 3, drawing 5 A or more)"
IDLE_NEED = "nothing flowing"
ANY_NEED = "any state"

#: check -> (what it needs of the house, the option that allows it, or None for
#: the checks every run makes).
CHECKS: dict[str, tuple[str, str | None]] = {
    "output current": (CHARGING_NEED, None),
    "current follow": (CHARGING_NEED, "follow"),
    "available current": (CHARGING_NEED, "follow"),
    "below minimum": (CHARGING_NEED, "below_minimum"),
    "above rating": (CHARGING_NEED, "above_rating"),
    "start/stop": (CHARGING_NEED, "start_stop"),
    "enable": (ANY_NEED, "enable"),
    "phase": (IDLE_NEED, "phase"),
    "phase while charging": (CHARGING_NEED, "phase_charging"),
    "fallback": (CHARGING_NEED, "fallback"),
    "mileage": (ANY_NEED, "mileage"),
}

#: The checks that cannot be judged without a car.
NEEDS_CAR = frozenset(
    name for name, (need, _o) in CHECKS.items() if need == CHARGING_NEED
)


class Live(NamedTuple):
    """What the wallbox is doing now, from the last poll."""

    status: int | None
    draw_a: float | None
    setting_a: float | None = None
    """The output current setting. 0 at idle at gerd's: the run's own guard
    refuses to write while it reads 0, so nothing is due then."""

    @property
    def writable(self) -> bool:
        """Whether a run would be let to write: the setting holds a current."""
        return self.setting_a is not None and self.setting_a > 0

    @property
    def charging(self) -> bool:
        """Whether a car is charging and drawing enough to be judged by."""
        return self.status == wct.CHARGING and (self.draw_a or 0.0) >= 5.0

    @property
    def idle(self) -> bool:
        """Whether nothing is flowing."""
        return self.status in wct.IDLE_STATUSES


def check_of(step_name: str) -> str:
    """Return the check a step belongs to."""
    if step_name.startswith("output current"):
        return "output current"
    return _ALIASES.get(step_name, step_name)


def rank(verdict: str | None) -> int:
    """Return how strongly a verdict answers its question."""
    return RANK.get(verdict or "", 0)


def enabled_checks(options: Mapping[str, Any]) -> frozenset[str]:
    """Return the checks the owner's leave and options allow."""
    return frozenset(
        name
        for name, (_need, option) in CHECKS.items()
        if option is None or options.get(option)
    )


def block(
    outcome: wct.Outcome,
    options: wct.Options,
    *,
    transport: str,
    fresh: bool,
    firmware: str | None = None,
) -> dict[str, Any]:
    """Return one run as a document block. No serial and no address."""
    return {
        "document": DOCUMENT,
        "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "leave": options.leave,
        "transport": transport,
        "fresh_session": fresh,
        "firmware": firmware,
        "options": {
            "max_amps": options.max_amps,
            "cap_explicit": options.cap_explicit,
            "current": options.current,
            "start_stop": options.start_stop,
            "enable": options.enable,
            "phase": options.phase,
            "follow": options.follow,
            "below_minimum": options.below_minimum,
            "above_rating": options.above_rating,
            "phase_charging": options.phase_charging,
            "fallback": options.fallback,
            "mileage": options.mileage,
        },
        "code": outcome.code,
        "conditions": {k: v for k, v in outcome.conditions.items() if k != "refusals"},
        "refusals": {
            str(k): v for k, v in outcome.conditions.get("refusals", {}).items()
        },
        "steps": [step._asdict() for step in outcome.steps],
        "restores": [row._asdict() for row in outcome.restores],
        "unestablished": list(outcome.unestablished),
    }


def fold_key(run: Mapping[str, Any]) -> tuple[str, bool]:
    """Return what two runs must share to be folded: the path and its session."""
    return str(run.get("transport")), bool(run.get("fresh_session"))


def fold(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fold kept runs into the strongest verdict per check.

    A dry run, and a run that wrote nothing, answers nothing and is not kept
    by a driver; folded anyway, its steps are empty and it changes nothing.
    """
    checks: dict[str, dict[str, Any]] = {}
    attempts: dict[str, int] = {}
    contradictions: dict[str, list[str]] = {}
    worst = 0
    for run in runs:
        worst = max(worst, int(run.get("code") or 0))
        seen: set[str] = set()
        car = (run.get("conditions") or {}).get("status") == "charging"
        for step in run.get("steps") or []:
            name = check_of(str(step["name"]))
            verdict = str(step["verdict"])
            row = {
                "verdict": verdict,
                "detail": step.get("detail", ""),
                "read_at": run.get("read_at"),
            }
            kept = checks.get(name)
            if kept is None or rank(verdict) >= rank(kept["verdict"]):
                if (
                    kept is not None
                    and rank(verdict) == FINDING
                    and rank(kept["verdict"]) >= ANSWERED
                ):
                    contradictions.setdefault(name, []).append(kept["verdict"])
                checks[name] = row
            elif rank(kept["verdict"]) == FINDING and rank(verdict) >= ANSWERED:
                contradictions.setdefault(name, []).append(verdict)
            # An attempt is a run whose need was met and that still did not settle.
            met = car or name not in NEEDS_CAR
            if met and rank(verdict) in (1, 2) and name not in seen:
                attempts[name] = attempts.get(name, 0) + 1
            seen.add(name)
    for name, row in checks.items():
        row["established"] = rank(row["verdict"]) >= ESTABLISHED
        row["attempts"] = attempts.get(name, 0)
        if name in contradictions:
            row["contradicted_by"] = sorted(set(contradictions[name]))
    options: dict[str, Any] = {}
    for run in runs:
        for key, value in (run.get("options") or {}).items():
            if value is True or key not in options:
                options[key] = value
    return {
        "schema": LEDGER_SCHEMA,
        "runs": len(runs),
        "code": worst,
        "checks": checks,
        "options": options,
        "first": runs[0].get("read_at") if runs else None,
        "last": runs[-1].get("read_at") if runs else None,
    }


def awaited(
    folded: Mapping[str, Any] | None, options: Mapping[str, Any]
) -> list[tuple[str, str]]:
    """Return (check, what it needs) for every allowed check still unsettled.

    A check tried `MAX_ATTEMPTS` times without settling is not waited for: it
    is reported as not settled, and a car's own limit never ends a day's run.
    """
    rows = (folded or {}).get("checks") or {}
    out: list[tuple[str, str]] = []
    for name in sorted(enabled_checks(options)):
        row = rows.get(name)
        if row is not None and row["established"]:
            continue
        if row is not None and row.get("attempts", 0) >= MAX_ATTEMPTS:
            continue
        out.append((name, CHECKS[name][0]))
    return out


def due(
    folded: Mapping[str, Any] | None, live: Live, options: Mapping[str, Any]
) -> list[str]:
    """Return the awaited checks the wallbox's state allows right now."""
    out: list[str] = []
    for name, need in awaited(folded, options):
        if need == CHARGING_NEED and not live.charging:
            continue
        if need == IDLE_NEED and not (live.idle and live.writable):
            continue
        if need == ANY_NEED and not live.writable:
            continue
        out.append(name)
    return out


def still_missing(
    folded: Mapping[str, Any] | None, options: Mapping[str, Any]
) -> list[dict[str, str]]:
    """Return what is not established, and why, for the published document."""
    rows = (folded or {}).get("checks") or {}
    out: list[dict[str, str]] = []
    for name in sorted(enabled_checks(options)):
        row = rows.get(name)
        if row is not None and row["established"]:
            continue
        if row is None:
            why = f"never ran: needs {CHECKS[name][0]}"
        elif row.get("attempts", 0) >= MAX_ATTEMPTS:
            why = f"not settled after {row['attempts']} tries: {row['detail']}"
        else:
            why = f"{row['verdict']}: {row['detail']}"
        out.append({"check": name, "why": why})
    return out


def counts(folded: Mapping[str, Any] | None) -> dict[str, int]:
    """Return findings, answered and unanswered checks, for the counters."""
    rows = (folded or {}).get("checks") or {}
    found = sum(1 for r in rows.values() if rank(r["verdict"]) == FINDING)
    answered = sum(
        1 for r in rows.values() if r["established"] and rank(r["verdict"]) < FINDING
    )
    return {
        "findings": found,
        "answered": answered,
        "unanswered": len(rows) - found - answered,
    }


def document(folded: Mapping[str, Any], options: Mapping[str, Any]) -> dict[str, Any]:
    """Return the `wallbox_capability_test` block a diagnosis carries."""
    return {
        "document": DOCUMENT,
        **folded,
        "still_missing": still_missing(folded, options),
    }


def markdown(folded: Mapping[str, Any], options: Mapping[str, Any]) -> str:
    """Return the ledger as text for a notification."""
    lines = [
        f"**Wallbox:** {folded['runs']} run(s), "
        + ", ".join(f"{n} {k}" for k, n in counts(folded).items())
    ]
    for name, row in sorted((folded.get("checks") or {}).items()):
        lines.append(f"- {name}: {row['verdict']} — {row['detail']}")
    for item in still_missing(folded, options):
        lines.append(f"- *still missing* {item['check']}: {item['why']}")
    return "\n".join(lines)


#: A wallbox verdict in the inverter ledger's words, so the counters that
#: count the inverter's checks count the wallbox's with them.
COUNTED_AS: dict[str, str] = {
    wct.CONFIRMED: inverter.CONFIRMED,
    wct.CLAMPED: inverter.CLAMPED,
    wct.NOT_CLAMPED: inverter.CLAMPED,
    wct.REFUSED: inverter.REFUSED,
    wct.DECADE: inverter.SCALED,
    wct.MISMATCH: inverter.OFF_BY,
    wct.MATCHED: inverter.INCONCLUSIVE,
    wct.INCONCLUSIVE: inverter.INCONCLUSIVE,
    wct.DROPPED: inverter.DROPPED,
    wct.SKIPPED: inverter.SKIPPED,
}


def summary_rows(
    folded: Mapping[str, Any] | None, options: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """Return a row per allowed check in the inverter ledger's summary shape.

    A check no run has reached is a row without a verdict, so the counters
    total what could be asked, not only what has been.
    """
    rows = (folded or {}).get("checks") or {}
    out: dict[str, dict[str, Any]] = {}
    for name in sorted(enabled_checks(options)):
        row = rows.get(name)
        out[f"wallbox {name}"] = {
            "kind": "wallbox",
            "verdict": None if row is None else COUNTED_AS.get(row["verdict"]),
            "detail": "" if row is None else row["detail"],
            "needs": CHECKS[name][0],
            "established": bool(row and row["established"]),
            "read_at": None if row is None else row["read_at"],
        }
    return out
