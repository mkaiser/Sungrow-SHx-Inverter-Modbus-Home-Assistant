#!/usr/bin/env python3
"""Run the control test against a real inverter, from a terminal.

This is one of the two drivers over `sungrow_modbus.control_test`; the other is
the integration's own, which runs the same procedure from a device page as part
B of the survey. Everything that decides a verdict lives in the library, so the
two cannot disagree about what a measurement means. What lives here is the
things a library has no business doing: opening a connection, asking a person a
question, writing files, and choosing an exit code.

**It writes to your inverter.** That is the point of it, and it is why nothing
in `scripts/sungrow_scan/` does: that directory ships as a zip to strangers and
promises in six places that no file in it can write a register. This one is not
in the zip and never will be.

Start with `--dry-run`. It resolves every bound, picks every probe value and
prints exactly what it would write, without writing any of it.

    python scripts/sungrow_control_test.py 192.168.1.50 --dry-run
    python scripts/sungrow_control_test.py 192.168.1.50
    python scripts/sungrow_control_test.py 192.168.1.50 --restore .testdata/...json

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
from pathlib import Path
import sys
from typing import Any

from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from sungrow_modbus import SungrowInverter
from sungrow_modbus.control_test import (
    CODES,
    ControlTest,
    Options,
    Outcome,
    Snapshot,
    document,
)
from sungrow_modbus.fingerprint import stand_in

#: Where a run's private record goes. Gitignored, and it carries the real serial
#: and the real address -- which is exactly why the publishable block is built
#: separately rather than by redacting this.
PRIVATE_DIR = Path(".testdata/control-tests")

_LOGGER = logging.getLogger("control_test")

#: What `--restore` returns internally on success, mapped to 0 before it reaches
#: a shell. Not 0 here: a *run* also succeeds with 0, and sharing the number
#: made an ordinary run sign off with "everything in the snapshot is back" --
#: a sentence about something it had not done.
#: Exit 1 from `CODES`, named so the handler that returns it reads as what it
#: means rather than as a bare integer.
COULD_NOT_RUN = 1

RESTORED = -1


def _stamp() -> str:
    """Return a sortable timestamp for this run's filenames."""
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def _workspace() -> Path:
    """Return the directory this run's files belong in, creating it.

    Inside a checkout that is `.testdata/control-tests`, which is gitignored.
    Outside one it is the working directory, visibly, so nobody is left
    wondering where a file carrying their serial number went.
    """
    root = Path(__file__).resolve().parent.parent
    if (root / ".git").exists():
        directory = root / PRIVATE_DIR
    else:
        directory = Path.cwd() / "sungrow-control-test"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# -- asking ------------------------------------------------------------------

