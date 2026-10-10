"""The block read test: which of the poll's block reads this device fails.

The library pools neighbouring registers into single block reads, which is
what makes a full poll 27 requests instead of 105. The cost is that one
register a device cannot answer takes its whole block with it -- a `Component`
either updates or raises -- so one bad register can empty a whole tier of
entities. That has happened twice, and both times only a block read test said
which register it was.

This is the same measurement `scripts/sungrow_scan/blocks.py` makes from a
terminal, for the integration to run from the device page. Two producers, one
measurement:

* **The outcome words are the tool's**, `OK` to `UNNARROWED`, because they are
  quoted in `scripts/layout.py` and a measurement's phrasing is part of it.
* **The published shape is `collect.py`'s**, key for key, so one reader handles
  a document from either. `tests/test_block_test.py` holds the two together.
* **The blocks are recorded, not computed** -- `inverter_blocks` drives every
  polled component against a recorder and keeps what it asked for, which is
  how `scripts/generate_scan_plan.py` builds the plan the terminal tool reads.
  So both test exactly the reads the poll makes, and the test asserts it.

What this cannot do that the terminal tool can: name the count that would
reconcile a padded frame. That needs the raw reply, and `modbus-connection`
rightly discards a frame it rejects. So a rejection is reported as `REJECTED`
and the fix still comes from `blocks.py --client raw`. Everything else -- a
refusal, a dropped link, contention -- reads the same here as there.

Reads only. Nothing in this module can write.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import time
from typing import Any

from modbus_connection import ModbusError, ModbusExceptionError, ModbusProtocolError

from .components import InverterIdentity
from .registers import COMPONENTS

#: How a block read came back. The same words as `blocks.py`.
OK = "ok"
DROPPED = "dropped the connection"
REFUSED = "refused with an exception"
REJECTED = "the library rejected the frame"

#: Answered some attempts and not others: contention, not a fault. A block
#: that answers *any* attempt is never narrowed and never offered to
#: `scripts/layout.py`, because isolating a register on that evidence would be
#: isolating whatever else was polling the inverter at the time.
INCONSISTENT = "inconsistent"

#: Narrowing ran out of time here, so this range is as small as the run made
#: it -- not as small as it goes. `layout.py` takes an exact register.
UNNARROWED = "not narrowed"

#: Rounds over the whole plan and attempts per read, as `collect.py` runs them.
#: Two different measurements: three back-to-back reads of one block can all
#: land in one busy moment, where three rounds with the other blocks between
#: them cannot. A register fault fails in every round.
ROUNDS = 3
ATTEMPTS = 2

#: Seconds for the **whole** narrowing phase, split evenly across the blocks
#: that failed. Equal to `blocks.NARROW_BUDGET`, for the reason given there: a
#: link whose refusals arrive as timeouts spends the timeout times the attempts
#: on every node of the tree, and one unbounded block once outran a survey's
#: own cap so the run was killed with no document at all.
NARROW_BUDGET = 480.0

#: Said in the document because it changes what the rest means. The terminal
#: tool may use a deliberately lenient raw socket; this is the integration's
#: own stack, so whatever it cannot read the integration cannot read either.
CLIENT = (
    "modbus-connection through Home Assistant's modbus integration -- the "
    "integration's own reads, so it fails exactly where the integration fails"
)

Read = Callable[[str, int, int], Awaitable[list[int]]]
"""Read `count` words at a protocol address in `"input"` or `"holding"` space."""

Step = Callable[[str, bool], None]
"""Report progress: a label, and whether it is a step that can be counted."""


@dataclass(frozen=True)
class Block:
    """One read the poll makes: which component, and where."""

    component: str
    space: str
    address: int
    """Protocol address, one below the register number in Sungrow's document."""
    count: int


