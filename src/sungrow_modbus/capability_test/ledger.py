"""Fold several capability test runs into one block.

One run covers only the checks its moment allowed. Each behavioural check
looks at the house first and skips itself when it does not fit: the site
import limit needs a charge drawn from the grid, which a sunny noon covers
from PV; the PV cut needs PV; the charge ceiling needs a charging battery. So
a house that wants every check answered has to be asked several times, at
several moments, and a contributor should still publish **one** document.

This module is that fold. It takes the blocks of several runs on one inverter
(each one exactly what `engine.document` returned) and returns one block that:

- keeps every run whole, in `runs`, each with its own `read_at` -- so a
  folded block is dated, which a single run's block never was;
- keeps the keys a schema-2 block has (`readback`, `effects`, `conditions`,
  `outcome`, `not_established`), filled with the **strongest** row per field
  and per check, so every reader of a block reads a folded one unchanged;
- names, in `summary`, which run established each check, and in
  `still_missing`, the checks no run has established yet and what the latest
  run said about why -- which is what tells the owner when to come back;
- flags, in `contradictions`, a check that one run found off by a decade and
  another found right. That is never resolved here: it is a finding about the
  device, or about the procedure, and either way a person has to read it.

Runs are only folded when they speak for the same thing: the same transport
(`direct_connection`), and neither simulated nor a dry run unless all are.
Firmware is the caller's to watch, because a block does not carry it; the
integration's ledger starts again when it changes.

Nothing here talks to a device, opens a file or knows about Home Assistant.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, NamedTuple

from .coverage import EFFECT_FIELDS
from .procedure import (
    CLAMPED,
    CODES,
    CONFIRMED,
    DROPPED,
    EFFECT_FLOOR_W,
    EFFECT_SCALED,
    INCONCLUSIVE,
    MATCH,
    MIN_PV_W,
    NO_BOUNDS,
    NO_EFFECT,
    NO_SNAPSHOT,
    NO_WINDOW,
    NOT_CAPABLE,
    OFF_BY,
    OUT_OF_TIME,
    PV_CUT_MIN_W,
    REFUSED,
    SCALED,
    SEVERITY,
    SIGN_INVERTED,
    SKIPPED,
    SLOPE_WRONG,
    SOC_CEILING_FLOOR,
    SOC_CHARGE_CEILING,
    UNCHANGED,
    UNSAFE_STATE,
    USER_DECLINED,
)

#: The folded block's schema. A single run's block is `BLOCK_SCHEMA` (2); a
#: reader that finds 3 finds every key a 2 has, plus the ones below.
LEDGER_SCHEMA = 3

#: How strongly a verdict answers its question, highest first.
#:
#: A finding outranks a pass on purpose: once one run has seen a value off by
#: a decade, a later run that matched does not make it go away -- the two are
#: listed in `contradictions`, and the row shown is the finding.
#: `ESTABLISHED` is the line a row has to reach to stop being "still missing".
FINDING = 5
ANSWERED = 4
ESTABLISHED = 3
RANK: dict[str, int] = {
    # findings
    SCALED: FINDING,
    SLOPE_WRONG: FINDING,
    OFF_BY: FINDING,
    EFFECT_SCALED: FINDING,
    SIGN_INVERTED: FINDING,
    # the question answered, the way it was hoped
    MATCH: ANSWERED,
    CONFIRMED: ANSWERED,
    # the question answered, another way
    CLAMPED: ESTABLISHED,
    REFUSED: ESTABLISHED,
    UNCHANGED: ESTABLISHED,
    NO_EFFECT: ESTABLISHED,
    NOT_CAPABLE: ESTABLISHED,
    # not answered: the moment, the link or the leave was missing
    INCONCLUSIVE: 2,
    OUT_OF_TIME: 1,
    DROPPED: 1,
    UNSAFE_STATE: 1,
    NO_BOUNDS: 1,
    NO_SNAPSHOT: 1,
    NO_WINDOW: 1,
    USER_DECLINED: 0,
    SKIPPED: 0,
}

#: The two halves of a verdict that cannot both be true of one register.
_GOOD = frozenset({MATCH, CONFIRMED})

#: A behavioural check's skip note starts with one of these, and names that
#: check. The notes are sentences for a person (`base._note`); this is the one
#: place they are read by a program, and `tests/test_capability_ledger.py`
#: holds the table to the notes `effects.py` actually writes.
NOTE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("no forced charge check", "forced charge"),
    ("no forced discharge check", "forced discharge"),
    ("no charge-ceiling check", "charge ceiling"),
    ("no export limit check", "export power limit"),
    ("could not make the house export", "export power limit"),
    ("no PV cut check", "PV generation cut"),
    ("PV generation cut", "PV generation cut"),
    ("no charge window check", "forced-charging window"),
    ("no discharge window check", "discharge windows away from now"),
    ("no import limit check", "site import limit"),
)

#: A note that stops every behavioural check at once.
_ALL_EFFECTS = ("no behavioural check",)

#: Checks that are a mode of their own rather than part of an ordinary run.
#: Forced startup needs standby at minimum SoC, which every other check
#: refuses to start in, so it is never counted missing from an ordinary run.
MODES = frozenset({"forced startup under low SoC"})


def note_check(note: str) -> str | None:
    """Return the behavioural check a skip note is about, or None."""
    for prefix, check in NOTE_PREFIXES:
        if note.startswith(prefix):
            return check
    return None


def fold_key(block: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    """Return what two runs must share to be folded together.

    The transport, because through a WiNet-S a readback is the dongle's cache
    and not the register; and whether the run was simulated or dry, because
    neither is evidence about a device and must not dilute a run that is.
    """
    conditions = block.get("conditions") or {}
    return (
        bool(conditions.get("direct_connection")),
        bool(conditions.get("simulated")),
        bool(conditions.get("dry_run")),
    )


def _rank(row: Mapping[str, Any]) -> int:
    return RANK.get(str(row.get("verdict")), 1)


def _strongest(
    rows: Sequence[tuple[int, Mapping[str, Any]]],
) -> tuple[int, Mapping[str, Any]]:
    """Pick the strongest row; between equals, the latest run's."""
    return max(rows, key=lambda item: (_rank(item[1]), item[0]))