RESTART_QUESTION = """
Also stop and restart the inverter as part of this run?

  This writes 0xCE to register 13000, waits for the inverter to report a
  stopped state, then writes 0xCF to start it again. While it is stopped:

    * PV production stops. Everything it would have generated is lost.
    * The battery neither charges nor discharges.
    * Backup and off-grid output drop, so anything on that circuit loses
      power.
    * Home Assistant, the Sungrow app and anything else watching will see
      the inverter as unavailable, and automations may fire on that.
    * How long it takes to come back has never been measured in this
      project. Expect tens of seconds; this run will time it and say. It
      may add several minutes.

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
    answer = input("  Stop and start the inverter? [y/N] ").strip().lower()
    return answer in ("y", "yes")


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
    lines += [f"**{CODES[outcome.code]}** (exit {outcome.code}).", ""]

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
        import os

        os.fsync(handle.fileno())
    return path


async def _restore_mode(inverter: SungrowInverter, args: argparse.Namespace) -> int:
    """Put a saved snapshot back, and report what could not be put back.

    The way out of a run that died halfway. Idempotent by construction: it
    reads each register before writing it, so running it when nothing is
    actually wrong costs one read per control and changes nothing.
    """
    saved = Snapshot.from_dict(json.loads(Path(args.restore).read_text()))
    run = ControlTest(inverter, options=Options(dry_run=args.dry_run))
    if saved.stopped_at is not None:
        print(
            "This snapshot was taken with the inverter stopped. Starting it "
            "before anything else.",
            file=sys.stderr,
        )
        await run.async_ensure_running()
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
    print(
        f"\nPut {len(results)} register(s) back, and read each one to check it took.",
        file=sys.stderr,
    )
    return RESTORED


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
    run = ControlTest(inverter)
    started = await run.async_ensure_running()
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

        restart = _ask_restart(args.restart)

        async def keep(snapshot: Snapshot) -> None:
            snapshot_path.write_text(json.dumps(snapshot.to_dict(), indent=2))

        options = Options(
            allow_dark=args.allow_dark,
            enable_export_limit=args.enable_export_limit,
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
        run = ControlTest(
            inverter,
            options=options,
            on_progress=lambda fraction, label: print(
                f"  [{fraction:>4.0%}] {label}", file=sys.stderr
            ),
            on_snapshot=keep,
        )
        outcome = await run.async_run()
    finally:
        await connection.close()

    title = f"Control test -- {inverter.model or 'unknown model'}"
    private = report(outcome, title=f"{title} ({serial or 'no serial'})")
    public = report(
        outcome, title=f"{title} ({stand_in(serial) if serial else 'anon'})"
    )
    block = document(outcome)

    paths = [
        _save(directory, stamp, "private.md", private),
        _save(directory, stamp, "public.md", public),
        _save(directory, stamp, "control_test.json", json.dumps(block, indent=2)),
    ]
    if args.merge_into:
        paths.append(_merge(Path(args.merge_into), block, serial, args.host))

    print(f"\n{summarise(outcome)}", file=sys.stderr)
    for sentence in outcome.unestablished:
        print(f"  not established: {sentence}", file=sys.stderr)
    print("\nWrote:", file=sys.stderr)
    for path in paths:
        role = "keep this -- real serial" if "private" in path.name else "send this"
        print(f"  {path}  ({role})", file=sys.stderr)
    if snapshot_path.exists():
        print(
            f"  {snapshot_path}  (the before-state; --restore takes it)",
            file=sys.stderr,
        )
    if outcome.not_restored:
        print(
            "\nSomething was not put back. Run:\n"
            f"  python {Path(__file__).name} {args.host} --restore {snapshot_path}",
            file=sys.stderr,
        )
    return outcome.code


def _merge(target: Path, block: dict[str, Any], serial: str | None, host: str) -> Path:
    """Fold the block into an existing fingerprint document, and refuse to leak.

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
    document_data["control_test"] = block
    target.write_text(json.dumps(document_data, indent=2) + "\n")
    return target


def main() -> int:
    """Parse arguments and run."""
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
        "--simulated",
        action="store_true",
        help="stamp the report as evidence about nothing; for a simulator",
    )
    parser.add_argument(
        "--restore", help="put a saved snapshot back, and do nothing else"
    )
    parser.add_argument(
        "--merge-into", help="fold the result into an existing fingerprint document"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        code = asyncio.run(_run(args))
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
        # CLAUDE.md names as the progressive signature of session exhaustion.
        print(f"\n{err}", file=sys.stderr)
        print(
            "\nA Sungrow grants few Modbus sessions and wants about 90 seconds "
            "of quiet to reclaim them. If something else is polling this "
            "inverter -- a Home Assistant, another survey -- stop it and try "
            "again; reads that die a little further into the poll each time "
            "are contention, not a broken register.",
            file=sys.stderr,
        )
        print(f"\nexit {COULD_NOT_RUN}: {CODES[COULD_NOT_RUN]}", file=sys.stderr)
        return COULD_NOT_RUN
    except KeyboardInterrupt:
        print(
            "\nInterrupted. Everything this run wrote has been put back; if the "
            "last line below says otherwise, use --restore.",
            file=sys.stderr,
        )
        return 5
    if code == RESTORED:
        # A restore is not a run, so it does not get a run's verdict. Saying
        # "every planned check ran" after putting things back would be a
        # sentence about something that did not happen.
        print("\nexit 0: everything in the snapshot is back", file=sys.stderr)
        return 0
    print(f"\nexit {code}: {CODES[code]}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
