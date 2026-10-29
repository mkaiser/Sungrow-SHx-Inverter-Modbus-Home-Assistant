#!/usr/bin/env python3
"""The block read test: find the register that takes a whole block down.

The library pools neighbouring registers into single block reads, which is
what makes a full poll a few dozen requests instead of one per field. The
cost is that one register a device cannot answer takes its whole block with
it -- and a `Component` either updates or raises, so a bad block loses every
field in it, often most of a tier. Two cases show the shapes:

* the two firmware strings at 2612 and 2628 come back on a cable in a frame
  the device **pads to fifteen registers while declaring the correct byte
  count**, which `modbus-connection` rightly rejects -- and a pooled block
  holding one loses every unrelated field beside it;
* the same two registers **refuse with exception 0x02, three attempts out of
  three, through a WiNet-S**, while every other block answers in the same
  session, and read on a direct-LAN connection to the same inverter. So the
  tool's own output has to be read against the transport: this is a dongle
  not forwarding a measuring point, and no amount of isolating registers in
  `src/sungrow_modbus/inverter/layout.py` will fix it.

Those two are why the tool reports *how* a block failed rather than just
that it did: the first has a fix in `layout.COUNTS`, the second in
`layout.ISOLATE`, and a link that merely drops has no fix here at all.

`src/sungrow_modbus/inverter/layout.py` is where the fix goes, and it takes two things
this tool produces: the register to isolate, and the length that actually
reads. Guessing either from a document is how the wrong fix gets committed,
which is why that module says to add to it only from a measurement.

    cd device-survey/scripts/python
    python blocks.py 192.168.1.10                     # every component
    python blocks.py 192.168.1.10 -c fast_input       # one of them
    python blocks.py 192.168.1.10 -r input:5010:25    # a range

It reads and never writes. Nothing here can change a setting.

The measurement is the library's, `sungrow_modbus.block_test`, which the
integration's device page runs too: the plan is recorded from the poll, so
this tests exactly what the integration asks for. `--client` picks the
reader -- `modbus-connection`, which fails where the integration fails, or
`sungrow_modbus.raw_client`, the strict raw socket that names the count a
padded frame needs. This file is the terminal around it: arguments, the
lines printed as it goes, and `report`.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
import sys
from typing import NamedTuple

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
import probe

from sungrow_modbus import block_test, raw_client
from sungrow_modbus.addresses import device_components
from sungrow_modbus.block_test import (
    DROPPED,  # noqa: F401
    INCONSISTENT,  # noqa: F401
    NARROW_BUDGET,
    OK,
    PADDED,
    REFUSED,  # noqa: F401
    REJECTED,
    TIMED_OUT,  # noqa: F401
    UNNARROWED,
    WRONG_LENGTH,
    Block,
    Outcome,
    component_blocks,
    declared,
    inverter_blocks,
)
from sungrow_modbus.survey import word_reader

#: What the document says measured, when `modbus-connection` did.
LIBRARY_LABEL = "modbus-connection -- rejects a frame exactly as the integration does"


class Client(NamedTuple):
    """One way of making the reads: which, how, its reconnect count, and closing."""

    label: str
    read: block_test.Read
    reconnects: Callable[[], int] | None
    close: Callable[[], Awaitable[None]]


def client_for(
    host: str,
    port: int,
    unit: int,
    timeout: float,
    delay: float,
    prefer: str = "library",
) -> Client:
    """Return the Modbus client to measure with.

    The library client is the default, because whatever it cannot read the
    integration cannot read either -- there is no second frame validator to
    keep in step. It reconnects on nothing, which is also the integration's
    behaviour. The raw client is the other half of the tool: it is the one
    that turns a rejected frame into the count that would have worked.
    """
    if prefer == "raw":
        raw = raw_client.RawClient(host, port, unit, timeout, delay)
        return Client(raw.label, raw.read, lambda: raw.reconnects, raw.close)

    connection = ModbusConnection(
        ModbusTcpParams(host=host, port=port), timeout=timeout
    )
    words = word_reader(connection.for_unit(unit))

    async def read(space: str, address: int, count: int) -> list[int]:
        found = await words(space, address, count)
        if delay:
            await asyncio.sleep(delay)
        return found

    return Client(LIBRARY_LABEL, read, None, connection.close)


def _components() -> dict[str, type]:
    """Every component the library maps, on any device, by name."""
    return {
        name: klass
        for components in device_components().values()
        for name, klass in components.items()
    }


def _blocks_of(component: str | None) -> list[Block]:
    """Return the reads to test.

    **Only the inverter's own components**, unless one is named explicitly.
    The SBR pack at 200 or 2 and the wallbox at 3 or 248 live on other unit
    ids, and reading their addresses at the inverter's unit tests nothing:
    input 10740 and 21215 answer 0xFFFF or refuse there whatever the pack and
    the charge point are doing. Recording them into every survey would add
    guaranteed failures, each narrowed at the cost of the budget and offered
    to `src/sungrow_modbus/inverter/layout.py` as a register fault. Naming a
    component still selects it, so `-c sbr_battery_cells` works against a
    pack when that is what somebody is testing.
    """
    if component is None:
        return probe.run(inverter_blocks())
    known = _components()
    if component not in known:
        raise SystemExit(f"No such component: {component}.\nKnown: {', '.join(known)}")
    return probe.run(component_blocks(component, known[component]))


async def measure(
    client: Client,
    blocks: list[Block],
    attempts: int = 3,
    rounds: int = 1,
    echo: Callable[[str], None] = print,
    narrow_budget: float = NARROW_BUDGET,
) -> Outcome:
    """Run `block_test.measure`, printing each read as it happens.

    `echo` rather than `print`, so a caller can put this inside a transcript;
    the wording is unchanged, because `layout.py` quotes it and a
    measurement's phrasing is part of the measurement.
    """
    shown = {"round": 0}

    def result(block: Block, round_number: int, kind: str, detail: str) -> None:
        if rounds > 1 and round_number != shown["round"]:
            if shown["round"]:
                echo("")
            echo(f"round {round_number}:")
            shown["round"] = round_number
        flag = "     " if kind == OK else "  >> "
        echo(
            f"{flag}{block.component:<34} {block.space} {block.address} "
            f"x{block.count:<4} {kind} ({detail})"
        )

    def narrowing(block: Block, index: int, total: int, seconds: float) -> None:
        if index == 1:
            if rounds > 1:
                echo("")
            echo(
                f"\nNarrowing {total} failing block(s)"
                + (f", {seconds:.0f}s each.\n" if seconds else ".\n")
            )
        else:
            echo("")
        echo(f"  {block.component} ({block.space} {block.address} x{block.count})")

    def narrowed(block: Block, depth: int, kind: str, detail: str) -> None:
        indent = "   " + "  " * depth
        echo(
            f"{indent}{block.space} {block.address} x{block.count:<4} {kind} ({detail})"
        )

    outcome = await block_test.measure(
        client.read,
        blocks,
        attempts=attempts,
        rounds=rounds,
        narrow_budget=narrow_budget,
        reconnects=client.reconnects,
        on_result=result,
        on_narrowing=narrowing,
        on_narrow=narrowed,
    )
    if outcome.failing or rounds > 1:
        echo("")
    return outcome


def report(outcome: Outcome, echo: Callable[[str], None] = print) -> None:
    """Say what the measurement means, and what to do about it."""
    if outcome.intermittent:
        echo("\nIntermittent, so contention rather than a fault:")
        for block in outcome.intermittent:
            summary = ", ".join(
                f"{kind} x{n}" for kind, n in sorted(outcome.tally[block].items())
            )
            echo(
                f"  {block.component:<34} {block.space} {block.address} "
                f"x{block.count:<4} {summary}"
            )
        echo("  Re-run when nothing else is polling the inverter.")

    if not outcome.failing:
        echo("\nEvery block answered at least once: nothing here is a")
        echo("register fault.")
        return

    echo("=" * 72)
    if outcome.reconnects:
        echo(f"The device hung up {outcome.reconnects} time(s) and was reconnected.\n")
    if not outcome.culprits:
        echo("The blocks failed but no sub-range did, which usually means")
        echo("contention rather than a bad register. Re-run when nothing else")
        echo("is polling the inverter.")
        return

    echo("Smallest ranges that still fail:\n")
    for block, kind, detail in outcome.culprits:
        address, count = block.address, block.count
        registers = (
            f"register {address + 1}"
            if count == 1
            else f"registers {address + 1}-{address + count}"
        )
        echo(
            f"  {block.space} {address} x{count}  ({registers}), "
            f"inside {block.component}"
        )
        echo(f"     {kind} -- {detail}")
        if kind == REJECTED:
            echo("     -> re-run with --client raw for the count that would read")
        # Only worth listing the fields where the range is small enough to
        # act on. An un-narrowed 15-register block would print fifteen names
        # and imply all fifteen are suspect.
        if kind != UNNARROWED:
            for offset in range(count):
                named = declared(block.space, address + offset)
                echo(f"     {address + offset + 1}: {named}")
        if kind in {WRONG_LENGTH, PADDED}:
            echo("     -> the count named above belongs in layout.COUNTS")
        echo("")

    stopped = [row for row in outcome.culprits if row[1] == UNNARROWED]
    if stopped:
        echo(
            f"{len(stopped)} range(s) above stopped at the narrowing budget rather "
            "than at\na register. On this link a refusal arrives as a timeout, so "
            "each read\ncosts the timeout times --attempts; the block above is as "
            "small as the\nbudget reached, not as small as it goes. To finish one, "
            "aim at it:\n"
        )
        for block, _kind, _detail in stopped:
            echo(
                f"  python device-survey/scripts/python/blocks.py <host> "
                f"-r {block.space}:{block.address}:{block.count}    # {block.component}"
            )
        echo("\nA lower --timeout, or --attempts 1, buys depth on a link like this.")
        echo("")

    if len(stopped) < len(outcome.culprits):
        echo(
            "Put the fields these belong to in "
            "src/sungrow_modbus/inverter/layout.py, and quote this"
        )
        echo("output in the comment: that module is only ever added to from a")
        echo("measurement, and this is the measurement.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("host")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="pause between reads; raise it if a WiNet-S drops the connection",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="how many times to go round the whole plan (default 1). This is "
        "a different measurement from --attempts: contention correlates in "
        "time, so three back-to-back reads of one block can all land in the "
        "same busy moment, where three rounds with the other blocks in "
        "between cannot. A register fault fails in every round",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="how many times to repeat each read (default 3). A real register "
        "fault fails every attempt; contention does not.",
    )
    parser.add_argument(
        "--narrow-budget",
        type=float,
        default=NARROW_BUDGET,
        help=f"seconds for the whole narrowing phase (default {NARROW_BUDGET:.0f}), "
        "split evenly across the blocks that failed. Narrowing walks a binary tree "
        "over each block, so a link whose refusals arrive as timeouts rather than "
        "as exceptions spends the timeout times --attempts on every node. 0 removes "
        "the bound, which is right when this is the only thing running and wrong "
        "inside a survey.",
    )
    parser.add_argument(
        "--client",
        choices=("library", "raw"),
        default="library",
        help="which Modbus client makes the reads. `library` (the default) is "
        "what the integration uses, so whatever it cannot read the integration "
        "cannot either; `raw` is a strict socket that additionally reports the "
        "count which reconciles a padded frame",
    )
    parser.add_argument("-c", "--component", help="test only this component")
    parser.add_argument(
        "-r",
        "--range",
        action="append",
        default=[],
        metavar="SPACE:ADDRESS:COUNT",
        help="test an explicit range, e.g. input:5010:25. Repeatable. "
        "Addresses are protocol addresses, one below the register number.",
    )
    return parser


def _ranges(given: list[str]) -> list[Block]:
    blocks = []
    for text in given:
        try:
            space, address, count = text.split(":")
            blocks.append(Block("(given)", space, int(address), int(count)))
        except ValueError:
            raise SystemExit(
                f"Cannot read --range {text!r}; want space:address:count"
            ) from None
    if any(block.space not in {"input", "holding"} for block in blocks):
        raise SystemExit("Space must be 'input' or 'holding'.")
    return blocks


async def _run(args: argparse.Namespace, blocks: list[Block]) -> Outcome:
    client = client_for(
        args.host, args.port, args.unit, args.timeout, args.delay, args.client
    )
    print(f"  client {client.label}")
    print(f"{len(blocks)} block(s), {args.attempts} attempts each.\n")
    try:
        return await measure(
            client,
            blocks,
            args.attempts,
            args.rounds,
            narrow_budget=args.narrow_budget,
        )
    finally:
        await client.close()


def main() -> int:
    """Test each block, bisect the ones that fail, and say what to do about it."""
    args = _parser().parse_args()
    blocks = _ranges(args.range) if args.range else _blocks_of(args.component)
    print(f"Reading {args.host}:{args.port}, unit {args.unit}. This only reads.")
    # Both axes, because they are independent: which reads to make, and which
    # client makes them. A clean result from a client that reconnects and
    # retries mid-block is worth less: the integration cannot do either.
    print("  plan   the library's own block reads, recorded from the poll")
    report(probe.run(_run(args, blocks)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
