#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "sungrow-modbus==0.1.0a38",
#     "modbus-connection[tmodbus]==4.12.7",
# ]
# ///
"""Test a wallbox that a hybrid inverter manages, by writing the inverter.

**It writes to your inverter.** A Sungrow wallbox on a hybrid inverter's bus
(set up as the inverter's EV charger in iSolarCloud) is driven by the
inverter: writes to the wallbox's own registers are overwritten within
seconds. Its charge is controlled at the inverter, unit 1: charging on/off,
the charging mode, and the user-defined current. This writes those, watches
what the car does, and puts everything back. The wallbox is only read.

Start without `--leave`. That is a dry run: it reads the inverter's EV charger
block and the wallbox, and says what it would do. With `--leave` and a car
charging it switches to user-defined mode, offers 6, 8 and 10 A (never above
`--max-amps` or the wallbox's rating) and watches the car follow each, then
offers 5 A and expects the inverter to refuse it. `--start-stop` also stops the
charge for fifteen seconds and starts it again.

    python python/sungrow_managed_wallbox_test.py INVERTER --wallbox WALLBOX
    python python/sungrow_managed_wallbox_test.py INVERTER --wallbox WALLBOX --leave
    python python/sungrow_managed_wallbox_test.py INVERTER --restore SNAPSHOT

`INVERTER` is the inverter's own LAN port or its WiNet-S (port 502, unit 1).
`--wallbox` is the wallbox's own address (TLS, port 516, unit 248); without it
the wallbox is read through `INVERTER` at `--wallbox-unit` (3 behind a WiNet-S).

Before you start:

* **Stop whatever else talks to the inverter** on that path (Home Assistant,
  evcc, your own polling): it accepts few sessions.
* **A car must be plugged in and charging.** Without one nothing is written.
* **The restore puts the house back**: the user current first (it can only be
  written in user-defined mode), then the mode, then charging on. Leaving
  user-defined mode ends a charging session, and charging on starts it again.
  If the car does not charge again within a minute, the run says so (exit 5):
  set the mode in iSolarCloud, press Start, and replug the car.

The snapshot of what the inverter held is flushed to the disk before the first
write. If the run dies, `--restore SNAPSHOT` puts it back.
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

from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

try:
    from sungrow_modbus.wallbox import managed_test as mt
except ImportError:  # pragma: no cover -- the pinned wheel predates the module
    print(
        "This needs a sungrow-modbus that has wallbox.managed_test; the pinned "
        "one does not. It ships in the release after 0.1.0a38; until then run it "
        "on this repository's library (doc/development.md, make scan-local).",
        file=sys.stderr,
    )
    raise SystemExit(2) from None

import wallbox_direct

#: Left in the way a person at a terminal is asked a last time.
CANCELLED = -2

QUESTION = """
This writes to your inverter's EV charger settings: the charging mode (to user
defined), the user-defined current (6, 8 and 10 A, and 5 A, which the inverter
should refuse), and with --start-stop charging off and on. Each is put back
afterwards, and the charge with it. The car's charging current changes for a
few minutes.
"""


def _stamp() -> str:
    """Return a sortable timestamp for this run's filenames."""
    return datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")


def _workspace() -> Path:
    """Return `device-diagnosis/`, where the run's files belong (gitignored by name)."""
    return Path(__file__).resolve().parents[2]


def _save(path: Path, text: str) -> Path:
    """Write a file and flush it to the disk before returning."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    return path


class InverterPort:
    """The inverter at unit 1, one session kept open."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        """Remember where to connect; nothing is opened yet."""
        self.connection = ModbusConnection(
            ModbusTcpParams(host=host, port=port), timeout=timeout
        )
        self.unit = self.connection.for_unit(1)

    async def read(self, address: int, count: int) -> list[int]:
        """Read holding words."""
        return list(await self.unit.read_holding_registers(address, count))

    async def write(self, address: int, word: int) -> None:
        """Write one holding word."""
        await self.unit.write_register(address, word)


class WallboxReader:
    """The wallbox, read only: its own TLS address, or through the inverter's path."""

    def __init__(self, connection: ModbusConnection, unit: int) -> None:
        """Read through `connection` at `unit`."""
        self.connection = connection
        self.unit = connection.for_unit(unit)

    async def read(self, space: str, address: int, count: int) -> list[int]:
        """Read words."""
        if space == "holding":
            return list(await self.unit.read_holding_registers(address, count))
        return list(await self.unit.read_input_registers(address, count))


