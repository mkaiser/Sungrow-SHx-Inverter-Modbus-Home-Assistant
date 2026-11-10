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

from .coverage import (
    CHECK_REVISIONS,
    EFFECT_FIELDS,
    READBACK,
    RESTART,
    WRITE_PATH_CHECKS,
)
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
    STALE_READBACK,
    STOPPED,
    STOPPED_W,
    UNCHANGED,
    UNCURABLE,
    UNSAFE_STATE,
    USER_DECLINED,
    WINDOW_START_W,
    bound_check,
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
    STOPPED: 1,
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
    ("no charging threshold check", "charging start threshold"),
    ("no discharging threshold check", "discharging start threshold"),
    # The write-path checks start their notes with their own name.
    *((name, name) for name in sorted(WRITE_PATH_CHECKS)),
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


def run_revision(block: Mapping[str, Any], name: str) -> int:
    """Return the revision of check `name` a run's block was measured with.

    `name` is a behavioural check, `READBACK` for every readback row, or
    `RESTART`. A block from before `CHECK_REVISIONS` ran revision 1.
    """
    return int((block.get("revisions") or {}).get(name, 1))


def _current(block: Mapping[str, Any], name: str) -> bool:
    """Whether a run measured `name` with the logic this library runs."""
    return run_revision(block, name) == CHECK_REVISIONS.get(name, 1)


def _worst_code(codes: Sequence[int]) -> int:
    known = [code for code in codes if code in SEVERITY]
    return max(known, key=SEVERITY.index) if known else 1


