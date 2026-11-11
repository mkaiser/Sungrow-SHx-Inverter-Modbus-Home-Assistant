#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "sungrow-modbus==0.1.0a37",
#     "modbus-connection[tmodbus]==4.12.4",
# ]
# ///
"""Measure a Sungrow wallbox's output current scale, and put everything back.

**It writes to your wallbox.** The wallbox is read only everywhere else in this
project, because three sources disagree on the output current setting (holding
21203: 0.1 A per count here, 0.01 A in discussion #571), which is a factor of
ten on a mains charger. This settles it by the same method the inverter's
capability test uses, and writes nothing until you say so.

Start without `--leave`. That is a dry run: it identifies the wallbox, reads
the rating, the setting and what the car draws, says which scale they fit, and
prints what it would write. With a car charging, "the car draws 13 A while the
setting is 160" already rules out 0.01 A per count, before any write.

With `--leave` it offers 6, 8 and 10 A (60, 80 and 100 counts). Those are safe
at either scale: at the wrong one they offer a tenth. `--max-amps` lowers the
top. It never goes above what you give it, so give it your installation's limit
if that is below 10 A.

    python python/sungrow_wallbox_capability_test.py 192.168.1.60
    python python/sungrow_wallbox_capability_test.py 192.168.1.60 --leave
    python python/sungrow_wallbox_capability_test.py 192.168.1.60 --leave --enable
    python python/sungrow_wallbox_capability_test.py 192.168.1.60 --restore SNAPSHOT

With a car charging, `--follow` steps the offer from 6 A to your `--max-amps` and
back and times how the car follows; `--below-minimum`, `--above-rating` and
`--fallback` need `--max-amps` given on purpose (the last also needs it no
higher than the setting the wallbox had); `--phase-charging` switches the phase
with the charge stopped first; `--mileage` writes the mileage setting its own
word. `--merge-into DIAGNOSIS.json` keeps the run in a diagnosis document under
`wallbox_capability_test`. These need a `sungrow-modbus` newer than the one
pinned above.

**At the wallbox's own address only**: Modbus inside TLS on port 516, unit 248.
Through a WiNet-S the wallbox reads back stale and the readback is not
evidence, so this does not run there.

Before you start:

* **Stop whatever else talks to the wallbox** (Home Assistant, evcc, an
  iHomeManager). It accepts few sessions, refuses connections opened in quick
  succession, and drops a session after sixty seconds of silence.
* **For the behavioural leg, a car must be plugged in and charging.** Without
  one only the raw word is checked, and the run says the scale is not settled.
* **`--enable` disables the charge point and enables it again**: a charge in
  progress stops and resumes. **`--phase` switches the phase setting and
  back**, and only when nothing is flowing. **`--start-stop`** stops and starts
  the charge once, and only if the register reads 0 while a car charges.

The snapshot of what the settings held is written and flushed to the disk
before the first write. If the run dies, `--restore SNAPSHOT` puts it back.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

from modbus_connection import ModbusError
from modbus_connection.tmodbus import ModbusConnection

try:
    from sungrow_modbus.wallbox import capability_test as wct
except ImportError:  # pragma: no cover -- the pinned wheel predates the module
    print(
        "This needs a sungrow-modbus that has wallbox.capability_test; the pinned "
        "one does not. It ships in the release after 0.1.0a27.",
        file=sys.stderr,
    )
    raise SystemExit(2) from None

import wallbox_direct

#: The options only a library newer than the pinned one has.
NEW_FLAGS = (
    "follow",
    "below_minimum",
    "above_rating",
    "phase_charging",
    "fallback",
    "mileage",
)

#: Left in the way a person at a terminal is asked a last time.
CANCELLED = -2

#: A wallbox refuses connections opened within seconds of each other, and is
#: fine again after about ten.
RECONNECT_QUIET = 10.0


def _stamp() -> str:
    """Return a sortable timestamp for this run's filenames."""
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def _workspace() -> Path:
    """Return the directory the run's files belong in: `device-diagnosis/`.

    Anchored on the script, as the inverter's capability test is. Nothing written
    there carries a serial or an address: the report names the model only, and
    the snapshot holds register values. `.gitignore` covers both by name.
    """
    return Path(__file__).resolve().parents[2]


