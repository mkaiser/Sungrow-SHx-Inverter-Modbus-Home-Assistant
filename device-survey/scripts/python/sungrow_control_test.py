#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "sungrow-modbus==0.1.0a19",
#     "modbus-connection[tmodbus]>=4.10.0",
# ]
# ///
"""Run the control test against a real inverter, from a terminal.

This is one of the two drivers over `sungrow_modbus.control_test`; the other is
the integration's own, which runs the same procedure from a device page as part
B of the survey. Everything that decides a verdict lives in the library, so the
two cannot disagree about what a measurement means. What lives here is the
things a library has no business doing: opening a connection, asking a person a
question, writing files, and choosing an exit code.

**It writes to your inverter.** That is the point of it. The survey beside it
runs it as its last step, and only when the person running the survey said
yes to it; this file is the same test on its own, for the modes the survey
never needs -- a dry run, a restore, a start, the export-scale question.

Start with `--dry-run`. It resolves every bound, picks every probe value and
prints exactly what it would write, without writing any of it.

Everything it needs is the published `sungrow-modbus` library, pinned in the
header above. The survey's launchers fetch it through uv and hand everything
after `control` to this file:

    ./survey.sh control 192.168.1.50 --dry-run       (Linux, macOS)
    survey.cmd control 192.168.1.50 --dry-run        (Windows)

In a checkout with the library installed, run it with Python directly:

    python python/sungrow_control_test.py 192.168.1.50 --dry-run
    python python/sungrow_control_test.py 192.168.1.50
    python python/sungrow_control_test.py 192.168.1.50 --restore SNAPSHOT

Run it while the sun is up. Half the procedure measures what the inverter does
with the power it has, and in the dark there is nothing for it to do.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
import probe

from sungrow_modbus import SungrowInverter, battery
from sungrow_modbus.control_test import (
    CODES,
    ControlTest,
    Options,
    Outcome,
    Snapshot,
    document,
)
from sungrow_modbus.inverter import export_scale
from sungrow_modbus.survey_document import SCHEMA, stand_in

_LOGGER = logging.getLogger("control_test")

#: What `--restore` returns internally on success, mapped to 0 before it reaches
#: a shell. Not 0 here: a *run* also succeeds with 0, and sharing the number
#: made an ordinary run sign off with "everything in the snapshot is back" --
#: a sentence about something it had not done.
#: Exit 1 from `CODES`, named so the handler that returns it reads as what it
#: means rather than as a bare integer.
COULD_NOT_RUN = 1

RESTORED = -1

#: Cancelled at the last prompt, before anything was written.
CANCELLED = -2


def _stamp() -> str:
    """Return a sortable timestamp for this run's filenames."""
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def _workspace() -> Path:
    """Return the directory this run's files belong in: `device-survey/`.

    Anchored on the script, not the working directory, so a launcher, `make`
    and a plain `python` all land in the same place -- the folder that holds
    `scripts/`, two above this file. Nothing written there carries the serial or the
    address: the result block is anonymous by construction, and the snapshot
    holds register values. `.gitignore` covers both by name inside a checkout.
    """
    return Path(__file__).resolve().parents[2]


# -- asking ------------------------------------------------------------------

RESTART_QUESTION = """
The test can also stop the inverter and start it again, and time both.

  This writes 0xCE to register 13000, waits for the inverter to report a
  stopped state, then writes 0xCF to start it again. While it is stopped:

    * PV production stops. Everything it would have generated is lost.
    * The battery neither charges nor discharges.
    * Backup and off-grid output drop, so anything on that circuit loses
      power.
    * Home Assistant, the Sungrow app and anything else watching will see
      the inverter as unavailable, and automations may fire on that.
    * Measured so far: stopped within about 2 seconds, running again after
      3 to 4 minutes in daylight and over 6 at night, and generating up to
      20 seconds after that. The run waits up to 10 minutes for it and says
      how long it took.

  The inverter is never left stopped: if the start fails, this retries it on
  fresh connections and, failing that, prints the command to run.
"""


