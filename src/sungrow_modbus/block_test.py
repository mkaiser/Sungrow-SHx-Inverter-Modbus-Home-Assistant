"""The block read test: which of the poll's block reads this device fails.

The library pools neighbouring registers into single block reads, which is
what makes a full poll a few dozen requests instead of one per field. The
cost is that one register a device cannot answer takes its whole block with
it -- a `Component` either updates or raises -- so one bad register can empty
a whole tier of entities, and only a block read test says which register it
is.

The integration runs it from the device page and
`device-survey/scripts/python/blocks.py` from a terminal, both through
this module. Two callers, one measurement:

* **The outcome words are the tool's**, `OK` to `UNNARROWED`, because they are
  quoted in `src/sungrow_modbus/inverter/layout.py` and a measurement's phrasing is part
  of it.
* **The published shape is `sungrow_survey.py`'s**, key for key, so one reader handles
  a document from either. `tests/test_block_test.py` holds the two together.
* **The blocks are recorded, not computed** -- `inverter_blocks` drives every
  polled component against a recorder and keeps what it asked for, and the
  terminal tool takes its plan from the same function. So both test exactly
  the reads the poll makes.

Two clients, one measurement. `read` is any `read(space, address, count)`:
the integration's own stack, which fails exactly where the integration fails
and reports a padded frame as `REJECTED`; or `raw_client.RawClient.read`,
the strict raw socket, which names the count that would reconcile the frame
(`PADDED`, `WRONG_LENGTH`) and counts its reconnects -- a read that needed
one is reported `DROPPED`, because the integration cannot retry mid-block.

Reads only. Nothing in this module can write.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
import time
from typing import TYPE_CHECKING, Any

from modbus_connection import (
    ModbusError,
    ModbusExceptionError,
    ModbusProtocolError,
    ModbusTimeoutError,
)

from . import raw_client
from .inverter.components import InverterIdentity
from .inverter.registers import COMPONENTS

if TYPE_CHECKING:
    from modbus_connection.model import Component

#: How a block read came back. The same words as `blocks.py`.
OK = "ok"
DROPPED = "dropped the connection"
REFUSED = "refused with an exception"
REJECTED = "the library rejected the frame"

#: The raw client's two diagnoses, each naming its own fix: a device answering
#: 15 registers to a request for 11 is saying the field is 15 long, and a
#: padded frame says which count makes its two lengths agree. Both belong in
#: `layout.COUNTS`.
WRONG_LENGTH = "answered a different length"
PADDED = "padded the frame"

#: No answer within the timeout -- the link, not the device. Its own word so
#: that neither "refused" nor "dropped the connection" is claimed for it.
TIMED_OUT = "timed out"

#: Answered some attempts and not others: contention, not a fault. A block
#: that answers *any* attempt is never narrowed and never offered to
#: `src/sungrow_modbus/inverter/layout.py`, because isolating a register on that
#: evidence would be isolating whatever else was polling the inverter at the time.
INCONSISTENT = "inconsistent"

#: Narrowing ran out of time here, so this range is as small as the run made
#: it -- not as small as it goes. `layout.py` takes an exact register.
UNNARROWED = "not narrowed"

#: Rounds over the whole plan and attempts per read, as `sungrow_survey.py` runs them.
#: Two different measurements: three back-to-back reads of one block can all
#: land in one busy moment, where three rounds with the other blocks between
#: them cannot. A register fault fails in every round.
ROUNDS = 3
ATTEMPTS = 2

#: Seconds for the **whole** narrowing phase, split evenly across the blocks
#: that failed. Not per block, deliberately.
#:
#: Narrowing walks every node of a binary tree over the block, so a
#: 15-register block costs about 29 reads. Where a device refuses immediately
#: -- exception 0x02, as on a LAN -- that is a couple of seconds. Where
#: refusal arrives as a **timeout** instead, as it can over a VPN, each read
#: costs the timeout times the attempts: 30 seconds, so one block is a quarter
#: of an hour, and a handful of such blocks is a run somebody kills before it
#: writes a document.
#:
#: A *per-block* budget does not fix that: it bounds each block and leaves the
#: phase unbounded, so a device that fails eight blocks costs eight times as
#: much as one that fails one. Dividing a total is what makes the survey's
#: length predictable -- one failing block gets the whole budget and is
#: narrowed to a register, eight get a minute each and are narrowed to a half.
#: 480 seconds is eight minutes, against a dump that is allowed 600.
NARROW_BUDGET = 480.0

#: Said in the document because it changes what the rest means. The terminal
#: tool may use the strict raw socket, which names the count a padded frame
#: needs and retries by reconnecting; this is the integration's own stack, so
#: whatever it cannot read the integration cannot read either.
CLIENT = (
    "modbus-connection through Home Assistant's modbus integration -- the "
    "integration's own reads, so it fails exactly where the integration fails"
)

Read = Callable[[str, int, int], Awaitable[list[int]]]
"""Read `count` words at a protocol address in `"input"` or `"holding"` space."""

Step = Callable[[str, bool], None]
"""Report progress: a label, and whether it is a step that can be counted."""

Reconnects = Callable[[], int]
"""How many times the client has reconnected so far."""


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
    reconnects: int = 0
    """How often the client reconnected; only the raw client counts them."""


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


async def component_blocks(name: str, klass: type[Component]) -> list[Block]:
    """Return the block reads one component makes, recorded rather than computed.

    Any component, on any device: the terminal tool aims a test at the SBR's
    or the wallbox's by name, on the unit that answers for it.
    """
    recorder = _Recorder()
    await klass(recorder).async_update()  # type: ignore[arg-type]
    return [
        Block(name, space, address, count) for space, address, count in recorder.seen
    ]


async def inverter_blocks() -> list[Block]:
    """Return every block read the inverter's poll makes, in poll order.

    Recorded by driving each component against `_Recorder`, so the answer is
    whatever the pooling rules produce today rather than a second
    implementation of them. The identity block is included because it is read
    at setup, and a device that refuses it never gets that far. Components on
    another unit -- the SBR pack, the wallbox -- are not: read at the
    inverter's unit they answer 0xFFFF or refuse whatever the pack is doing,
    which would put guaranteed failures into every survey.
    """
    blocks: list[Block] = []
    for name, klass in {**COMPONENTS, "identity": InverterIdentity}.items():
        blocks += await component_blocks(name, klass)
    return blocks


def declared(space: str, address: int) -> str:
    """Return the field at an address, or say that nothing reads it.

    The distinction decides the fix. A bad **declared** register is isolated
    into its own component; a bad address in a **gap** is one nothing asked
    for in the first place, and the answer there is to stop bridging the gap
    rather than to isolate anything.
    """
    from .addresses import device_components

    for components in device_components().values():
        for name, klass in components.items():
            if klass.register_space != space:
                continue
            for field_name, declared_field in klass.declared_fields.items():
                start = declared_field.address
                if start <= address < start + declared_field.count:
                    return f"{field_name} (in {name})"
    return "nothing reads this -- pooling bridges a gap to reach it"


def _describe(err: ModbusError) -> tuple[str, str]:
    """Classify a failed read, in the words the terminal tool uses.

    The library's taxonomy decides, never the message: an exception
    *response* is the device answering, while a lost connection, a timeout or
    a desync is the link failing to carry the question. `AGENTS.md` says what
    confusing the two costs.
    """
    if isinstance(err, ModbusExceptionError):
        code = err.exception_code
        return REFUSED, f"exception 0x{code:02X}" if code is not None else str(err)
    if isinstance(err, ModbusProtocolError):
        return REJECTED, str(err)
    if isinstance(err, ModbusTimeoutError):
        return TIMED_OUT, str(err)
    return DROPPED, str(err) or type(err).__name__


async def attempt(
    read: Read,
    space: str,
    address: int,
    count: int,
    attempts: int,
    reconnects: Reconnects | None = None,
) -> tuple[str, str]:
    """Read one block several times and say what happened, and how consistently.

    Repetition is the point. A Sungrow grants very few sessions, so a single
    failure is more likely another client than a bad register, and a fault
    that is real fails every attempt.

    With `reconnects`, a read that answered only after the client reconnected
    is a failure: the raw client reconnects and retries, which is right for
    a survey and would report "ok (3/3)" for a block the integration,
    which has no mid-block retry, cannot read at all.
    """
    outcomes: list[tuple[str, str]] = []
    for _ in range(attempts):
        before = reconnects() if reconnects is not None else 0
        try:
            await read(space, address, count)
        except raw_client.PaddedFrame as err:
            outcomes.append(
                (
                    PADDED,
                    f"declared {err.declared_registers} registers, frame sized "
                    f"for {err.frame_registers}; ask for {err.consistent_count}",
                )
            )
        except raw_client.WrongLength as err:
            outcomes.append((WRONG_LENGTH, f"got {err.got} registers"))
        except raw_client.Refused as err:
            outcomes.append((REFUSED, str(err)))
        except ModbusError as err:
            outcomes.append(_describe(err))
        except TimeoutError as err:
            outcomes.append((TIMED_OUT, str(err) or type(err).__name__))
        except raw_client.TimedOut as err:
            outcomes.append((TIMED_OUT, str(err)))
        except OSError as err:
            outcomes.append((DROPPED, str(err) or type(err).__name__))
        else:
            after = reconnects() if reconnects is not None else 0
            if after > before:
                outcomes.append(
                    (
                        DROPPED,
                        f"answered only after {after - before} reconnect(s); "
                        "the integration cannot retry mid-block",
                    )
                )
            else:
                outcomes.append((OK, ""))

    kinds = {kind for kind, _ in outcomes}
    every = f"{attempts}/{attempts}"
    if kinds == {OK}:
        return OK, every
    if OK in kinds:
        failures = sum(1 for kind, _ in outcomes if kind != OK)
        return INCONSISTENT, f"failed {failures}/{attempts}"
    kind, detail = outcomes[0]
    return kind, f"{every}, {detail}" if detail else every


Narrowed = Callable[[Block, int, str, str], None]
"""Report one narrowing read: the range, its depth, the outcome and detail."""

Result = Callable[[Block, int, str, str], None]
"""Report one block's read in a round: the block, the round, outcome, detail."""


