#!/usr/bin/env python3
"""The block read test: find the register that takes a whole block down.

The library pools neighbouring registers into single block reads, which is
what makes a full poll 23 requests instead of 105. The cost is that one
register a device cannot answer takes its whole block with it -- and a
`Component` either updates or raises, so a bad block loses every field in it.
Twice now that has cost real users most of a tier:

* the two firmware strings at 2612 and 2628 come back in a frame the device
  **pads to fifteen registers while declaring the correct byte count**, which
  `modbus-connection` rightly rejects -- and that failed the 58-register
  `slowest_input` request, leaving 36 unrelated entities permanently empty;
* input 2612 and input 2628 -- the sub-controller and battery firmware
  strings -- **refuse with exception 0x02, three attempts out of three,
  through a WiNet-S**, while every other block answers in the same session.
  Replicated on two houses, two inverter models and two dongle firmwares,
  against two direct-LAN readings of the same register map where all 27
  blocks answer. So the tool's own output has to be read against the
  transport: this is a dongle not forwarding a measuring point, and no
  amount of isolating registers in `scripts/layout.py` will fix it.

Those two are why the tool reports *how* a block failed rather than just
that it did: the first has a fix in `layout.COUNTS`, the second in
`layout.ISOLATE`, and a link that merely drops has no fix here at all.

One warning about reading the *other* tool's output, because it cost a wrong
conclusion: a fingerprint's `components_that_did_not_answer` came from a
`pending` list that was one pass stale, so a device answering everything on
the first attempt was written up as having missed all thirteen components.
The claim "every component missed as a whole while 95 of 104 fields read
individually" was published in this docstring and in a committed fingerprint
on that basis, and it was the tool, not the inverter. Fixed in
`probe.py`, guarded by
`tests/test_portable_readings.py::test_a_device_that_answers_everything_reports_nothing_missed`.
The measurement that stands is the one above, and it came from *this* file --
which is the argument for the block read test being a fixed phase of every
survey rather than something run when a document looks odd.

`scripts/layout.py` is where the fix goes, and it takes two things this script
produces: the register to isolate, and the length that actually reads. Guessing
either from a document is how the wrong fix gets committed, which is why that
module says to add to it only from a measurement.

Two tools used to answer this and they have been merged here. `probe.py` had a
`components` subcommand that drove the real library and tallied every read it
issued over several rounds -- the better way to tell a register fault from
contention, because a fault fails in every round and contention moves. This
file had the narrowing, the field naming and the padded-frame diagnosis. Both
halves are here now: `--rounds` is the interleaved measurement, `--attempts`
the back-to-back one, and `--client` chooses which Modbus stack makes the
reads.

    python scripts/sungrow_scan/blocks.py 192.168.1.10               # every component
    python scripts/sungrow_scan/blocks.py 192.168.1.10 -c fast_input # one of them
    python scripts/sungrow_scan/blocks.py 192.168.1.10 -r input:5010:25   # a range

It reads and never writes. Nothing here can change a setting.

**It needs no packages** -- the Modbus client comes from
`portable.py` next door, which speaks the protocol over a plain
socket. The block plan comes from the device library when this runs somewhere
that has it (the devcontainer, or after `pip install sungrow-modbus`); without
it, pass ranges by hand with `-r` and the script works just the same.
"""

from __future__ import annotations

import argparse
import contextlib
from pathlib import Path
import struct
import sys
from time import monotonic
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portable import (
    _FC_READ_HOLDING,
    _FC_READ_INPUT,
    PLAN_FILE,
    Connection,
    Dropped,
    ModbusError,
    load_plan,
)

#: How a read came back. `WRONG_LENGTH` is its own outcome rather than an
#: error, because it is the one that names its own fix: a device answering 15
#: registers to a request for 11 is telling you the field is 15 long.
OK = "ok"
DROPPED = "dropped the connection"
REFUSED = "refused with an exception"
WRONG_LENGTH = "answered a different length"
PADDED = "padded the frame"