def _worst_code(codes: Sequence[int]) -> int:
    known = [code for code in codes if code in SEVERITY]
    return max(known, key=SEVERITY.index) if known else 1


def fold(
    runs: Sequence[Mapping[str, Any]],
    *,
    readings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fold runs, oldest first, into one block.

    Each run is a mapping with `read_at` (an ISO time), `block` (what
    `engine.document` returned) and optionally `readings` (that run's decoded
    readings). `readings`, the argument, is the document's own snapshot; each
    run then carries only the fields that differed from it, so a setting
    changed during the day shows up without every run copying ~245 fields.

    Raises ValueError when the runs cannot be folded (`fold_key` differs), so
    a caller never publishes a cable run's readback beside a dongle's.
    """
    if not runs:
        raise ValueError("nothing to fold")
    keys = {fold_key(run["block"]) for run in runs}
    if len(keys) > 1:
        raise ValueError(
            "these runs cannot be folded: they differ in transport, or in "
            "whether they were simulated or dry"
        )

    readback: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    effects: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    notes: dict[str, tuple[int, str]] = {}
    general: list[str] = []
    out_runs: list[dict[str, Any]] = []
    restored: list[dict[str, Any]] = []
    for index, run in enumerate(runs):
        block = run["block"]
        for row in block.get("readback") or []:
            readback.setdefault(str(row.get("field")), []).append((index, row))
        for row in block.get("effects") or []:
            effects.setdefault(str(row.get("check")), []).append((index, row))
        for row in block.get("restored") or []:
            restored.append({**row, "run": index})
        for note in block.get("not_established") or []:
            check = note_check(note)
            if check is not None:
                notes[check] = (index, note)
            elif note.startswith(_ALL_EFFECTS):
                for name in EFFECT_FIELDS:
                    notes[name] = (index, note)
            elif index == len(runs) - 1:
                general.append(note)
        entry: dict[str, Any] = {"read_at": run.get("read_at"), **block}
        if readings is not None and run.get("readings") is not None:
            entry["readings_changed"] = {
                field: value
                for field, value in run["readings"].items()
                if readings.get(field) != value
            }
        out_runs.append(entry)

    summary: dict[str, dict[str, Any]] = {}
    contradictions: list[dict[str, Any]] = []
    for kind, table in (("readback", readback), ("effect", effects)):
        for name, rows in table.items():
            index, row = _strongest(rows)
            summary[name] = {
                "kind": kind,
                "verdict": row.get("verdict"),
                "run": index,
                "read_at": runs[index].get("read_at"),
                "established": _rank(row) >= ESTABLISHED,
            }
            verdicts = {str(r.get("verdict")) for _, r in rows}
            if verdicts & _GOOD and any(RANK.get(v) == FINDING for v in verdicts):
                contradictions.append(
                    {
                        "name": name,
                        "kind": kind,
                        "verdicts": [
                            {"run": i, "verdict": r.get("verdict")} for i, r in rows
                        ],
                    }
                )

    # A check no run produced a row for, but some run named in a skip note,
    # is missing too -- that is the import limit on every sunny noon.
    for check, (index, _note) in notes.items():
        if check not in summary and check not in MODES:
            summary[check] = {
                "kind": "effect",
                "verdict": None,
                "run": index,
                "read_at": runs[index].get("read_at"),
                "established": False,
            }

    still_missing = []
    for name, row in summary.items():
        if row["established"]:
            continue
        noted = notes.get(name)
        if noted is not None and noted[0] >= row["run"]:
            why = noted[1]
        else:
            source = (readback if row["kind"] == "readback" else effects)[name]
            latest = source[-1][1]
            why = str(latest.get("detail") or latest.get("verdict"))
        still_missing.append({"name": name, "kind": row["kind"], "why": why})

    code = _worst_code([int(run["block"].get("outcome", 1)) for run in runs])
    last = runs[-1]["block"]
    return {
        "schema": LEDGER_SCHEMA,
        "outcome": code,
        "outcome_means": CODES[code],
        "conditions": dict(last.get("conditions") or {}),
        "readback": [dict(_strongest(rows)[1]) for rows in readback.values()],
        "effects": [dict(_strongest(rows)[1]) for rows in effects.values()],
        "restored": restored,
        "restart": next(
            (
                run["block"]["restart"]
                for run in reversed(runs)
                if run["block"].get("restart")
            ),
            None,
        ),
        "not_established": [item["why"] for item in still_missing] + general,
        "summary": summary,
        "still_missing": still_missing,
        "contradictions": contradictions,
        "runs": out_runs,
    }


def progress(folded: Mapping[str, Any]) -> tuple[int, int]:
    """Return (established, total) over a folded block's summary."""
    summary = folded.get("summary") or {}
    established = sum(1 for row in summary.values() if row.get("established"))
    return established, len(summary)


def status_line(folded: Mapping[str, Any], *, limit: int = 255) -> str:
    """One line for a sensor state: how far, how many runs, what is awaited."""
    established, total = progress(folded)
    runs = len(folded.get("runs") or [])
    missing = [item["name"] for item in folded.get("still_missing") or []]
    line = f"{established}/{total} established · {runs} run{'s' if runs != 1 else ''}"
    if missing:
        line += " · waiting for: " + ", ".join(missing)
    if len(line) > limit:
        line = line[: limit - 1] + "…"
    return line


def run_lines(folded: Mapping[str, Any]) -> list[str]:
    """Return a log, one line per row and note, oldest run first."""
    lines: list[str] = []
    for index, run in enumerate(folded.get("runs") or []):
        when = run.get("read_at") or "?"
        lines.append(f"{when} run {index + 1}: {run.get('outcome_means')}")
        for row in run.get("effects") or []:
            lines.append(
                f"{when} run {index + 1}: {row.get('check')}: {row.get('verdict')}"
            )
        for row in run.get("readback") or []:
            verdict = row.get("verdict")
            if verdict != MATCH:
                lines.append(f"{when} run {index + 1}: {row.get('field')}: {verdict}")
        for note in run.get("not_established") or []:
            lines.append(f"{when} run {index + 1}: {note}")
    return lines


def markdown(folded: Mapping[str, Any], *, log_lines: int = 30) -> str:
    """Render a folded block for a notification: progress, checks, the log."""
    established, total = progress(folded)
    runs = folded.get("runs") or []
    out = [
        f"**{established} of {total}** checks established over **{len(runs)}** "
        f"run{'s' if len(runs) != 1 else ''}.",
        "",
    ]
    for item in folded.get("contradictions") or []:
        verdicts = ", ".join(
            f"run {v['run'] + 1}: {v['verdict']}" for v in item["verdicts"]
        )
        out.append(f"- ⚠ **{item['name']}** disagrees between runs ({verdicts})")
    if folded.get("contradictions"):
        out.append("")
    missing = folded.get("still_missing") or []
    if missing:
        out.append("**Still waiting for:**")
        out.extend(f"- **{item['name']}**: {item['why']}" for item in missing)
        out.append("")
    done = [
        (name, row)
        for name, row in (folded.get("summary") or {}).items()
        if row.get("established")
    ]
    if done:
        out.append("**Established:**")
        out.extend(
            f"- {name}: {row['verdict']} (run {row['run'] + 1})" for name, row in done
        )
        out.append("")
    lines = run_lines(folded)[-log_lines:]
    if lines:
        out.append("**Log** (latest last):")
        out.append("```")
        out.extend(lines)
        out.append("```")
    return "\n".join(out)


# -- when to come back -------------------------------------------------------


class Live(NamedTuple):
    """The house now, from the fields the procedure samples (`base._sample`).

    `battery` is the inverter's own sign, negative while charging; `export`
    is positive while exporting. Any of them may be None: not read yet.
    """

    pv: float | None
    battery: float | None
    export: float | None
    soc: float | None


def _below(value: float | None, limit: float) -> bool:
    return value is not None and value < limit


def _above(value: float | None, limit: float) -> bool:
    return value is not None and value >= limit


#: Room in the battery for a charge the checks command, with margin under the
#: ceiling at which a pack tapers on its own.
_ROOM = SOC_CHARGE_CEILING - 5.0

#: Charge in the battery for a discharge, with margin over any minimum.
_CHARGE = 30.0

#: What each behavioural check needs the house to be doing, in words for the
#: owner and as a test on `Live`. Taken from the guards in `effects.py`, with
#: margin, so a run started for a check does not refuse it at once; a run is
#: still the judge, and a check it skips stays missing.
NEEDS: dict[str, tuple[str, Callable[[Live], bool]]] = {
    "forced charge": (
        f"the battery under {_ROOM:.0f} %",
        lambda live: _below(live.soc, _ROOM),
    ),
    "forced discharge": (
        f"the battery above {_CHARGE:.0f} %",
        lambda live: _above(live.soc, _CHARGE),
    ),
    "charge ceiling": (
        f"the battery charging, above {SOC_CEILING_FLOOR:.0f} %",
        lambda live: (
            _below(live.battery, -EFFECT_FLOOR_W)
            and _above(live.soc, SOC_CEILING_FLOOR)
            and _below(live.soc, SOC_CHARGE_CEILING)
        ),
    ),
    "export power limit": (
        "export, or a battery to discharge into the grid",
        lambda live: _above(live.export, EFFECT_FLOOR_W) or _above(live.soc, _CHARGE),
    ),
    "PV generation cut": (
        f"PV above {PV_CUT_MIN_W + EFFECT_FLOOR_W:.0f} W",
        lambda live: _above(live.pv, PV_CUT_MIN_W + EFFECT_FLOOR_W),
    ),
    "forced-charging window": (
        f"the battery under {_ROOM:.0f} %",
        lambda live: _below(live.soc, _ROOM),
    ),
    "discharge windows away from now": (
        "the battery discharging",
        lambda live: _above(live.battery, EFFECT_FLOOR_W),
    ),
    "site import limit": (
        f"dark (PV under {MIN_PV_W:.0f} W), the battery under {_ROOM:.0f} %",
        lambda live: _below(live.pv, MIN_PV_W) and _below(live.soc, _ROOM),
    ),
}

#: A skip note that waiting cannot cure: the owner's options refused it.
NEEDS_LEAVE = ("not given leave", "not asked for")


def needs_leave(item: Mapping[str, Any]) -> bool:
    """Whether a missing check waits on the owner's options, not the house."""
    return any(words in str(item.get("why")) for words in NEEDS_LEAVE)


def awaited(folded: Mapping[str, Any] | None) -> list[tuple[str, str]]:
    """Return (check, what it needs) for every check waiting can still answer.

    A readback field needs nothing but a run. Checks that wait on leave, and
    the modes of their own, are left out: no moment of the day answers them.
    """
    if folded is None:
        return [("every check", "a first run")]
    out = []
    for item in folded.get("still_missing") or []:
        name = str(item["name"])
        if needs_leave(item) or name in MODES:
            continue
        need = NEEDS.get(name)
        out.append((name, need[0] if need else "another run"))
    return out


def due(folded: Mapping[str, Any] | None, live: Live) -> list[str]:
    """Return the awaited checks the house is in a state to answer now."""
    ready = []
    for name, _words in awaited(folded):
        need = NEEDS.get(name)
        if need is None or need[1](live):
            ready.append(name)
    return ready