def _save(path: Path, text: str) -> Path:
    """Write a file and flush it to the disk before returning."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    return path


class TlsPort:
    """A wallbox at its own address, as the procedure's `WallboxPort`.

    One session is kept open and reused, because the port refuses quick
    reconnects. A *fresh* read is the one thing that does not reuse it: the
    session is closed, the link is left quiet for ten seconds, and a new one is
    opened, which then serves the reads after it. That is what gives the raw
    readback its independence from the write.
    """

    fresh = True

    def __init__(self, host: str, timeout: float) -> None:
        """Remember where to connect; nothing is opened yet."""
        self.host = host
        self.timeout = timeout
        self._connection: ModbusConnection | None = None

    def _unit(self) -> Any:
        if self._connection is None:
            self._connection = ModbusConnection(
                wallbox_direct.params(self.host), timeout=self.timeout
            )
        return self._connection.for_unit(wallbox_direct.UNIT)

    async def close(self) -> None:
        """Close the session, if one is open."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read on the open session."""
        unit = self._unit()
        if space == "holding":
            return list(await unit.read_holding_registers(address, count))
        return list(await unit.read_input_registers(address, count))

    async def read_fresh(self, space: str, address: int, count: int) -> list[int]:
        """Read on a new session, after ten quiet seconds."""
        await self.close()
        await asyncio.sleep(RECONNECT_QUIET)
        return await self.read(space, address, count)

    async def write(self, address: int, word: int) -> None:
        """Write one holding word."""
        await self._unit().write_register(address, word)


# -- asking and reporting -----------------------------------------------------

QUESTION = """
This writes to your wallbox's settings: the output current (60, 80 and 100
counts, which is 6, 8 and 10 A at the reading this project holds and a tenth of
that at the other), and whatever of --enable, --phase and --start-stop you gave.
Each is put back afterwards and read back on a fresh session. A charge in
progress may be interrupted.
"""