async def _bisect(
    read: Read,
    block: Block,
    attempts: int,
    deadline: float | None,
    step: Step | None,
    *,
    reconnects: Reconnects | None = None,
    on_narrow: Narrowed | None = None,
    depth: int = 0,
) -> list[tuple[Block, str, str]]:
    """Narrow a failing range to the smallest ranges that still fail.

    Every minimal failing range, not the first: a block can hold more than one
    bad register. A range whose halves both read while the whole does not is
    reported as it is -- the device refuses the *span*, and no single register
    is at fault. Past `deadline` the range is returned `UNNARROWED`: a partial
    answer that says it is partial.
    """
    if deadline is not None and time.monotonic() > deadline:
        if on_narrow is not None:
            on_narrow(block, depth, UNNARROWED, "out of time")
        return [(block, UNNARROWED, "narrowing ran out of time here")]
    if step is not None:
        step(
            f"narrowing {block.component}: {block.space} "
            f"{block.address + 1} x{block.count}",
            False,
        )
    kind, detail = await attempt(
        read, block.space, block.address, block.count, attempts, reconnects
    )
    if on_narrow is not None:
        on_narrow(block, depth, kind, detail)
    if kind in {OK, INCONSISTENT}:
        return []
    if block.count == 1:
        return [(block, kind, detail)]
    half = block.count // 2
    left = Block(block.component, block.space, block.address, half)
    right = Block(
        block.component, block.space, block.address + half, block.count - half
    )
    found: list[tuple[Block, str, str]] = []
    for half_block in (left, right):
        found += await _bisect(
            read,
            half_block,
            attempts,
            deadline,
            step,
            reconnects=reconnects,
            on_narrow=on_narrow,
            depth=depth + 1,
        )
    if found:
        return found
    return [(block, kind, f"{detail}; both halves read on their own")]


