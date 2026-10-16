"""The block read test from the device page, held to the terminal tool's.

`sungrow_modbus.block_test` is the second producer of a measurement that
`device-fingerprints/scripts/python/blocks.py` and `sungrow_survey.py` already
make, and its answers end up in the same place: a published document, read by
a maintainer deciding what goes in `src/sungrow_modbus/layout.py`. So most of
what is asserted here is *agreement* -- the same blocks, the same outcome
words, the same budget and the same document shape -- and the rest is the
classification that four bugs in this project got wrong: an exception response
is an answer, a lost link is not.

Fakes raise the library's real exception types. A fixture that fakes a
refusal with a bare `ModbusError` cannot see the difference this module exists
to keep.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusDesyncError,
    ModbusTimeoutError,
)
import pytest

from sungrow_modbus import block_test
from sungrow_modbus.block_test import (
    DROPPED,
    INCONSISTENT,
    REFUSED,
    REJECTED,
    TIMED_OUT,
    UNNARROWED,
    Block,
    attempt,
    inverter_blocks,
    measure,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "device-fingerprints" / "scripts" / "python"))

import blocks as terminal  # noqa: E402
import sungrow_survey  # noqa: E402

Reader = Callable[[str, int, int], object]


def reader(fails: Callable[[str, int, int], BaseException | None]):
    """Return a read that raises whatever `fails` says, and counts its calls."""
    calls: list[tuple[str, int, int]] = []

    async def read(space: str, address: int, count: int) -> list[int]:
        calls.append((space, address, count))
        error = fails(space, address, count)
        if error is not None:
            raise error
        return [0] * count

    read.calls = calls  # type: ignore[attr-defined]
    return read


def refuses(register: int) -> Callable[[str, int, int], BaseException | None]:
    """Refuse any read that covers this register, as a WiNet-S refuses 2613."""
    address = register - 1

    def fails(_space: str, start: int, count: int) -> BaseException | None:
        if start <= address < start + count:
            return IllegalDataAddressError(2)
        return None

    return fails


# -- agreement with the terminal tool ----------------------------------------


def test_the_outcome_words_and_the_budget_are_the_terminal_tools() -> None:
    """`sungrow_modbus.layout` quotes these words, so they are part of the result."""
    for name in ("OK", "DROPPED", "REFUSED", "REJECTED", "INCONSISTENT"):
        assert getattr(block_test, name) == getattr(terminal, name), name
    assert block_test.UNNARROWED == terminal.UNNARROWED
    assert block_test.NARROW_BUDGET == terminal.NARROW_BUDGET
    assert (block_test.ROUNDS, block_test.ATTEMPTS) == (
        sungrow_survey.ROUNDS,
        sungrow_survey.ATTEMPTS,
    )


async def test_the_terminal_tool_measures_through_the_library() -> None:
    """One measurement: the terminal tool prints around it and changes nothing.

    The same reads -- a block that refuses, one that answers, and the
    narrowing that names the register -- must give the same outcome whether
    the library is asked directly or through `blocks.measure`.
    """
    plan = [
        Block("fast_input", "input", 5010, 25),
        Block("sub_controller_firmware", "input", 2612, 15),
    ]
    mine = await measure(reader(refuses(2613)), plan, narrow_budget=0)

    async def no_close() -> None:
        return None

    client = terminal.Client("stub", reader(refuses(2613)), None, no_close)
    theirs = await terminal.measure(
        client,
        plan,
        attempts=block_test.ATTEMPTS,
        rounds=block_test.ROUNDS,
        echo=lambda _line: None,
        narrow_budget=0,
    )

    assert theirs == mine
    assert sungrow_survey._block_document(
        block_test.Outcome(), "raw"
    ) == block_test.document(block_test.Outcome(), client="raw")


# -- classification ------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (IllegalDataAddressError(2), REFUSED),
        (ModbusTimeoutError("Response timeout after 10.0 seconds"), TIMED_OUT),
        (ModbusConnectionError("Connection lost"), DROPPED),
        (ModbusDesyncError("PDU length mismatch"), REJECTED),
        (OSError("No route to host"), DROPPED),
    ],
)
async def test_an_answer_and_a_lost_link_are_told_apart(error, expected) -> None:
    """An exception response is the device answering; the rest are not."""
    kind, _detail = await attempt(reader(lambda *_: error), "input", 2612, 15, 2)
    assert kind == expected


async def test_a_refusal_is_worded_as_the_terminal_tool_words_it() -> None:
    """`exception 0x02`, which is what every published document says."""
    _kind, detail = await attempt(
        reader(lambda *_: IllegalDataAddressError(2)), "input", 2612, 15, 2
    )
    assert detail == "2/2, exception 0x02"


async def test_one_failure_among_successes_is_contention() -> None:
    """Failed once, answered once: another client, not this register."""
    answers = iter([IllegalDataAddressError(2), None])
    kind, detail = await attempt(reader(lambda *_: next(answers)), "input", 1, 1, 2)
    assert kind == INCONSISTENT
    assert detail == "failed 1/2"


# -- measuring and narrowing ---------------------------------------------------


async def test_a_refused_register_is_narrowed_to_itself() -> None:
    """The finding `layout.py` needs: one register, not a fifteen-wide block."""
    outcome = await measure(
        reader(refuses(2613)),
        [Block("sub_controller_firmware", "input", 2612, 15)],
    )
    assert [block.address for block in outcome.failing] == [2612]
    ((block, kind, _detail),) = outcome.culprits
    assert (block.address, block.count, kind) == (2612, 1, REFUSED)


async def test_a_block_that_answers_once_is_never_narrowed() -> None:
    """Answering in any round rules out a register fault."""
    rounds = iter([IllegalDataAddressError(2)] * 2 + [None] * 10)
    read = reader(lambda *_: next(rounds))
    outcome = await measure(read, [Block("fast_input", "input", 5010, 25)])

    assert outcome.failing == []
    assert outcome.culprits == []
    assert [block.address for block in outcome.intermittent] == [5010]


async def test_narrowing_that_runs_out_of_time_says_so() -> None:
    """A range wearing `not narrowed` names no register, and must look it."""
    outcome = await measure(
        reader(refuses(2613)),
        [Block("sub_controller_firmware", "input", 2612, 15)],
        narrow_budget=1e-9,
    )
    assert [kind for _block, kind, _detail in outcome.culprits] == [UNNARROWED]


async def test_progress_counts_reads_and_holds_still_while_narrowing() -> None:
    """The bar's total is known before the run; narrowing is not counted."""
    blocks = [
        Block("fast_input", "input", 5010, 25),
        Block("sub_controller_firmware", "input", 2612, 15),
    ]
    steps: list[tuple[str, bool]] = []
    await measure(reader(refuses(2613)), blocks, step=lambda *step: steps.append(step))

    counted = [label for label, countable in steps if countable]
    assert len(counted) == block_test.planned_steps(blocks)
    assert any(label.startswith("narrowing") for label, countable in steps)
    assert all(not countable for label, countable in steps if "narrowing" in label)


async def test_nothing_failing_publishes_three_empty_lists() -> None:
    """A run where no block failed says so with three empty lists."""
    blocks = await inverter_blocks()
    published = block_test.document(await measure(reader(lambda *_: None), blocks))

    assert len(published["answered"]) == len(blocks)
    assert published["never_answered"] == []
    assert published["intermittent"] == []
    assert published["narrowed"] == []