def _through_dongle(row: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a readback row of a run through a WiNet-S, as far as it is evidence.

    A dongle answers with the word it held before it forwarded a write, so
    its "kept its old value" settles nothing. A run kept before the probe
    recorded it so is read the way the probe now records it.
    """
    if row.get("verdict") != UNCHANGED:
        return row
    return {**row, "verdict": INCONCLUSIVE, "detail": STALE_READBACK}


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
    already_original = 0
    for index, run in enumerate(runs):
        block = run["block"]
        direct = (block.get("conditions") or {}).get("direct_connection") is True
        for row in block.get("readback") or []:
            readback.setdefault(str(row.get("field")), []).append(
                (index, row if direct else _through_dongle(row))
            )
        for row in block.get("effects") or []:
            effects.setdefault(str(row.get("check")), []).append((index, row))
        for row in block.get("restored") or []:
            # A register the restore found holding its original word needed
            # nothing, and on a whole run that is most of them: counted, so
            # what was written back, or could not be, is what the list shows.
            # Each run in `runs` keeps every row.
            if row.get("restored") and not row.get("attempts"):
                already_original += 1
            else:
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
            # A run measured with an older revision of the check's logic
            # speaks only until a run with the current one has: then it is
            # left out here (it stays whole in `runs`), and until then it
            # establishes nothing, so the check is measured again.
            check = READBACK if kind == "readback" else name
            fresh = [(i, r) for i, r in rows if _current(runs[i]["block"], check)]
            stale = not fresh
            rows = fresh or rows
            table[name] = rows
            index, row = _strongest(rows)
            summary[name] = {
                "kind": kind,
                "verdict": row.get("verdict"),
                "run": index,
                "read_at": runs[index].get("read_at"),
                "established": _rank(row) >= ESTABLISHED and not stale,
            }
            if stale:
                summary[name]["outdated"] = True
            if kind == "effect":
                summary[name]["moments"] = sorted(
                    {
                        moment_of(runs[i]["block"].get("conditions") or {})
                        for i, r in rows
                        if _rank(r) >= ESTABLISHED
                    }
                    - {None}
                )
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
        if row.get("outdated"):
            why = f"{name}: measured with an older revision of the test"
        elif noted is not None and noted[0] >= row["run"]:
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
        "restored_already_original": already_original,
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


def unfold(
    block: Mapping[str, Any],
    *,
    read_at: str | None,
    readings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return a block's runs, in the shape `fold` takes, to fold one more in.

    A folded block (schema 3) gives its runs back, each with the readings it
    had where `readings_changed` says what moved. A single run's block has no
    date of its own; it is given `read_at`, which a caller takes from the
    document it sits in -- the reading's date, which the block may be older
    than, and no later.
    """
    if block.get("schema") != LEDGER_SCHEMA:
        return [{"read_at": read_at, "block": dict(block)}]
    runs = []
    for entry in block.get("runs") or []:
        run_block = {
            key: value
            for key, value in entry.items()
            if key not in ("read_at", "readings_changed")
        }
        run: dict[str, Any] = {"read_at": entry.get("read_at"), "block": run_block}
        if readings is not None and "readings_changed" in entry:
            run["readings"] = {**readings, **entry["readings_changed"]}
        runs.append(run)
    return runs


#: Behavioural checks measured once more at the other moment of the day,
#: once established at one: a firmware that obeys a forced charge in sun
#: may not at night, where PV no longer covers the house around it. Never
#: more than the two moments, so a collection still ends.
TWO_MOMENTS = frozenset(
    {"forced charge", "forced discharge", "charge ceiling", "export power limit"}
)


def moment_of(conditions: Mapping[str, Any]) -> str | None:
    """Return "day" or "night" for a run's conditions, by its PV; None unread."""
    pv = conditions.get("pv_w")
    if pv is None:
        return None
    return "day" if float(pv) >= MIN_PV_W else "night"


def live_moment(live: Live) -> str | None:
    """Return the moment the house is in now, as `moment_of` names it."""
    return moment_of({"pv_w": live.pv})


def _wants_moment(name: str, row: Mapping[str, Any], moment: str | None) -> bool:
    """Whether an established check is worth measuring again at `moment`."""
    moments = row.get("moments")
    return (
        moment is not None
        and name in TWO_MOMENTS
        and moments is not None
        and moment not in moments
        and len(moments) < 2
    )


def established(
    folded: Mapping[str, Any] | None, moment: str | None = None
) -> frozenset[str]:
    """Return the checks a run may leave out (`Options.skip`): every established one.

    A check two runs disagree on is not among them, however strong its best
    verdict: `contradictions` wants another run, not fewer. Given the moment
    the run starts in, a check in `TWO_MOMENTS` established only at the other
    one is not among them either, so a run that happens anyway measures it
    there too; no run is started for that alone.
    """
    if folded is None:
        return frozenset()
    contradicted = {item.get("name") for item in folded.get("contradictions") or []}
    names = {
        name
        for name, row in (folded.get("summary") or {}).items()
        if row.get("established")
        and name not in contradicted
        and row.get("kind") != PLAUSIBILITY
        and not _wants_moment(name, row, moment)
    }
    # A restart measured once, back to running, is not worth stopping the
    # house again for; clearing the history measures it afresh.
    restart = folded.get("restart") or {}
    restarted_in: Mapping[str, Any] = next(
        (run for run in reversed(folded.get("runs") or []) if run.get("restart")),
        {},
    )
    if restart.get("running_after") is not None and _current(restarted_in, RESTART):
        names.add(RESTART)
    return frozenset(names)


def progress(folded: Mapping[str, Any]) -> tuple[int, int]:
    """Return (established, total) over a folded block's summary."""
    summary = folded.get("summary") or {}
    established = sum(1 for row in summary.values() if row.get("established"))
    return established, len(summary)


#: The outcome buckets a folded block's checks are counted in, in the order a
#: person reads them. Every check lands in exactly one, so they add up to the
#: total; which one is decided by its strongest verdict's `RANK` alone.
#:
#: - `passed`: the specification held (a match, or an effect confirmed);
#: - `failed`: the specification is wrong for this device (a finding: off by
#:   a decade, scaled, sign inverted). A contradiction counts here, because
#:   the finding is the row a fold shows;
#: - `not_supported`: the device answered, otherwise than documented
#:   (refused, clamped, unchanged, no effect, not capable);
#: - `inconclusive`: it ran, and could not tell;
#: - `not_run`: the moment, the link or the leave was missing, or no run
#:   reached it at all.
BUCKETS: tuple[str, ...] = (
    "passed",
    "failed",
    "not_supported",
    "inconclusive",
    "not_run",
)


def bucket(verdict: str | None) -> str:
    """Return the outcome bucket of one check's strongest verdict."""
    if verdict is None:
        return "not_run"
    rank = RANK.get(verdict)
    if rank == FINDING:
        return "failed"
    if rank == ANSWERED:
        return "passed"
    if rank == ESTABLISHED:
        return "not_supported"
    if verdict == INCONCLUSIVE:
        return "inconclusive"
    return "not_run"


def counts(folded: Mapping[str, Any]) -> dict[str, int]:
    """Count a folded block's checks per bucket; they sum to `progress`'s total."""
    out = dict.fromkeys(BUCKETS, 0)
    for row in (folded.get("summary") or {}).values():
        out[bucket(row.get("verdict"))] += 1
    return out


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


def _source(row: Mapping[str, Any]) -> str:
    """Name where a summary row's verdict came from, for a person."""
    if row.get("kind") == PLAUSIBILITY:
        return str(row.get("detail") or "readings")
    return f"run {int(row['run']) + 1}"


#: How a summary row from the readings, not from a run, is marked
#: (`plausibility.KIND`).
PLAUSIBILITY = "plausibility"


def with_plausibility(
    folded: Mapping[str, Any] | None, rows: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any] | None:
    """Return the folded block with the readings' checks counted in it.

    `rows` is `Plausibility.summary()`. Its rows join `summary`, so the
    counters, `progress` and the notification count them with the writes;
    the unsettled ones join `still_missing`, marked so that `awaited` never
    starts a run for them -- a run cannot answer what only time can. The
    block a run publishes is never this one: `fold` builds that.
    """
    if not rows:
        return dict(folded) if folded is not None else None
    out: dict[str, Any] = dict(folded or {})
    out["summary"] = {**(out.get("summary") or {}), **rows}
    out["still_missing"] = [
        *(out.get("still_missing") or []),
        *(
            {
                "name": name,
                "kind": PLAUSIBILITY,
                "why": f"{name}: waits for {row.get('needs')} ({row.get('detail')})",
            }
            for name, row in rows.items()
            if not row.get("established")
        ),
    ]
    return out


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
        out.extend(f"- {name}: {row['verdict']} ({_source(row)})" for name, row in done)
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

#: The most a battery may move for a start threshold at its 1000 W maximum
#: to stand clear above it (`effects._start_power_effects`).
_THRESHOLD_FLOW = 1000.0 - EFFECT_FLOOR_W

#: Where the minimum state of charge's bound may be probed: its 50 % maximum,
#: a step above it, and strictly more than the readback walk's margin under
#: the battery (`preflight._safe_soc_probe`).
_MIN_SOC_BOUND = 50.0 + 1.0 + 5.0 + 1.0

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
        f"the battery under {_ROOM:.0f} % and not charging",
        lambda live: _below(live.soc, _ROOM) and _above(live.battery, -WINDOW_START_W),
    ),
    "charging start threshold": (
        f"the battery charging {STOPPED_W:.0f} to {_THRESHOLD_FLOW:.0f} W, "
        "nothing exported",
        lambda live: (
            _above(live.battery, -_THRESHOLD_FLOW)
            and _below(live.battery, -STOPPED_W + 1)
            and _below(live.export, EFFECT_FLOOR_W)
        ),
    ),
    "discharging start threshold": (
        f"the battery discharging {STOPPED_W:.0f} to {_THRESHOLD_FLOW:.0f} W, "
        "nothing imported",
        lambda live: (
            _above(live.battery, STOPPED_W)
            and _below(live.battery, _THRESHOLD_FLOW + 1)
            and _above(live.export, -EFFECT_FLOOR_W)
        ),
    ),
    "discharge windows away from now": (
        "the battery discharging",
        lambda live: _above(live.battery, EFFECT_FLOOR_W),
    ),
    "site import limit": (
        f"dark (PV under {MIN_PV_W:.0f} W), the battery under {_ROOM:.0f} %",
        lambda live: _below(live.pv, MIN_PV_W) and _below(live.soc, _ROOM),
    ),
    **dict.fromkeys(WRITE_PATH_CHECKS, ("a run", lambda live: True)),
    # A floor offered a step above its 50 % maximum, only under a battery
    # well above it (`preflight._safe_soc_probe`).
    bound_check("battery_min_soc"): (
        f"the battery above {_MIN_SOC_BOUND:.0f} %",
        lambda live: _above(live.soc, _MIN_SOC_BOUND),
    ),
}

#: A skip note that waiting cannot cure: the owner's options refused it.
NEEDS_LEAVE = ("not given leave", "not asked for", UNCURABLE)


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
        if needs_leave(item) or name in MODES or item.get("kind") == PLAUSIBILITY:
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