#: Only the library client produces this: it validates the frame and raises,
#: without saying what would have read. That is the honest report -- the
#: integration cannot read it either -- and the raw client is what turns it
#: into a number, so this outcome says to re-run with `--client raw`.
REJECTED = "the library rejected the frame"

#: Answered some attempts and not others. A *result*, not a fault: contention
#: correlates in time, so this is most likely another client polling the
#: inverter. It was a bare string inside `attempt` and therefore invisible to
#: the tally, which counted "no OK in this block's outcomes" as never
#: answered -- so a block that answered two attempts out of three was
#: narrowed, printed under "smallest ranges that still fail", and recommended
#: for `layout.ISOLATE`. That is the wrong fix, permanently applied, from the
#: one condition the tool is most careful about in prose.
INCONSISTENT = "inconsistent"


class Reader(Connection):
    """A connection strict enough to fail where the integration fails.

    This is the whole reason the script exists rather than a couple of raw
    reads. `portable.Connection` trusts the PDU byte count and
    reads whatever the MBAP length says is there, so it accepts frames the
    shipping stack rejects -- and a diagnostic that reports "ok" for a read
    the integration cannot make is worse than no diagnostic.

    Measured on the reference SH10RT at register 2613, asking for 11:

        -> 00 01 00 00 00 06 01 04 0a 34 00 0b     address 2612, count 11
        <- 00 01 00 00 00 21 01 04 16 53 55 42 ... 39 bytes

    `mbap_len = 0x21 = 33`, so the frame carries 30 data bytes -- fifteen
    registers. `byte_count = 0x16 = 22` says eleven, which is what was asked
    for and what the first 22 bytes correctly contain. The device pads the
    frame and does not say so. `modbus-connection` validates against the MBAP
    length and rejects the whole answer; a lenient client takes the byte count
    and never notices.

    So both numbers are reported, and the count that would make them agree --
    which is the number that belongs in `layout.COUNTS`.
    """

    def _read_once(self, unit, function, address, count):
        """Read one block, raising when the frame is padded or the count wrong."""
        request = struct.pack(">HHHBBHH", 1, 0, 6, unit, function, address, count)
        self.sock.sendall(request)
        header = _recv(self.sock, 8)
        length = struct.unpack(">H", header[4:6])[0]
        body = _recv(self.sock, max(0, length - 2))
        if header[7] != function:
            raise ModbusError(f"exception 0x{body[0] if body else 0:02X}")
        if len(body) < 1:
            raise ModbusError("empty answer")
        # A self-consistent answer has mbap_len == 3 + byte_count: one byte
        # each of unit, function and byte count, then the data.
        if length != 3 + body[0]:
            raise PaddedFrame(declared=body[0], mbap_length=length, asked=count)
        if body[0] != count * 2:
            raise WrongLength(body[0] // 2, count)
        return list(struct.unpack(f">{count}H", body[1 : 1 + count * 2]))


class WrongLength(Exception):
    """The device answered, with a number of registers nobody asked for."""

    def __init__(self, got: int, asked: int) -> None:
        """Remember both counts, because the fix is the one it sent."""
        super().__init__(f"asked {asked} registers, got {got}")
        self.got = got
        self.asked = asked


class PaddedFrame(Exception):
    """The frame is longer than the byte count it declares.

    The data is there and correct; the frame around it is not, and the
    shipping Modbus stack rejects it on that basis. `consistent_count` is the
    count to ask for so that the two numbers agree.
    """

    def __init__(self, declared: int, mbap_length: int, asked: int) -> None:
        """Work out the count that would make the frame self-consistent."""
        self.declared_registers = declared // 2
        self.frame_registers = (mbap_length - 3) // 2
        self.asked = asked
        self.consistent_count = self.frame_registers
        super().__init__(
            f"declared {self.declared_registers} registers but sent a frame "
            f"sized for {self.frame_registers}"
        )


class RawClient:
    """The strict raw socket, and the only client that can name the fix.

    When a device pads a frame, `modbus-connection` validates it and raises --
    correctly, and unhelpfully: the number that would have read is in the
    reply it just discarded. This client reads that number out and reports it,
    which is the value `layout.COUNTS` needs.
    """

    label = "raw socket -- strict, and reports the count that reconciles a padded frame"

    def __init__(self, host: str, port: int, unit: int, timeout: float, delay: float):
        """Open nothing yet; `Reader` connects on its first read."""
        self._link = Reader(host, port, timeout, delay)
        self._unit = unit

    @property
    def reconnects(self) -> int:
        """How many times the device has hung up and been reconnected."""
        return self._link.reconnects

    def read(self, space: str, address: int, count: int) -> list[int]:
        """Read one block, raising the strict outcomes this module defines."""
        function = _FC_READ_INPUT if space == "input" else _FC_READ_HOLDING
        return self._link.read(self._unit, function, address, count)

    def close(self) -> None:
        """Close the socket."""
        self._link.close()


class LibraryClient:
    """`modbus-connection`, which fails exactly where the integration fails.

    Strictness by construction rather than by reimplementation. Whatever this
    client cannot read, the integration cannot read -- there is no second
    frame validator to keep in step, which is what the padded-frame diagnosis
    cost a day over. It reconnects on nothing, which is also the integration's
    behaviour: a `Component` has no mid-block retry.
    """

    label = "modbus-connection -- rejects a frame exactly as the integration does"

    def __init__(self, host: str, port: int, unit: int, timeout: float, delay: float):
        """Open one connection and keep one loop for the whole run."""
        import asyncio

        from modbus_connection import ModbusTcpParams
        from modbus_connection.tmodbus import ModbusConnection

        self._runner = asyncio.Runner()
        self._connection = ModbusConnection(
            ModbusTcpParams(host=host, port=port), timeout=timeout
        )
        self._unit = self._connection.for_unit(unit)
        self._delay = delay

    #: Nothing to count: this client never reconnects, deliberately.
    reconnects = 0

    def read(self, space: str, address: int, count: int) -> list[int]:
        """Read one block through the library, translating what it raises."""
        import time

        # Imported under another name **on purpose**. As
        # `from modbus_connection import ModbusError` this shadowed the
        # module-level one this file raises and `attempt` catches, so a
        # refused register came back as a class nothing here handles: the
        # default client crashed on the first refusal instead of recording
        # it, which is the one measurement the tool exists to take.
        from modbus_connection import (
            ModbusConnectionError,
            ModbusError as LibraryModbusError,
        )

        read = (
            self._unit.read_input_registers
            if space == "input"
            else self._unit.read_holding_registers
        )
        try:
            words = list(self._runner.run(read(address, count)))
        except ModbusConnectionError as err:
            raise Dropped(str(err)) from err
        except LibraryModbusError as err:
            # A protocol error is the padded-frame case, and the library has
            # already thrown away the length that would have worked.
            if "PDU length" in str(err) or "Protocol" in type(err).__name__:
                raise FrameRejected(str(err)) from err
            raise ModbusError(str(err)) from err
        if self._delay:
            time.sleep(self._delay)
        return words

    def close(self) -> None:
        """Close the connection and the loop that owned it."""
        with contextlib.suppress(Exception):
            self._runner.run(self._connection.close())
        with contextlib.suppress(Exception):
            self._runner.close()


class FrameRejected(Exception):
    """The library refused the reply, without saying what would have read."""


def _recv(sock, size):
    """Read exactly `size` bytes, or raise `Dropped`."""
    chunks = []
    while size > 0:
        chunk = sock.recv(size)
        if not chunk:
            raise Dropped("the device closed the connection")
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


def attempt(
    client: RawClient | LibraryClient,
    space: str,
    address: int,
    count: int,
    attempts: int,
) -> tuple[str, str]:
    """Read one block several times and say what happened, and how consistently.

    Repetition is the whole point. A Sungrow accepts very few Modbus sessions,
    so a single failure is more likely to be another client than a bad
    register -- and a register recorded as a hazard when it was really
    contention gets isolated forever for nothing. A fault that is real fails
    every attempt.
    """
    outcomes: list[tuple[str, str]] = []
    for _ in range(attempts):
        # A reconnect during the read *is* the failure, even when the retry
        # that follows it succeeds. `Connection.read` reconnects and tries
        # again, which is right for a fingerprint and hid the worst hazard
        # this script exists to find: gerd's SH8.0RT closes the connection on
        # a one-register read of 5242, and this reported it "ok (3/3)" while
        # the integration could not read the component at all. The
        # integration has no mid-component retry -- one drop loses every
        # field in the block -- so a read that needed a reconnect is a read
        # it cannot make.
        before = client.reconnects
        try:
            client.read(space, address, count)
        except FrameRejected as err:
            outcomes.append(
                (REJECTED, f"{err}; re-run with --client raw for the count")
            )
        except PaddedFrame as err:
            outcomes.append(
                (
                    PADDED,
                    f"declared {err.declared_registers} registers, frame sized "
                    f"for {err.frame_registers}; ask for {err.consistent_count}",
                )
            )
        except WrongLength as err:
            outcomes.append((WRONG_LENGTH, f"got {err.got} registers"))
        except ModbusError as err:
            outcomes.append((REFUSED, str(err)))
        except (Dropped, OSError) as err:
            outcomes.append((DROPPED, str(err)))
        else:
            if client.reconnects > before:
                outcomes.append(
                    (
                        DROPPED,
                        f"answered only after {client.reconnects - before} "
                        "reconnect(s); the integration cannot retry mid-block",
                    )
                )
            else:
                outcomes.append((OK, ""))

    kinds = {kind for kind, _ in outcomes}
    if kinds == {OK}:
        return OK, f"{attempts}/{attempts}"
    if OK in kinds:
        # Not a verdict. Isolating a register on this evidence would be
        # isolating whatever else was polling the inverter at the time.
        failures = sum(1 for kind, _ in outcomes if kind != OK)
        return INCONSISTENT, (
            f"failed {failures}/{attempts} -- most likely another Modbus "
            "client, not this register; re-run when the inverter is quiet"
        )
    kind, detail = outcomes[0]
    every = f"{attempts}/{attempts}"
    return kind, f"{every}, {detail}" if detail else every


#: Narrowing gave up here, so this range is as small as the run could make it.
#:
#: Not an outcome of a read -- every read that produced it failed -- but it has
#: to travel with the range, because "input 13279 x15 refused" narrowed to one
#: register and "input 13279 x15 refused" that was never narrowed are the same
#: sentence and mean different things. `layout.py` takes an exact register, so
#: a range wearing this word is not yet an answer.
UNNARROWED = "not narrowed"

#: Seconds for the **whole** narrowing phase, split evenly across the blocks
#: that failed. Not per block, deliberately: see below.
#:
#: Measured, and the measurement is why this exists at all. Narrowing walks
#: every node of a binary tree over the block, so a 15-register block costs
#: about 29 reads. Where a device refuses immediately -- exception 0x02, which
#: is what two houses on a LAN did -- that is a couple of seconds and this is
#: never reached. Where refusal arrives as a **timeout** instead, which is
#: what a third house did over a VPN, each read costs the timeout times
#: `--attempts`: 30 seconds, so one block is a quarter of an hour. Four such
#: blocks outran the survey's own 25-minute cap and the run was killed with no
#: document written at all -- the whole survey lost to the cheapest phase in
#: it, and a phase whose findings are a nice-to-have losing one whose findings
#: are the point.
#:
#: A *per-block* budget does not actually fix that: it bounds each block and
#: leaves the phase unbounded, so a device that fails eight blocks costs eight
#: times as much as one that fails one. Dividing a total is what makes the
#: survey's length predictable, and it spends the time where there is least to
#: look at -- one failing block gets the whole budget and is narrowed to a
#: register, eight get a minute each and are narrowed to a half.
#:
#: 480 seconds is eight minutes, against a dump that is allowed 600. Two
#: failing blocks on the slow link above then get 240 each, which is eight
#: reads -- enough to name one exact register, depth-first, rather than
#: several vague halves.
NARROW_BUDGET = 480.0


def bisect(
    client: RawClient | LibraryClient,
    space: str,
    address: int,
    count: int,
    attempts: int,
    depth: int = 0,
    deadline: float | None = None,
    echo=print,
) -> list[tuple[int, int, str, str]]:
    """Narrow a failing range to the smallest ranges that still fail.

    Returns every minimal failing range, not the first one -- a block can have
    more than one bad register, and stopping at the first would send somebody
    back to the hardware a second time.

    A range whose halves both read while the whole does not is reported as it
    is: that is the signature of a device answering a fixed length, where no
    single register is at fault and the *span* is what it refuses.

    Bounded by `deadline`, an absolute `time.monotonic()`. Past it the range
    is returned marked `UNNARROWED` rather than narrowed further or dropped:
    a partial answer that says it is partial. See `NARROW_BUDGET`.

    `echo` rather than `print`, matching `measure`. It made no difference to
    `collect.py` -- that replaces `sys.stdout` with its transcript, so a bare
    `print` landed there anyway -- but a caller passing `echo` and then
    finding half the output somewhere else is a trap worth not leaving, and
    `measure` already took one.
    """
    indent = "   " + "  " * depth
    if deadline is not None and monotonic() > deadline:
        echo(f"{indent}{space} {address} x{count:<4} {UNNARROWED} (out of time)")
        return [(address, count, UNNARROWED, "narrowing ran out of time here")]
    kind, detail = attempt(client, space, address, count, attempts)
    echo(f"{indent}{space} {address} x{count:<4} {kind} ({detail})")
    if kind in {OK, "inconsistent"}:
        return []
    if count == 1:
        return [(address, 1, kind, detail)]

    half = count // 2
    left = bisect(client, space, address, half, attempts, depth + 1, deadline, echo)
    right = bisect(
        client, space, address + half, count - half, attempts, depth + 1, deadline, echo
    )
    if left or right:
        return left + right
    return [(address, count, kind, f"{detail}; both halves read on their own")]


#: The artefact this reads instead of the library. Written by
#: `scripts/generate_scan_plan.py`, committed, and checked in CI, so it cannot
#: drift from what the integration actually asks for.
def _blocks_of(plan: dict, component: str | None) -> list[tuple[str, str, int, int]]:
    """Return the reads to test, as (component, space, address, count).

    **Only the inverter's own components**, unless one is named explicitly.
    A plan entry carrying a `unit` role belongs to a device on another unit
    id -- the SBR pack at 200 or 2, the wallbox at 3 or 248 -- and reading
    its addresses at the inverter's unit tests nothing: input 10740 and
    21215 answer 0xFFFF or refuse there whatever the pack and the charge
    point are doing.

    This is a regression that happened: recording those components into the
    plan added eight blocks to every survey's block read test, all of them
    guaranteed to fail, all of them then narrowed at the cost of the
    narrowing budget, and all of them offered to `scripts/layout.py` as
    register faults. Naming a component still selects it, so
    `-c sbr_battery_cells` works against a pack when that is what somebody
    is testing.
    """
    known = [entry["component"] for entry in plan["components"]]
    if component is not None and component not in known:
        raise SystemExit(f"No such component: {component}.\nKnown: {', '.join(known)}")
    return [
        (entry["component"], entry["space"], address, count)
        for entry in plan["components"]
        if (
            entry["component"] == component
            if component is not None
            else not entry.get("unit")
        )
        for address, count in entry["blocks"]
    ]


def _declared(plan: dict, space: str, address: int) -> str:
    """Return the field at an address, or say that nothing reads it.

    The distinction decides the fix. A bad **declared** register is isolated
    into its own component; a bad address in a **gap** is one nothing asked
    for in the first place, and the answer there is to stop bridging the gap
    rather than to isolate anything.
    """
    for field in plan["fields"]:
        if field["space"] != space:
            continue
        if field["address"] <= address < field["address"] + field["count"]:
            return f"{field['name']} (in {field['component']})"
    return "nothing reads this -- pooling bridges a gap to reach it"


class BlockOutcome(NamedTuple):
    """What a block read test measured, for a caller to report on.

    Extracted from `main` so `collect.py` can run this as a phase of a
    survey rather than as a command somebody remembers to run afterwards.
    The distinction the fields carry is the whole point of the tool:
    `failing` never answered and belongs in `scripts/layout.py`,
    `intermittent` answered sometimes and belongs in a re-run on a quiet
    inverter, and confusing the two is how a wrong fix gets committed.
    """

    #: {(name, space, address, count): {outcome: times}}
    tally: dict
    intermittent: list
    failing: list
    #: (name, space, address, count, outcome, detail) -- the narrowed ranges.
    culprits: list
    reconnects: int


def measure(
    client, blocks, attempts=3, rounds=1, echo=print, narrow_budget=NARROW_BUDGET
) -> BlockOutcome:
    """Read every block, several rounds, and narrow whatever never answered.

    `echo` rather than `print` so a caller can put this inside a transcript
    or send it to stderr; the wording is unchanged, because `layout.py`
    quotes it and a measurement's phrasing is part of the measurement.

    Narrowing gets `narrow_budget` seconds in total, split evenly across the
    blocks that failed, and then stops and marks what it did not reach. That
    bound is not tidiness: without it, a link whose refusals arrive as
    timeouts spends a quarter of an hour on a single block and the survey
    around it is killed before it writes anything. See `NARROW_BUDGET`.
    """
    tally: dict[tuple[str, str, int, int], dict[str, int]] = {}
    culprits: list[tuple[str, str, int, int, str, str]] = []
    for round_number in range(1, max(1, rounds) + 1):
        if rounds > 1:
            echo(f"round {round_number}:")
        for name, space, address, count in blocks:
            kind, detail = attempt(client, space, address, count, attempts)
            counts = tally.setdefault((name, space, address, count), {})
            counts[kind] = counts.get(kind, 0) + 1
            flag = "     " if kind == OK else "  >> "
            echo(f"{flag}{name:<34} {space} {address} x{count:<4} {kind} ({detail})")
        if rounds > 1:
            echo("")

    # Never answered in any round is the only shape that belongs in
    # layout.py. Mixed is contention, and saying so is the point -- so a block
    # that answered *any* attempt, including one that answered inconsistently
    # inside a single round, is not a fault and is not narrowed.
    answered = (OK, INCONSISTENT)
    failing = [
        key
        for key, counts in tally.items()
        if not any(kind in counts for kind in answered)
    ]
    intermittent = [
        key
        for key, counts in tally.items()
        if INCONSISTENT in counts or (OK in counts and len(counts) > 1)
    ]
    if failing:
        # Split rather than shared, so the last block in the list gets the
        # same chance as the first. A shared deadline is spent in list order,
        # which on a slow link means block one is narrowed to a register and
        # blocks two to four are never read at all -- and the list order is
        # the plan's, which is arbitrary as far as the finding is concerned.
        each = narrow_budget / len(failing) if narrow_budget else 0
        echo(
            f"\nNarrowing {len(failing)} failing block(s)"
            + (f", {each:.0f}s each.\n" if each else ".\n")
        )
        for name, space, address, count in failing:
            echo(f"  {name} ({space} {address} x{count})")
            for bad_address, bad_count, kind, detail in bisect(
                client,
                space,
                address,
                count,
                attempts,
                deadline=monotonic() + each if each else None,
                echo=echo,
            ):
                culprits.append((name, space, bad_address, bad_count, kind, detail))
            echo("")
    return BlockOutcome(tally, intermittent, failing, culprits, client.reconnects)


def report(outcome: BlockOutcome, plan: dict, echo=print) -> None:
    """Say what the measurement means, and what to do about it."""
    if outcome.intermittent:
        echo("\nIntermittent, so contention rather than a fault:")
        for key in outcome.intermittent:
            name, space, address, count = key
            summary = ", ".join(
                f"{kind} x{n}" for kind, n in sorted(outcome.tally[key].items())
            )
            echo(f"  {name:<34} {space} {address} x{count:<4} {summary}")
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
    for name, space, address, count, kind, detail in outcome.culprits:
        registers = (
            f"register {address + 1}"
            if count == 1
            else f"registers {address + 1}-{address + count}"
        )
        echo(f"  {space} {address} x{count}  ({registers}), inside {name}")
        echo(f"     {kind} -- {detail}")
        # Only worth listing the fields where the range is small enough to
        # act on. An un-narrowed 15-register block would print fifteen names
        # and imply all fifteen are suspect.
        if kind != UNNARROWED:
            for offset in range(count):
                named = _declared(plan, space, address + offset)
                echo(f"     {address + offset + 1}: {named}")
        if kind in {WRONG_LENGTH, PADDED}:
            echo("     -> the count named above belongs in layout.COUNTS")
        echo("")

    stopped = [row for row in outcome.culprits if row[4] == UNNARROWED]
    if stopped:
        echo(
            f"{len(stopped)} range(s) above stopped at the narrowing budget rather "
            "than at\na register. On this link a refusal arrives as a timeout, so "
            "each read\ncosts the timeout times --attempts; the block above is as "
            "small as the\nbudget reached, not as small as it goes. To finish one, "
            "aim at it:\n"
        )
        for name, space, address, count, _kind, _detail in stopped:
            echo(
                f"  python scripts/sungrow_scan/blocks.py <host> "
                f"-r {space}:{address}:{count}    # {name}"
            )
        echo("\nA lower --timeout, or --attempts 1, buys depth on a link like this.")
        echo("")

    if len(stopped) < len(outcome.culprits):
        echo("Put the fields these belong to in scripts/layout.py, and quote this")
        echo("output in the comment: that module is only ever added to from a")
        echo("measurement, and this is the measurement.")


def client_for(host, port, unit, timeout, delay, prefer="auto"):
    """Return the Modbus client to measure with, and why it is that one.

    The library client is the default where it can be had, because whatever
    it cannot read the integration cannot read either -- there is no second
    frame validator to keep in step. The raw client is not a fallback so much
    as the other half of the tool: it is the one that turns a rejected frame
    into the count that would have worked.
    """
    if prefer == "raw":
        return RawClient(host, port, unit, timeout, delay)
    try:
        return LibraryClient(host, port, unit, timeout, delay)
    except ModuleNotFoundError:
        if prefer == "library":
            raise SystemExit(
                "--client library needs modbus-connection, which is not "
                "installed here. Leave the flag off to use the raw client."
            ) from None
        return RawClient(host, port, unit, timeout, delay)


def main() -> int:
    """Test each block, bisect the ones that fail, and say what to do about it."""
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
        choices=("auto", "library", "raw"),
        default="auto",
        help="which Modbus client makes the reads. `library` is what the "
        "integration uses, so whatever it cannot read the integration cannot "
        "either; `raw` is a strict socket that additionally reports the count "
        "which reconciles a padded frame. `auto` (the default) prefers the "
        "library and falls back to raw where it is not installed",
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
    args = parser.parse_args()

    loaded = load_plan()
    if args.range:
        blocks = []
        for raw in args.range:
            try:
                space, address, count = raw.split(":")
                blocks.append(("(given)", space, int(address), int(count)))
            except ValueError:
                raise SystemExit(
                    f"Cannot read --range {raw!r}; want space:address:count"
                ) from None
        if any(space not in {"input", "holding"} for _, space, *_ in blocks):
            raise SystemExit("Space must be 'input' or 'holding'.")
    else:
        blocks = _blocks_of(loaded, args.component)

    print(f"Reading {args.host}:{args.port}, unit {args.unit}. This only reads.")
    # Both axes, because they are independent: which reads to make, and which
    # client makes them. A clean result from a lenient client is worth much
    # less, which is how registers the integration cannot read at all were
    # once measured as fine.
    verified = "verified against the library" if loaded["verified"] else "not verified"
    print(
        f"  plan   {PLAN_FILE.name} -- "
        f"{len(loaded['components'])} components, {verified}"
    )
    client = client_for(
        args.host, args.port, args.unit, args.timeout, args.delay, args.client
    )
    print(f"  client {client.label}")
    print(f"{len(blocks)} block(s), {args.attempts} attempts each.\n")

    try:
        outcome = measure(
            client,
            blocks,
            args.attempts,
            args.rounds,
            narrow_budget=args.narrow_budget,
        )
    finally:
        client.close()
    report(outcome, loaded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