#: The outcomes `layout.py` may be changed on: the device answering, in a way
#: that names a fix. Every entry in `layout.ISOLATE` is an exception code, a
#: deterministic hangup or a padded frame, and `layout.COUNTS` takes the
#: length a padded or wrong-length frame names. A timeout is deliberately not
#: among them -- from this end a silent inverter and an answer lost in a
#: tunnel are the same event, and the same four blocks at one house closed
#: the connection on a LAN two days before they timed out over a VPN.
EVIDENCE = frozenset({REFUSED, DROPPED, PADDED, WRONG_LENGTH, REJECTED})


def refused_outright(kind: str, detail: str = "") -> bool:
    """Whether a narrowed failure is the kind `layout.py` may be changed on.

    Decided by the outcome, and a detail that mentions a timeout overrides
    it: a drop that the link reported as a timeout is still the link.
    """
    lowered = detail.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return False
    return kind in EVIDENCE


class Advice(StrEnum):
    """What a narrowed failure means for `layout.py`, before any wording."""

    FORWARDING_LIMIT = "forwarding limit"
    """Measured through a communication module: maybe a measuring point the
    dongle does not forward, which is capability gating, not `layout.py`."""
    NOT_NARROWED = "not narrowed"
    """The budget stopped first, so the range names no single register."""
    NOT_EVIDENCE = "not evidence"
    """It timed out rather than refusing, which says nothing about it."""
    ALREADY_ISOLATED = "already isolated"
    """The device refuses it, and `layout.ISOLATE` already holds it."""
    ISOLATE = "isolate"
    """The device refuses it outright: this is the measurement to add."""


@dataclass(frozen=True)
class Finding:
    """One component's narrowed failures of one kind, with what they mean."""

    component: str
    space: str
    outcome: str
    detail: str
    addresses: tuple[int, ...]
    """Protocol addresses, sorted; one below the register numbers."""
    advice: Advice

    @property
    def registers(self) -> str:
        """The register numbers as runs: "13200-13207", "5242"."""
        return register_ranges(address + 1 for address in self.addresses)