def _ask_restart(default: bool | None) -> bool:
    """Ask whether the run should include a stop and a start.

    Asked before anything is written, so the whole shape of the run is settled
    while it is still cheap to say no. `--restart` and `--no-restart` answer it
    in advance, which is what makes the script usable from another script.
    """
    if default is not None:
        return default
    if not sys.stdin.isatty():
        return False
    print(RESTART_QUESTION, file=sys.stderr)
    answer = input("  Do you permit the test to stop and restart the inverter? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def _ready(dry_run: bool) -> bool:
    """Wait for Enter before the first write, or say the run was cancelled.

    The questions are answered and nothing has been written yet: the last
    moment where stopping costs nothing. Skipped where nobody is at a
    terminal, so a scripted run with `--restart` or `--no-restart` goes ahead.
    """
    if not sys.stdin.isatty():
        return True
    what = "the dry run (it writes nothing)" if dry_run else "testing"
    try:
        input(f"\n  Press Enter to start {what}, or Ctrl+C to cancel. ")
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled. Nothing was written to the inverter.", file=sys.stderr)
        return False
    return True


# -- reporting ---------------------------------------------------------------


def _cell(value: Any, unit: str = "") -> str:
    """Render one value for a table, and an absence as an absence."""
    if value is None:
        return "--"
    space = " " if unit and not unit.startswith(" ") else ""
    if isinstance(value, float):
        return f"{value:g}{space}{unit}"
    return f"{value}{space}{unit}"


def _findings_section(outcome: Outcome) -> list[str]:
    """Render the findings, or say plainly that there were none.

    Both halves matter. A decade error is why this procedure exists, so it gets
    a table with the raw word beside the expected one and a column naming
    **which side** is implicated -- the library, if the map's scale disagrees
    with the specification, or the device, if they agree and the firmware
    stored something else anyway.

    And an empty findings list is stated as a sentence rather than left as a
    blank heading, because "no findings" and "this section did not run" look
    identical when the answer is nothing at all.
    """
    lines = ["## Findings", ""]
    if not outcome.findings:
        return [
            *lines,
            "Nothing came back off by a decade. Every register that was written "
            "held the word the specification says it should.",
            "",
        ]
    lines += [
        "| What | Register | Commanded | Seen | Ratio | Whose |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {row.verdict} | {row.register} "
        f"| {_cell(row.written, row.unit)} "
        f"| raw {_cell(row.raw_word)}, expected {_cell(row.expected_raw)} "
        f"| {_cell(row.ratio)} | {row.implicates or '--'} |"
        for row in outcome.probes
        if row in outcome.findings
    ]
    lines += [
        f"| {row.verdict} | {row.check} "
        f"| {_cell(row.commanded, ' ' + row.commanded_unit)} "
        f"| {_cell(row.during, ' W')} | {_cell(row.ratio)} | device |"
        for row in outcome.effects
        if row in outcome.findings
    ]
    return [*lines, ""]


def report(outcome: Outcome, *, title: str) -> str:
    """Render the run as markdown, worst news first.

    The order is the whole design of this function. A reader stops early, so
    anything the house is still carrying goes above the findings, the findings
    go above the tables, and what the run could *not* establish is a section of
    its own rather than an absence somebody has to notice.
    """
    lines = [f"# {title}", ""]
    means = _means(outcome.code, outcome.conditions.get("dry_run"))
    lines += [f"**{means}** (exit {outcome.code}).", ""]

    lines += ["## What is still changed", ""]
    if outcome.not_restored:
        lines += [
            "**The following registers were not put back.** Restore them with "
            "`--restore`, or set them by hand:",
            "",
            "| Register | Should be | Reads | Why |",
            "| --- | --- | --- | --- |",
        ]
        lines += [
            f"| `{row.field}` | {_cell(row.original)} | {_cell(row.readback)} "
            f"| {row.detail or ''} |"
            for row in outcome.not_restored
        ]
    else:
        lines.append(
            "Every setting this run touched was put back and read back at its "
            "original value."
        )
    lines.append("")

    lines += _findings_section(outcome)

    lines += ["## Readback", ""]
    if outcome.conditions.get("direct_connection") is False:
        # The caveat goes above the table rather than only in the notes,
        # because a reader skims a table and believes the word "matched".
        # Measured at gerd 2026-09-19: a dongle polled every 5 s for two
        # minutes never reported a value written over the cable, and the
        # figure it kept returning was hours old. So these verdicts describe
        # the dongle's cache, and no amount of waiting would change that.
        lines += [
            "> **Read through a WiNet-S, so this table is not evidence.** The "
            "dongle answers a stale word after forwarding a write, and it does "
            "not catch up: polled every 5 s for two minutes it never reported a "
            "value the cable confirmed. `matched` here means the cache agreed, "
            "`unchanged` cannot tell a dropped write from a stale read, and only "
            "the behavioural table below is unaffected.",
            "",
        ]
    lines += [
        "| Control | Reg | Per count | Wrote | Library read | Raw | Expected raw "
        "| Slope | Verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| `{row.field}` | {row.register} | {_cell(row.spec_units_per_count)} "
        f"{row.unit} | {_cell(row.written, row.unit)} "
        f"| {_cell(row.library_read, row.unit)} "
        f"| {_cell(row.raw_word)} | {_cell(row.expected_raw)} | {_cell(row.slope)} "
        f"| {row.verdict}{' -- ' + row.detail if row.detail else ''} |"
        for row in outcome.probes
    ]
    lines.append("")
    if "export_write_scale" in outcome.conditions:
        scale = outcome.conditions["export_write_scale"]
        lines += [
            "`export_power_limit` was written at the factor this inverter "
            + (
                f"states: it {scale['answer']} ({scale['reason']})."
                if scale and scale["write_units_per_count"] is not None
                else "could not be asked for, so divided by ten"
                + (f" ({scale['reason']})." if scale else ".")
            ),
            "",
        ]

    if outcome.effects:
        lines += [
            "## What the inverter actually did",
            "",
            "| Check | Observable | Commanded | Before | During | After | Drift "
            "| Verdict |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {row.check} | {row.observable} "
            f"| {_cell(row.commanded, ' ' + row.commanded_unit)} "
            f"| {_cell(row.before, ' W')} ±{_cell(row.before_mad)} "
            f"| {_cell(row.during, ' W')} ±{_cell(row.during_mad)} "
            f"| {_cell(row.after, ' W')} ±{_cell(row.after_mad)} "
            f"| {_cell(row.drift, ' W')} "
            f"| {row.verdict}{' -- ' + row.detail if row.detail else ''} |"
            for row in outcome.effects
        ]
        lines.append("")

    if outcome.restart is not None:
        restart = outcome.restart
        lines += [
            "## The restart",
            "",
            "Numbers this project has not had before: how long a Modbus stop and "
            "start actually takes on this model.",
            "",
            f"* stopped after **{_cell(restart.stopped_after, ' s')}**",
            f"* running again after **{_cell(restart.running_after, ' s')}**",
            f"* generating again after **{_cell(restart.generating_after, ' s')}**",
            "* polls that could not connect at all: "
            f"{restart.polls_refused_connection}",
            f"* settings survived the restart: {_cell(restart.settings_survived)}",
            "",
        ]

    lines += ["## Conditions", ""]
    lines += [f"* {key}: {value}" for key, value in outcome.conditions.items()]
    lines.append("")

    lines += ["## What this run could not establish", ""]
    if outcome.unestablished:
        lines += [f"* {sentence}" for sentence in outcome.unestablished]
    else:
        lines.append("Every check the procedure knows how to make, it made.")
    lines.append("")
    return "\n".join(lines)


def summarise(outcome: Outcome) -> str:
    """Render the few lines a person reads in the terminal."""
    counted: dict[str, int] = {}
    for row in outcome.probes:
        counted[row.verdict] = counted.get(row.verdict, 0) + 1
    parts = [f"{count} {verdict}" for verdict, count in sorted(counted.items())]
    return ", ".join(parts) or "nothing was written"


# -- connecting and running --------------------------------------------------


class _Terminal:
    """Progress lines, and a dot per `WAIT_TICK` while a restart is waited out.

    The dots share a line, so the next progress line first ends it.
    """

    def __init__(self) -> None:
        self._dotted = False

    def progress(self, fraction: float, label: str) -> None:
        self.end()
        print(f"  [{fraction:>4.0%}] {label}", file=sys.stderr)

    def dot(self) -> None:
        print("." if self._dotted else "  .", end="", file=sys.stderr, flush=True)
        self._dotted = True

    def end(self) -> None:
        if self._dotted:
            print(file=sys.stderr)
            self._dotted = False


async def _connect(host: str, port: int, unit_id: int, timeout: float) -> Any:
    """Open one connection and return it with its unit handle."""
    connection = ModbusConnection(
        ModbusTcpParams(host=host, port=port), timeout=timeout
    )
    return connection, connection.for_unit(unit_id)


#: Attempts at each of the two opening reads, and the pause between them.
#:
#: Both need them, and for the same reason. The library treats a *lost
#: connection* as fatal to a whole poll -- rightly, since retrying the
#: remaining components would only multiply the timeout -- so one dropped read
#: propagates all the way out here. On a house where something else is already
#: polling the inverter, which is every house worth running this on, that is a
#: moment rather than a state: the second attempt normally succeeds.
#:
#: Measured. The first daylight run against the reference SH10RT died on
#: `read_input_registers(5010, 25): Connection lost before response was
#: received` during this very call, with the YAML package polling alongside,
#: and the identical read answered immediately afterwards.
#: Escalating, and the last step is the load-bearing one. A Sungrow grants very
#: few sessions and reclaims them slowly: `doc/development.yaml` records that
#: after the link starts refusing, **90 seconds of quiet** is what fixes it.
#: Retrying three seconds apart therefore does not retry at all -- it spends
#: four attempts inside the window where nothing can work, which is exactly
#: what the first daylight run did, failing at 5010, then 5114, then 5241,
#: each attempt getting a little further into a poll before the link dropped.
OPENING_BACKOFF = (5.0, 20.0, 45.0, 90.0)


async def _retrying(what: str, read: Callable[[], Awaitable[Any]]) -> Any:
    """Run one opening read, backing off far enough to outlast contention."""
    attempts = len(OPENING_BACKOFF) + 1
    for attempt in range(1, attempts + 1):
        try:
            return await read()
        except (ModbusError, TimeoutError, OSError) as err:
            if attempt > len(OPENING_BACKOFF):
                raise
            pause = OPENING_BACKOFF[attempt - 1]
            _LOGGER.warning(
                "%s attempt %d of %d failed (%s), waiting %.0fs -- a Sungrow "
                "grants few sessions and wants quiet to reclaim them",
                what,
                attempt,
                attempts,
                err,
                pause,
            )
            await asyncio.sleep(pause)
    return None


async def _prepare(inverter: SungrowInverter) -> None:
    """Read identity and every tier, retrying both against a contended link."""
    await _retrying("identity", inverter.async_update_identity)
    await _retrying("first full read", inverter.async_update)


def _save(directory: Path, stamp: str, name: str, text: str) -> Path:
    """Write one of this run's files, flushed to the disk before returning."""
    path = directory / f"{stamp}-{name}"
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    return path


async def _restore_mode(inverter: SungrowInverter, args: argparse.Namespace) -> int:
    """Put a saved snapshot back, and report what could not be put back.

    The way out of a run that died halfway. Idempotent by construction: it
    reads each register before writing it, so running it when nothing is
    actually wrong costs one read per control and changes nothing.
    """
    saved = Snapshot.from_dict(json.loads(Path(args.restore).read_text()))
    terminal = _Terminal()
    run = ControlTest(
        inverter, options=Options(dry_run=args.dry_run), on_wait=terminal.dot
    )
    if saved.stopped_at is not None:
        print(
            "This snapshot was taken with the inverter stopped. Starting it "
            "before anything else; this may take some minutes.",
            file=sys.stderr,
        )
        await run.async_ensure_running()
        terminal.end()
    results = await run.async_restore(saved)
    for row in results:
        mark = "restored" if row.restored else "COULD NOT RESTORE"
        print(f"  {row.field}: {mark} ({row.attempts} attempts)")
    missing = [row.field for row in results if not row.restored]
    if missing:
        print(
            f"\n{len(missing)} register(s) would not take the write: "
            f"{', '.join(missing)}. Check that nothing else is polling "
            "the inverter, then run this again -- it is safe to repeat.",
            file=sys.stderr,
        )
        return 5
    if not args.dry_run:
        # Everything is back and read back, so the snapshot has done its job;
        # left behind it would turn the next look into a false alarm.
        Path(args.restore).unlink(missing_ok=True)
    print(
        f"\nPut {len(results)} register(s) back, and read each one to check it took.",
        file=sys.stderr,
    )
    return RESTORED


async def _export_scale_mode(
    inverter: SungrowInverter, args: argparse.Namespace, serial: str | None
) -> int:
    """Ask how this firmware writes 13074, and nothing else.

    At most one write, chosen so that it changes nothing on either known
    firmware -- `sungrow_modbus.inverter.export_scale` has the argument. With
    `--enable-export-limit` it may switch feed-in limitation on for that one
    write, and only where the limit already held caps nothing. Exit 0 with an
    answer, 3 without one, 5 if anything was left changed.
    """
    result = await export_scale.async_probe(
        inverter, lift_mode=args.enable_export_limit, dry_run=args.dry_run
    )
    answer = export_scale.ANSWERS[result.write_units_per_count]
    print(f"\n13074 write scale: {answer}", file=sys.stderr)
    print(f"  held     {result.held} W", file=sys.stderr)
    if result.wrote is not None:
        print(f"  wrote    {result.wrote}", file=sys.stderr)
        print(f"  answer   {result.response}", file=sys.stderr)
    if result.mode_lifted:
        print(
            "  feed-in limitation was lifted for the write and put back",
            file=sys.stderr,
        )
    print(f"  because  {result.reason}", file=sys.stderr)
    if args.merge_into and not args.dry_run:
        path = _merge(
            Path(args.merge_into),
            "export_scale",
            # The date, as the document's own `read_on` gives it: the block is
            # usually merged into a reading taken on another day.
            {
                **export_scale.document(result),
                "read_on": datetime.now().date().isoformat(),
            },
            serial,
            args.host,
        )
        print(f"\nWrote:\n  {path}  (send this)", file=sys.stderr)
    if result.left_changed:
        return 5
    return 0 if result.write_units_per_count is not None else 3


async def _start_only_mode(inverter: SungrowInverter) -> int:
    """Start the inverter and wait for it, and nothing else.

    The command every failure path names. It was referenced in three places
    before it existed -- including as the recovery to type when an inverter
    has not come back, which is the worst possible moment to be handed a
    command that is not there.
    """
    # Writing 0xCF to an inverter that is already running is a no-op, so this
    # doubles as a way to prove the write path to register 13000 works before
    # trusting it with a stop.
    terminal = _Terminal()
    run = ControlTest(inverter, on_wait=terminal.dot)
    print("Starting the inverter; this may take some minutes.", file=sys.stderr)
    started = await run.async_ensure_running()
    terminal.end()
    print(
        "the inverter reports a running state"
        if started
        else "the inverter has NOT reported a running state",
        file=sys.stderr,
    )
    return 0 if started else 5


async def _run(args: argparse.Namespace) -> int:
    """Do the whole thing, and return the exit code."""
    directory = _workspace()
    stamp = _stamp()
    snapshot_path = directory / f"{stamp}-snapshot.json"

    connection, unit = await _connect(args.host, args.port, args.unit, args.timeout)
    inverter = SungrowInverter(unit)
    try:
        await _prepare(inverter)
        serial = inverter.serial_number

        if args.restore:
            return await _restore_mode(inverter, args)

        if args.start_only:
            return await _start_only_mode(inverter)

        if args.export_scale:
            return await _export_scale_mode(inverter, args, serial)

        restart = _ask_restart(args.restart)
        # A simulator has no house to protect, and `make controltest-sim` is
        # run from a terminal; waiting there for Enter would only be in the way.
        # `--yes` is consent given before the run: the survey asks it among its
        # questions, a quarter of an hour before this point, and runs unattended.
        if not (args.simulated or args.yes) and not _ready(args.dry_run):
            return CANCELLED

        async def keep(snapshot: Snapshot) -> None:
            snapshot_path.write_text(json.dumps(snapshot.to_dict(), indent=2))

        options = Options(
            allow_dark=args.allow_dark,
            enable_export_limit=args.enable_export_limit,
            cut_pv=args.cut_pv,
            # `--restart-only` is a request to restart, so it implies it rather
            # than quietly measuring nothing when the question is declined.
            restart=restart or args.restart_only,
            restart_only=args.restart_only,
            simulated=args.simulated,
            dry_run=args.dry_run,
        )
        print(
            f"Writing to {args.host}:{args.port}, unit {args.unit}. "
            f"{'Nothing will be written: this is a dry run.' if args.dry_run else ''}",
            file=sys.stderr,
        )
        terminal = _Terminal()
        # A pack on its own unit is what the inverter's registers cannot show,
        # and with an SBR's capacity it sets the battery's write bounds from
        # the datasheet, as the integration does.
        pack_unit = await battery.probe_units(connection.for_unit)
        run = ControlTest(
            inverter,
            options=options,
            on_progress=terminal.progress,
            on_wait=terminal.dot,
            # A dry run writes nothing, so there is nothing to put back and no
            # before-state worth keeping.
            on_snapshot=None if args.dry_run else keep,
            sungrow_pack=pack_unit is not None,
        )
        outcome = await run.async_run()
    finally:
        await connection.close()

    # Removed only once everything is back and read back; anything else keeps
    # it, and the hint below names it.
    if not outcome.not_restored and outcome.code != 5:
        snapshot_path.unlink(missing_ok=True)

    title = f"Control test -- {inverter.model or 'unknown model'}"
    # Printed rather than saved: the one file a run writes is the result block,
    # and this is the same result for a person to read now. The stand-in, not
    # the serial, so a pasted transcript carries nothing that identifies a house.
    print(
        "\n"
        + report(outcome, title=f"{title} ({stand_in(serial) if serial else 'anon'})"),
        file=sys.stderr,
    )
    block = document(outcome)

    # A file that cannot be written is not a link that failed, and after a
    # whole run it must not be reported as one: the outer handler's "nothing
    # ran -- could not connect" was printed beneath a complete report. The
    # outcome stands and keeps its exit code; what was not written is said.
    paths: list[Path] = []
    unwritten: list[str] = []
    try:
        paths.append(
            _save(directory, stamp, "control_test.json", json.dumps(block, indent=2))
        )
    except OSError as err:
        unwritten.append(f"the result block, beside the script: {err}")
    if args.merge_into:
        try:
            paths.append(
                _merge(Path(args.merge_into), "control_test", block, serial, args.host)
            )
        except (OSError, ValueError) as err:
            kept = f"; the result is in {paths[0]}" if paths else ""
            unwritten.append(f"the merge into {args.merge_into}: {err}{kept}")

    # The count alone: what the run could not establish is a section of the
    # report printed above, and saying it twice buried the files list.
    print(f"\n{summarise(outcome)}", file=sys.stderr)
    print("\nWrote:", file=sys.stderr)
    for path in paths:
        print(f"  {path}  (send this)", file=sys.stderr)
    for what in unwritten:
        print(f"  NOT WRITTEN: {what}", file=sys.stderr)
    if snapshot_path.exists():
        print(
            f"  {snapshot_path}  (the before-state; --restore takes it)",
            file=sys.stderr,
        )
    if outcome.not_restored:
        print(
            "\nSomething was not put back. Run:\n"
            f"  ./survey.sh control {args.host} --port {args.port} --unit {args.unit} "
            f"--restore {snapshot_path}",
            file=sys.stderr,
        )
    return outcome.code


def _caller_path(value: str) -> Path:
    """Resolve a path argument the way the person typing it meant it.

    The launchers change into their own folder before starting this, so a
    relative path is resolved against the directory they were started from,
    which they pass as `SUNGROW_CALLER_DIR`.
    """
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return Path(os.environ.get("SUNGROW_CALLER_DIR", os.getcwd())) / path


def _merge(
    target: Path, key: str, block: dict[str, Any], serial: str | None, host: str
) -> Path:
    """Fold the block into an existing survey document, and refuse to leak.

    The block is anonymous by construction -- register numbers, chosen values,
    words that came back -- so there is nothing in it for a redaction step to
    miss. This checks anyway, and **refuses to write** rather than publishing on
    the assumption: a refusal costs somebody a minute, and the alternative costs
    somebody else their serial number in a public repository forever.
    """
    text = json.dumps(block)
    if serial and serial in text:
        raise SystemExit(f"refusing to merge: the block contains the serial ({target})")
    if host in text:
        raise SystemExit(
            f"refusing to merge: the block contains the address ({target})"
        )

    document_data = json.loads(target.read_text())
    if key == "export_scale" and document_data.get("schema", 0) < SCHEMA:
        # The schema says what a document *can* carry, so a reader takes the
        # block's absence as "not asked". A document from before 19 lacks
        # other fields that number promises; survey it again instead.
        if document_data.get("schema", 0) < SCHEMA - 1:
            raise SystemExit(
                f"refusing to merge: {target} is at schema "
                f"{document_data.get('schema')}, too old to be stamped {SCHEMA}"
            )
        document_data["schema"] = SCHEMA
    document_data[key] = block
    target.write_text(json.dumps(document_data, indent=2) + "\n")
    return target


class _LinkDrops(logging.Handler):
    """Count the Modbus backend's reconnects instead of printing each one.

    `tmodbus` logs every connection it opens and every one the inverter drops,
    and re-opens it by itself. Printed as they happen they are noise: the run
    carries on, and a read that really fails is reported by `_retrying` or ends
    the run with exit 1. What they say together is worth one line -- a Sungrow
    that keeps dropping the link has another client polling it.
    """

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "connection lost" in message or "closed by remote host" in message:
            self.count += 1


def _quiet_backend() -> _LinkDrops:
    """Keep the backend's connection log off the terminal, and count drops."""
    drops = _LinkDrops()
    backend = logging.getLogger("tmodbus")
    backend.addHandler(drops)
    backend.propagate = False
    return drops


def _say_drops(drops: _LinkDrops) -> None:
    """One line about the dropped connections, if there were any."""
    if drops.count:
        print(
            f"\nThe inverter dropped the connection {drops.count} time(s); each "
            "was re-opened and the run carried on. Frequent drops mean "
            "something else is polling it -- stop Home Assistant for a "
            "cleaner run.",
            file=sys.stderr,
        )


#: The library's `control_test.DRY_RUN_MEANS`, kept here because this script
#: runs on the published library, which may predate it.
#: `test_control_test_cli.py` holds the two equal.
DRY_RUN_MEANS = "dry run: the plan resolved, and nothing was written"


def _means(code: int, dry_run: bool | None) -> str:
    """Return the sentence for an exit code; a dry run's 0 says what it did."""
    return DRY_RUN_MEANS if dry_run and code == 0 else CODES[code]


def _parser() -> argparse.ArgumentParser:
    """Return the command line, which the survey also builds its run from."""
    parser = argparse.ArgumentParser(
        description="Write each control, read it back, and check the scale.",
        epilog="Start with --dry-run. It writes nothing.",
    )
    parser.add_argument("host", help="the inverter's address")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve everything and write nothing",
    )
    parser.add_argument(
        "--allow-dark",
        action="store_true",
        help="run without PV; the behavioural half will establish nothing",
    )
    parser.add_argument(
        "--enable-export-limit",
        action="store_true",
        help="turn feed-in limitation on for the test, and off again afterwards",
    )
    parser.add_argument(
        "--cut-pv",
        action="store_true",
        help="cut PV generation through register 31211 for about a minute, and "
        "watch DC power fall to zero; where the inverter has the register",
    )
    restart = parser.add_mutually_exclusive_group()
    restart.add_argument(
        "--restart",
        dest="restart",
        action="store_true",
        default=None,
        help="stop and start the inverter, and time it, without asking",
    )
    restart.add_argument(
        "--no-restart",
        dest="restart",
        action="store_false",
        help="skip the restart without asking",
    )
    parser.add_argument(
        "--start-only",
        action="store_true",
        help="just start the inverter and confirm it runs; the recovery command",
    )
    parser.add_argument(
        "--restart-only",
        action="store_true",
        help="measure the stop and start and nothing else; writes no control",
    )
    parser.add_argument(
        "--export-scale",
        action="store_true",
        help="ask how this firmware writes 13074 (times ten, or as handed) with "
        "one write that changes nothing on either, and do nothing else",
    )
    parser.add_argument(
        "--simulated",
        action="store_true",
        help="stamp the report as evidence about nothing; for a simulator",
    )
    parser.add_argument(
        "--restore", help="put a saved snapshot back, and do nothing else"
    )
    parser.add_argument(
        "--merge-into", help="fold the result into an existing survey document"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="consent was given already; start without waiting for Enter",
    )
    return parser