def _ready(args: argparse.Namespace) -> bool:
    """Ask a last time, defaulting to no. A run with nobody at a terminal is a no."""
    if args.yes:
        return True
    if not sys.stdin.isatty():
        print("No terminal and no --yes: not writing.", file=sys.stderr)
        return False
    print(QUESTION, file=sys.stderr)
    answer = input("  Do you permit the test to write to the wallbox? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def report(outcome: wct.Outcome, *, leave: bool) -> str:
    """Return the run as text: what was found first, what is not restored first."""
    lines: list[str] = []
    for row in outcome.not_restored:
        lines.append(
            f"NOT RESTORED: holding {row.address + 1} should hold {row.original} "
            f"({row.detail}). Run --restore with the snapshot."
        )
    meaning = wct.CODES[outcome.code]
    if not leave and outcome.code == 0:
        meaning = wct.DRY_RUN_MEANS
    lines.append(f"exit {outcome.code}: {meaning}")
    c = outcome.conditions
    if c.get("model"):
        lines.append(
            f"model {c['model']}, rated {c.get('rated_a')} A, setting word "
            f"{c.get('setting_word')}, status {c.get('status')}, "
            f"the car draws {c.get('draw_a')} A"
        )
    if c.get("scale_before_writing"):
        lines.append(f"scale, before writing: {c['scale_before_writing']}")
    if c.get("guard"):
        lines.append(f"stopped: {c['guard']}")
    for step in outcome.steps:
        lines.append(f"  {step.name}: {step.verdict} -- {step.detail}")
    for row in outcome.restores:
        state = "put back" if row.restored else "NOT put back"
        lines.append(
            f"  restore holding {row.address + 1}: {state} "
            f"({row.original}, {row.attempts} attempt(s))"
        )
    for sentence in outcome.unestablished:
        lines.append(f"  not established: {sentence}")
    return "\n".join(lines)


def document(outcome: wct.Outcome, args: argparse.Namespace) -> dict[str, Any]:
    """Return the run as a JSON document. No serial and no address."""
    return {
        "document": "wallbox_capability_test",
        "script": "sungrow_wallbox_capability_test.py",
        "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "leave": args.leave,
        "transport": "tls",
        "fresh_session": True,
        "options": {
            "max_amps": args.max_amps,
            "cap_explicit": args.cap_explicit,
            "enable": args.enable,
            "phase": args.phase,
            "start_stop": args.start_stop,
            **{name: getattr(args, name, False) for name in NEW_FLAGS},
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


# -- the modes -------------------------------------------------------------------


async def _restore_mode(port: wct.WallboxPort, path: Path) -> int:
    """Put a saved snapshot back, and say what could not be put back."""
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = {int(address): int(word) for address, word in data["raw"].items()}
    touched = [int(address) for address in data.get("touched") or raw]
    runner = wct.WallboxCapabilityTest(port, wct.Options())
    runner.snapshot = {"raw": raw, "touched": touched}
    await runner.async_restore()
    bad = [row for row in runner.restores if not row.restored]
    for row in runner.restores:
        print(
            f"  holding {row.address + 1}: "
            f"{'put back' if row.restored else 'NOT put back'} ({row.original})",
            file=sys.stderr,
        )
    return 5 if bad else 0


async def _run(
    args: argparse.Namespace,
    port: wct.WallboxPort | None = None,
    clock: Any = None,
) -> int:
    """Do the whole thing, and return the exit code."""
    port = port or TlsPort(args.host, args.timeout)
    directory = _workspace()
    stamp = _stamp()
    snapshot_path = directory / f"{stamp}-wallbox-snapshot.json"
    try:
        if args.restore:
            return await _restore_mode(port, Path(args.restore))
        if args.leave and not _ready(args):
            print("Cancelled. Nothing was written to the wallbox.", file=sys.stderr)
            return CANCELLED

        async def keep(snapshot: dict[str, Any]) -> None:
            _save(snapshot_path, json.dumps(snapshot, indent=2))

        extra = {name: True for name in NEW_FLAGS if getattr(args, name, False)}
        if args.cap_explicit:
            extra["cap_explicit"] = True
        if extra and "follow" not in wct.Options.__dataclass_fields__:
            print(
                "These options need a sungrow-modbus newer than the pinned one.",
                file=sys.stderr,
            )
            return 2
        options = wct.Options(
            leave=args.leave,
            max_amps=args.max_amps,
            start_stop=args.start_stop,
            enable=args.enable,
            phase=args.phase,
            **extra,
        )
        runner = wct.WallboxCapabilityTest(
            port,
            options,
            clock=clock,
            on_snapshot=keep if args.leave else None,
            on_step=lambda label: print(f"  {label}", file=sys.stderr),
        )
        outcome = await runner.async_run()
    except (ModbusError, TimeoutError, OSError):
        logging.getLogger(__name__).exception("lost the wallbox")
        print("Lost the wallbox before the run started.", file=sys.stderr)
        return 1
    finally:
        close = getattr(port, "close", None)
        if close is not None:
            await close()

    print(report(outcome, leave=args.leave), file=sys.stderr)
    merged = None
    if args.merge_into and outcome.conditions.get("model") and args.leave:
        merged = _merge(Path(args.merge_into), document(outcome, args), args.host)
        print(f"\n  merged into {merged}", file=sys.stderr)
    if outcome.conditions.get("model"):
        out = _save(
            directory / f"{stamp}-wallbox-capability-test.json",
            json.dumps(document(outcome, args), indent=2),
        )
        print(f"\n  {out}", file=sys.stderr)
    if outcome.not_restored or outcome.code == 5:
        print(
            f"\n  The before-state: {snapshot_path}\n  --restore takes it.",
            file=sys.stderr,
        )
    elif args.leave:
        snapshot_path.unlink(missing_ok=True)
    return outcome.code


def _merge(target: Path, block: dict[str, Any], host: str) -> Path:
    """Keep the run in a diagnosis document, folded with the runs already there.

    Refuses to write if the block holds the address: a refusal costs a minute,
    and an address in a public document is out for good.
    """
    from sungrow_modbus.wallbox import ledger  # newer than the pinned wheel

    if host in json.dumps(block):
        raise SystemExit(
            f"refusing to merge: the block contains the address ({target})"
        )
    data = json.loads(target.read_text(encoding="utf-8"))
    kept = list(data.get("wallbox_capability_test", {}).get("run_blocks") or [])
    kept = [run for run in kept if ledger.fold_key(run) == ledger.fold_key(block)]
    kept.append(block)
    folded = ledger.fold(kept)
    options = {
        option: bool(block["options"].get(option))
        for _need, option in ledger.CHECKS.values()
        if option
    }
    data["wallbox_capability_test"] = {
        **ledger.document(folded, options),
        "run_blocks": kept,
    }
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return target


class _CapChosen(argparse.Action):
    """Record that `--max-amps` was given, so the default is never taken for consent."""

    def __call__(self, parser, namespace, values, option_string=None):  # type: ignore[no-untyped-def]
        """Store the cap and that it was chosen."""
        setattr(namespace, self.dest, values)
        namespace.cap_explicit = True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure a wallbox's output current scale, with leave."
    )
    parser.add_argument("host", nargs="?", help="the wallbox's own address")
    parser.add_argument(
        "--leave", action="store_true", help="write (default: a dry run)"
    )
    parser.add_argument("--yes", action="store_true", help="answer the last question")
    parser.add_argument(
        "--max-amps",
        type=float,
        action=_CapChosen,
        default=wct.DEFAULT_MAX_AMPS,
        help="the highest current to offer (default %(default)s)",
    )
    parser.add_argument("--start-stop", action="store_true", help="also stop and start")
    parser.add_argument("--enable", action="store_true", help="also disable and enable")
    parser.add_argument("--phase", action="store_true", help="also switch the phase")
    parser.add_argument("--follow", action="store_true", help="step 6 A to the cap")
    parser.add_argument(
        "--below-minimum", action="store_true", help="offer 5 A, then 0"
    )
    parser.add_argument(
        "--above-rating", action="store_true", help="offer the rating plus 1 A"
    )
    parser.add_argument(
        "--phase-charging", action="store_true", help="switch phase while charging"
    )
    parser.add_argument("--fallback", action="store_true", help="fall silent for 75 s")
    parser.add_argument(
        "--mileage", action="store_true", help="write the mileage its own word"
    )
    parser.add_argument(
        "--merge-into", help="keep the run in this diagnosis document (needs --leave)"
    )
    parser.set_defaults(cap_explicit=False)
    parser.add_argument(
        "--restore", help="put a saved snapshot back, and do nothing else"
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run."""
    args = _parser().parse_args(argv)
    if not args.host:
        _parser().error("the wallbox's address is required")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