def register_ranges(numbers: Iterable[int]) -> str:
    """Return "13200-13207" for eight consecutive numbers, "5242" for one.

    Runs rather than a list, because consecutive addresses are the usual
    shape -- one absent measuring point is a block of them -- and eight
    numbers separated by commas hide whether they are contiguous.
    """
    runs: list[tuple[int, int]] = []
    for number in sorted(numbers):
        if runs and number == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], number)
        else:
            runs.append((number, number))
    return ", ".join(
        str(start) if start == end else f"{start}-{end}" for start, end in runs
    )


def findings(outcome: Outcome, *, through_module: bool) -> list[Finding]:
    """Say what each narrowed failure means for `layout.py`.

    Grouped by component and by how it failed, because the fix is per
    component and the narrowing is per register: eight refused addresses in
    one meter block are one finding, not eight.

    `through_module` comes first because it changes what a refusal is.
    Measured on gerd's SH8.0RT-V112: input 2612 and 2628 refuse three times
    out of three through its WiNet-S and read perfectly over the inverter's
    own LAN port four minutes later. Isolating them would make every direct
    user pay a per-field read for a dongle's behaviour.
    """
    from .inverter.layout import ISOLATE

    grouped: dict[tuple[str, str, str], list[int]] = {}
    details: dict[tuple[str, str, str], str] = {}
    for block, kind, detail in outcome.culprits:
        key = (block.component, block.space, kind)
        grouped.setdefault(key, []).extend(
            block.address + offset for offset in range(block.count)
        )
        details.setdefault(key, detail)
    # The components that exist only because a field was moved out of its
    # tier, which is what "already isolated" means.
    isolated = set(ISOLATE.values())
    found = []
    for (component, space, kind), addresses in grouped.items():
        detail = details[(component, space, kind)]
        if through_module:
            advice = Advice.FORWARDING_LIMIT
        elif kind == UNNARROWED:
            advice = Advice.NOT_NARROWED
        elif not refused_outright(kind, detail):
            advice = Advice.NOT_EVIDENCE
        elif component in isolated:
            advice = Advice.ALREADY_ISOLATED
        else:
            advice = Advice.ISOLATE
        found.append(
            Finding(component, space, kind, detail, tuple(sorted(addresses)), advice)
        )
    return found


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
    reconnects: Reconnects | None = None,
    on_result: Result | None = None,
    on_narrow: Narrowed | None = None,
    on_narrowing: Callable[[Block, int, int, float], None] | None = None,
) -> Outcome:
    """Read every block over several rounds, and narrow what never answered.

    A block that answered in any round, or answered inconsistently within
    one, is not a fault and is not narrowed. Narrowing gets `narrow_budget`
    seconds in total, split evenly across the failing blocks so the last in
    the list gets the same chance as the first.

    `on_result` follows each block's read in each round, `on_narrowing(block,
    index, total, seconds)` precedes the narrowing of each failing block, and
    `on_narrow` follows each narrowing read -- what a terminal prints. `reconnects` is
    the raw client's counter; see `attempt`.
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
            kind, detail = await attempt(
                read, block.space, block.address, block.count, attempts, reconnects
            )
            counts = outcome.tally.setdefault(block, {})
            counts[kind] = counts.get(kind, 0) + 1
            if on_result is not None:
                on_result(block, round_number, kind, detail)

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
        for index, block in enumerate(outcome.failing, 1):
            if on_narrowing is not None:
                on_narrowing(block, index, len(outcome.failing), each)
            deadline = time.monotonic() + each if each else None
            outcome.culprits += await _bisect(
                read,
                block,
                attempts,
                deadline,
                step,
                reconnects=reconnects,
                on_narrow=on_narrow,
            )
    if reconnects is not None:
        outcome.reconnects = reconnects()
    return outcome


def document(
    outcome: Outcome,
    *,
    rounds: int = ROUNDS,
    attempts: int = ATTEMPTS,
    client: str | None = CLIENT,
    reconnects: int = 0,
) -> dict[str, Any]:
    """Render a block read test as a survey publishes it.

    The one renderer: the integration and `sungrow_survey.py` both publish
    through it, the survey saying which of its clients measured and how often
    its raw socket reconnected. Register numbers as Sungrow's document prints
    them, one above the protocol address. Carries no host and no serial: block
    numbers and outcome words only, so it publishes the way the rest of a
    survey does.
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
        # Said because it changes what the rest means: the library reports a
        # padded frame as rejected, the raw socket names the count it needs.
        "client": client,
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
        # The terminal tool counts reconnects its raw socket made. The
        # integration's stack reconnects inside the shared connection and does
        # not say so, and a reconnect there is already counted as the failed
        # read that caused it -- hence 0 by default.
        "reconnects": reconnects,
    }