@dataclass
class Outcome:
    """What a block read test measured.

    `failing` never answered in any round and is what narrowing is for;
    `intermittent` answered sometimes and is contention. Confusing the two is
    how a wrong fix gets committed, so they are kept apart from here on.
    """

    tally: dict[Block, dict[str, int]] = field(default_factory=dict)
    intermittent: list[Block] = field(default_factory=list)
    failing: list[Block] = field(default_factory=list)
    culprits: list[tuple[Block, str, str]] = field(default_factory=list)
    """Narrowed ranges: a block for the range, its outcome and the detail."""


class _Recorder:
    """A unit that answers zeros and remembers every read it was asked for."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, int, int]] = []

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        self.seen.append(("input", address, count))
        return [0] * count

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        self.seen.append(("holding", address, count))
        return [0] * count


async def inverter_blocks() -> list[Block]:
    """Return every block read the inverter's poll makes, in poll order.

    Recorded by driving each component against `_Recorder`, so the answer is
    whatever the pooling rules produce today rather than a second
    implementation of them. The identity block is included because it is read
    at setup, and a device that refuses it never gets that far. Components on
    another unit -- the SBR pack, the wallbox -- are not: read at the
    inverter's unit they answer 0xFFFF or refuse whatever the pack is doing,
    and once filled eight guaranteed failures into every survey.
    """
    blocks: list[Block] = []
    for name, klass in {**COMPONENTS, "identity": InverterIdentity}.items():
        recorder = _Recorder()
        await klass(recorder).async_update()
        blocks += [
            Block(name, space, address, count)
            for space, address, count in recorder.seen
        ]
    return blocks


def _describe(err: ModbusError) -> tuple[str, str]:
    """Classify a failed read, in the words the terminal tool uses.

    The library's taxonomy decides, never the message: an exception
    *response* is the device answering, while a lost connection, a timeout or
    a desync is the link failing to carry the question. `CLAUDE.md` lists four
    bugs that came from confusing the two.
    """
    if isinstance(err, ModbusExceptionError):
        code = err.exception_code
        return REFUSED, f"exception 0x{code:02X}" if code is not None else str(err)
    if isinstance(err, ModbusProtocolError):
        return REJECTED, str(err)
    return DROPPED, str(err) or type(err).__name__


async def attempt(
    read: Read, space: str, address: int, count: int, attempts: int
) -> tuple[str, str]:
    """Read one block several times and say what happened, and how consistently.

    Repetition is the point. A Sungrow grants very few sessions, so a single
    failure is more likely another client than a bad register, and a fault
    that is real fails every attempt.
    """
    outcomes: list[tuple[str, str]] = []
    for _ in range(attempts):
        try:
            await read(space, address, count)
        except ModbusError as err:
            outcomes.append(_describe(err))
        except (TimeoutError, OSError) as err:
            outcomes.append((DROPPED, str(err) or type(err).__name__))
        else:
            outcomes.append((OK, ""))

    kinds = {kind for kind, _ in outcomes}
    every = f"{attempts}/{attempts}"
    if kinds == {OK}:
        return OK, every
    if OK in kinds:
        failures = sum(1 for kind, _ in outcomes if kind != OK)
        return INCONSISTENT, (
            f"failed {failures}/{attempts} -- most likely another Modbus "
            "client, not this register"
        )
    kind, detail = outcomes[0]
    return kind, f"{every}, {detail}" if detail else every


async def _bisect(
    read: Read,
    block: Block,
    attempts: int,
    deadline: float | None,
    step: Step | None,
) -> list[tuple[Block, str, str]]:
    """Narrow a failing range to the smallest ranges that still fail.

    Every minimal failing range, not the first: a block can hold more than one
    bad register. A range whose halves both read while the whole does not is
    reported as it is -- the device refuses the *span*, and no single register
    is at fault. Past `deadline` the range is returned `UNNARROWED`: a partial
    answer that says it is partial.
    """
    if deadline is not None and time.monotonic() > deadline:
        return [(block, UNNARROWED, "narrowing ran out of time here")]
    if step is not None:
        step(
            f"narrowing {block.component}: {block.space} "
            f"{block.address + 1} x{block.count}",
            False,
        )
    kind, detail = await attempt(
        read, block.space, block.address, block.count, attempts
    )
    if kind in {OK, INCONSISTENT}:
        return []
    if block.count == 1:
        return [(block, kind, detail)]
    half = block.count // 2
    left = Block(block.component, block.space, block.address, half)
    right = Block(
        block.component, block.space, block.address + half, block.count - half
    )
    found = await _bisect(read, left, attempts, deadline, step)
    found += await _bisect(read, right, attempts, deadline, step)
    if found:
        return found
    return [(block, kind, f"{detail}; both halves read on their own")]


def planned_steps(blocks: list[Block], rounds: int = ROUNDS) -> int:
    """Count the steps `measure` reports as countable, before it starts.

    One per block per round. Narrowing is not counted, because how much of it
    there is depends on what fails; its steps are reported as uncounted, so a
    bar holds still while it runs rather than overshooting.
    """
    return len(blocks) * max(1, rounds)


async def measure(
    read: Read,
    blocks: list[Block],
    *,
    attempts: int = ATTEMPTS,
    rounds: int = ROUNDS,
    narrow_budget: float = NARROW_BUDGET,
    step: Step | None = None,
) -> Outcome:
    """Read every block over several rounds, and narrow what never answered.

    A block that answered in any round, or answered inconsistently within
    one, is not a fault and is not narrowed. Narrowing gets `narrow_budget`
    seconds in total, split evenly across the failing blocks so the last in
    the list gets the same chance as the first.
    """
    outcome = Outcome()
    for round_number in range(1, max(1, rounds) + 1):
        for block in blocks:
            if step is not None:
                step(
                    f"block read test, round {round_number} of {rounds}: "
                    f"{block.component}",
                    True,
                )
            kind, _detail = await attempt(
                read, block.space, block.address, block.count, attempts
            )
            counts = outcome.tally.setdefault(block, {})
            counts[kind] = counts.get(kind, 0) + 1

    answered = (OK, INCONSISTENT)
    outcome.failing = [
        block
        for block, counts in outcome.tally.items()
        if not any(kind in counts for kind in answered)
    ]
    outcome.intermittent = [
        block
        for block, counts in outcome.tally.items()
        if INCONSISTENT in counts or (OK in counts and len(counts) > 1)
    ]
    if outcome.failing:
        each = narrow_budget / len(outcome.failing) if narrow_budget else 0
        for block in outcome.failing:
            deadline = time.monotonic() + each if each else None
            outcome.culprits += await _bisect(read, block, attempts, deadline, step)
    return outcome


def document(
    outcome: Outcome, *, rounds: int = ROUNDS, attempts: int = ATTEMPTS
) -> dict[str, Any]:
    """Render a block read test in the shape `collect.py` publishes.

    Register numbers as Sungrow's document prints them, one above the protocol
    address. Carries no host and no serial: block numbers and outcome words
    only, so it publishes the way the rest of a fingerprint does.
    """

    def where(block: Block) -> dict[str, Any]:
        return {
            "component": block.component,
            "space": block.space,
            "register": block.address + 1,
            "count": block.count,
        }

    return {
        "rounds": rounds,
        "attempts": attempts,
        "client": CLIENT,
        "answered": [
            where(block)
            for block in outcome.tally
            if block not in outcome.failing and block not in outcome.intermittent
        ],
        "never_answered": [
            {**where(block), "outcomes": sorted(outcome.tally[block])}
            for block in outcome.failing
        ],
        "intermittent": [
            {**where(block), "outcomes": sorted(outcome.tally[block])}
            for block in outcome.intermittent
        ],
        "narrowed": [
            {**where(block), "outcome": kind, "detail": detail}
            for block, kind, detail in outcome.culprits
        ],
        # The terminal tool counts reconnects its raw socket made. This stack
        # reconnects inside the shared connection and does not say so, and a
        # reconnect here is already counted as the failed read that caused it.
        "reconnects": 0,
    }