def _ready(args: argparse.Namespace) -> bool:
    """Ask a last time, defaulting to no. A run with nobody at a terminal is a no."""
    if args.yes:
        return True
    if not sys.stdin.isatty():
        print("No terminal and no --yes: not writing.", file=sys.stderr)
        return False
    print(QUESTION, file=sys.stderr)
    answer = input("  Do you permit the test to write to the inverter? [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def report(outcome: mt.Outcome, *, leave: bool) -> str:
    """Return the run as text: what is not restored first."""
    lines: list[str] = []
    c = outcome.conditions
    if not outcome.restored:
        lines.append(f"NOT PUT BACK: {c.get('on_site', mt.ON_SITE)}")
    meaning = mt.CODES[outcome.code]
    if not leave and outcome.code == 0:
        meaning = mt.DRY_RUN_MEANS
    lines.append(f"exit {outcome.code}: {meaning}")
    if c.get("model"):
        lines.append(
            f"{c['model']}, rated {c.get('rated_a')} A; the inverter: mode "
            f"{c.get('mode')}, user current {c.get('user_current_a')} A, charging "
            f"word {c.get('charging_word')}; status {c.get('status')}, the car "
            f"draws {c.get('draw_a')} A"
        )
    if c.get("guard"):
        lines.append(f"  {c['guard']}")
    for step in outcome.steps:
        lines.append(f"  {step.name}: {step.verdict} -- {step.detail}")
    return "\n".join(lines)


def document(outcome: mt.Outcome, args: argparse.Namespace) -> dict[str, Any]:
    """Return the run as JSON-able data, with no address."""
    return {
        "document": "managed_wallbox_capability_test",
        "script": Path(__file__).name,
        "read_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "leave": args.leave,
        "wallbox_path": "tls" if args.wallbox else f"unit {args.wallbox_unit}",
        "options": {
            "max_amps": args.max_amps,
            "start_stop": args.start_stop,
            "floor": not args.no_floor,
        },
        "code": outcome.code,
        "restored": outcome.restored,
        "conditions": outcome.conditions,
        "steps": [step._asdict() for step in outcome.steps],
    }


async def _run(
    args: argparse.Namespace,
    inverter: mt.InverterPort | None = None,
    wallbox: mt.WallboxReader | None = None,
    clock: Any = None,
) -> int:
    """Do the whole thing, and return the exit code."""
    closers: list[Any] = []
    if inverter is None:
        port = InverterPort(args.host, args.port, args.timeout)
        closers.append(port.connection)
        inverter = port
    if wallbox is None:
        if args.wallbox:
            connection = ModbusConnection(
                wallbox_direct.params(args.wallbox), timeout=args.timeout
            )
            closers.append(connection)
            wallbox = WallboxReader(connection, wallbox_direct.UNIT)
        else:
            assert isinstance(inverter, InverterPort)
            wallbox = WallboxReader(inverter.connection, args.wallbox_unit)
    directory = _workspace()
    snapshot_path = directory / f"{_stamp()}-managed-wallbox-snapshot.json"
    try:
        if args.restore:
            return await _restore_mode(inverter, wallbox, Path(args.restore), clock)
        if args.leave and not _ready(args):
            print("Cancelled. Nothing was written.", file=sys.stderr)
            return CANCELLED

        async def keep(snapshot: dict[str, Any]) -> None:
            _save(snapshot_path, json.dumps(snapshot, indent=2))

        runner = mt.ManagedWallboxTest(
            inverter,
            wallbox,
            mt.Options(
                leave=args.leave,
                max_amps=args.max_amps,
                floor=not args.no_floor,
                start_stop=args.start_stop,
            ),
            clock=clock,
            on_snapshot=keep if args.leave else None,
            on_step=lambda label: print(f"  {label}", file=sys.stderr),
        )
        outcome = await runner.async_run()
    except (ModbusError, TimeoutError, OSError):
        logging.getLogger(__name__).exception("lost a device")
        print("Lost a device before the run started.", file=sys.stderr)
        return 1
    finally:
        for closer in closers:
            await closer.close()
    print(report(outcome, leave=args.leave), file=sys.stderr)
    path = _save(
        directory / f"{_stamp()}-managed-wallbox-capability-test.json",
        json.dumps(document(outcome, args), indent=2, default=str),
    )
    print(f"\n  {path}", file=sys.stderr)
    if outcome.restored and snapshot_path.exists():
        snapshot_path.unlink()
    return outcome.code


async def _restore_mode(
    inverter: mt.InverterPort, wallbox: mt.WallboxReader, path: Path, clock: Any
) -> int:
    """Put a saved snapshot back, the charge included."""
    data = json.loads(path.read_text(encoding="utf-8"))
    runner = mt.ManagedWallboxTest(inverter, wallbox, mt.Options(), clock=clock)
    runner.snapshot = data
    await runner.async_restore()
    print(
        f"  the inverter's block: {runner.conditions.get('restored_block')}",
        file=sys.stderr,
    )
    if not runner.restored:
        print(f"NOT PUT BACK: {mt.ON_SITE}", file=sys.stderr)
        return 5
    print("Put back.", file=sys.stderr)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test a wallbox an inverter manages, by writing the inverter."
    )
    parser.add_argument("host", nargs="?", help="the inverter or its WiNet-S")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument(
        "--wallbox", help="the wallbox's own address (TLS 516); read only"
    )
    parser.add_argument(
        "--wallbox-unit",
        type=int,
        default=3,
        help="without --wallbox: its unit behind the WiNet-S (default 3)",
    )
    parser.add_argument("--leave", action="store_true", help="write (default: dry run)")
    parser.add_argument("--yes", action="store_true", help="answer the last question")
    parser.add_argument(
        "--max-amps", type=float, default=mt.DEFAULT_MAX_AMPS, help="highest offer"
    )
    parser.add_argument(
        "--start-stop", action="store_true", help="also stop and start the charge"
    )
    parser.add_argument(
        "--no-floor", action="store_true", help="do not offer 5 A for a refusal"
    )
    parser.add_argument("--restore", help="put a saved snapshot back, nothing else")
    parser.add_argument("--timeout", type=float, default=8.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and run."""
    args = _parser().parse_args(argv)
    if not args.host:
        _parser().error("the inverter's address is required")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