def _resolve_paths(args: argparse.Namespace) -> bool:
    """Resolve the path arguments, and say whether every one is there.

    Checked before anything connects: a document that is not there would
    otherwise surface after a whole run, restart included, and be reported as
    a link that never came up.
    """
    for name in ("merge_into", "restore"):
        if (value := getattr(args, name)) is None:
            continue
        path = _caller_path(value)
        if not path.is_file():
            print(f"--{name.replace('_', '-')}: no such file: {path}", file=sys.stderr)
            return False
        setattr(args, name, str(path))
    return True


async def async_main(args: argparse.Namespace, drops: _LinkDrops) -> int:
    """Run with parsed arguments inside a running loop, and return the exit code.

    The survey's way in: it already has a loop and its own count of dropped
    connections, so this takes both rather than starting either.
    """
    try:
        code = await _run(args)
    except (ModbusError, TimeoutError, OSError) as err:
        # Exit 1 exists for exactly this and was unreachable: `_retrying`
        # re-raises once it has spent 5, 20, 45 and 90 seconds of backoff, and
        # nothing caught it, so the most common failure this project documents
        # ended in a traceback through somebody else's library. The exit codes
        # are printed as the last line precisely because a pasted transcript
        # loses `$?`, and a stack trace defeats that where it is needed most.
        #
        # Measured 2026-09-20 against a house over a VPN whose Home Assistant
        # was polling: `read_input_registers(5114, 2): Connection lost before
        # response was received` -- 5114 being one of the three addresses
        # where such a run dies: the progressive signature of session
        # exhaustion in `.wiki/wiki/concepts/contention.md`.
        print(f"\n{err}", file=sys.stderr)
        print(
            "\nA Sungrow grants few Modbus sessions and wants about 90 seconds "
            "of quiet to reclaim them. If something else is polling this "
            "inverter -- a Home Assistant, another survey -- stop it and try "
            "again; reads that die a little further into the poll each time "
            "are contention, not a broken register.",
            file=sys.stderr,
        )
        _say_drops(drops)
        print(f"\nexit {COULD_NOT_RUN}: {CODES[COULD_NOT_RUN]}", file=sys.stderr)
        return COULD_NOT_RUN
    _say_drops(drops)
    if code == CANCELLED:
        print(
            f"\nexit {COULD_NOT_RUN}: nothing ran -- cancelled before anything "
            "was written",
            file=sys.stderr,
        )
        return COULD_NOT_RUN
    if code == RESTORED:
        # A restore is not a run, so it does not get a run's verdict. Saying
        # "every planned check ran" after putting things back would be a
        # sentence about something that did not happen.
        print("\nexit 0: everything in the snapshot is back", file=sys.stderr)
        return 0
    print(f"\nexit {code}: {_means(code, args.dry_run)}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run."""
    args = _parser().parse_args(argv)
    if not _resolve_paths(args):
        return 2
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    drops = _quiet_backend()
    try:
        return probe.run(async_main(args, drops))
    except KeyboardInterrupt:
        _say_drops(drops)
        print(
            "\nInterrupted. Everything this run wrote has been put back; if the "
            "last line below says otherwise, use --restore.",
            file=sys.stderr,
        )
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
