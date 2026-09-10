"""The block read test, which had no test of its own.

`scripts/sungrow_scan/blocks.py` answers one question -- which read inside a
component fails, and whether that is a register fault or another client
competing for the inverter -- and its answers get written into
`scripts/layout.py`, which is only ever added to from a measurement. So a
wrong answer here becomes a permanent wrong fix.

It shipped with no test, and the cost was exactly what that predicts: with
the library client, the default wherever the library is installed, a refused
register raised a class nothing in the file caught. The tool crashed on the
first refusal rather than recording it, and every existing test passed.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

import blocks  # noqa: E402
from blocks import (  # noqa: E402
    DROPPED,
    OK,
    PADDED,
    REFUSED,
    REJECTED,
    WRONG_LENGTH,
    Dropped,
    FrameRejected,
    LibraryClient,
    ModbusError,
    PaddedFrame,
    WrongLength,
    attempt,
    measure,
)


class Stub:
    """A client whose every read does whatever the test says.

    `attempt` takes a client and a plan, so a stub is the whole seam: no
    socket, no inverter, and every outcome reachable including the ones a
    real device produces about twice a year.
    """

    label = "stub"

    def __init__(self, *results, reconnect_on=()):
        """Take one result per read, cycling the last one for later reads."""
        self._results = list(results)
        self._reconnect_on = set(reconnect_on)
        self.reads = 0
        self.reconnects = 0

    def read(self, space, address, count):
        """Return or raise whatever was queued for this read."""
        result = self._results[min(self.reads, len(self._results) - 1)]
        self.reads += 1
        if self.reads in self._reconnect_on:
            self.reconnects += 1
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        """Nothing to close."""


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ([1, 2, 3], OK),
        (ModbusError("exception 0x02"), REFUSED),
        (Dropped("connection reset"), DROPPED),
        (OSError("timed out"), DROPPED),
        (FrameRejected("PDU length mismatch"), REJECTED),
        (WrongLength(15, 11), WRONG_LENGTH),
        (PaddedFrame(22, 33, 11), PADDED),
    ],
)
def test_every_way_a_read_can_fail_is_classified(result, expected) -> None:
    """Each outcome the tool distinguishes, because each implies a different fix."""
    kind, _detail = attempt(Stub(result), "input", 5010, 25, 3)
    assert kind == expected


def test_a_read_that_only_worked_after_a_reconnect_is_a_failure() -> None:
    """The hazard this tool once hid completely.

    `Connection.read` reconnects and tries again, which is right for a
    fingerprint. It reported "ok (3/3)" for a one-register read of gerd's
    5242 -- a read the integration cannot make, because a `Component` has no
    mid-block retry, so one drop loses every field in the block.
    """
    kind, detail = attempt(Stub([1], reconnect_on=(1, 2, 3)), "input", 5241, 1, 3)
    assert kind == DROPPED
    assert "reconnect" in detail


def test_one_failure_among_successes_is_named_contention_not_a_fault() -> None:
    """A verdict here would isolate whatever else was polling the inverter."""
    kind, detail = attempt(
        Stub(ModbusError("exception 0x02"), [1], [1]), "input", 5010, 25, 3
    )
    assert kind == blocks.INCONSISTENT
    assert "another Modbus" in detail
    assert "quiet" in detail


def test_a_fault_fails_every_round_and_contention_moves() -> None:
    """The distinction `measure` exists to draw, over several rounds."""
    blocks_to_read = [
        ("fast_input", "input", 5010, 25),
        ("grid_frequency", "input", 5241, 1),
    ]

    class Selective(Stub):
        """Answers everything except one address, which never answers."""

        def read(self, space, address, count):
            self.reads += 1
            if address == 5241:
                raise ModbusError("exception 0x02")
            return [0] * count

    outcome = measure(Selective(), blocks_to_read, attempts=2, rounds=2, echo=_silent)
    assert [key[0] for key in outcome.failing] == ["grid_frequency"]
    assert outcome.intermittent == []
    # Narrowed to the one register, which is what goes into layout.ISOLATE.
    assert [(entry[2], entry[3]) for entry in outcome.culprits] == [(5241, 1)]


def test_a_block_that_answers_at_least_once_is_not_narrowed() -> None:
    """Bisecting contention wastes reads and invents a culprit."""
    outcome = measure(
        Stub(ModbusError("exception 0x02"), [0] * 25),
        [("fast_input", "input", 5010, 25)],
        attempts=2,
        rounds=1,
        echo=_silent,
    )
    assert outcome.failing == [], "contention is not a register fault"
    assert outcome.culprits == [], "and must not be narrowed as one"
    assert [key[0] for key in outcome.intermittent] == ["fast_input"]


def _silent(*_args, **_kwargs):
    """Swallow the tool's output; these tests assert on its return value."""


def test_the_library_client_raises_what_attempt_catches() -> None:
    """The regression, at the seam where it lived.

    `LibraryClient.read` imported `modbus_connection.ModbusError`, which
    shadowed this file's own -- so the class it raised for a refused register
    was not the class `attempt` catches, and the exception escaped to the top
    level. Asserted against `blocks.ModbusError` by identity rather than by
    name, because the bug was two different classes with the same name.
    """
    from modbus_connection import ModbusError as LibraryModbusError

    client = object.__new__(LibraryClient)
    client._delay = 0
    client._runner = _Runner()
    client._unit = _Unit(LibraryModbusError("exception 0x02 for function code 0x04"))

    with pytest.raises(ModbusError) as raised:
        client.read("input", 13199, 8)
    assert type(raised.value) is blocks.ModbusError
    # And therefore reaches the classifier rather than the user's terminal.
    assert attempt(Stub(raised.value), "input", 13199, 8, 1)[0] == REFUSED


def test_a_dropped_link_from_the_library_client_stays_a_drop() -> None:
    """`ModbusConnectionError` is the link going away, not a refusal."""
    from modbus_connection import ModbusConnectionError

    client = object.__new__(LibraryClient)
    client._delay = 0
    client._runner = _Runner()
    client._unit = _Unit(ModbusConnectionError("connection lost"))

    with pytest.raises(Dropped):
        client.read("input", 5010, 25)


class _Runner:
    """Stands in for the `asyncio.Runner` the real client owns."""

    def run(self, coroutine):
        """Run the coroutine to completion on a loop of its own."""
        import asyncio

        return asyncio.run(coroutine)


class _Unit:
    """A library unit whose reads always raise the given error."""

    def __init__(self, error):
        self._error = error

    async def read_input_registers(self, address, count):
        raise self._error

    async def read_holding_registers(self, address, count):
        raise self._error


class _Slow(Stub):
    """A client whose every read fails, and takes time doing it.

    Which is the case the budget exists for. On a LAN a Sungrow refuses with
    exception 0x02 in milliseconds; over one VPN measured on 2026-09-09 the
    same refusal arrived as a 10-second timeout, so with `--attempts 3` a
    single read cost 30 seconds and narrowing one 15-register block cost a
    quarter of an hour.
    """

    def __init__(self, seconds: float = 10.0):
        super().__init__(ModbusError("Response timeout after 10.0 seconds"))
        self._seconds = seconds
        self.clock = 0.0

    def read(self, *args):
        # Charged per read, because that is what a timeout costs. `attempt`
        # makes `--attempts` of them, so one verdict costs three times this.
        self.clock += self._seconds
        return super().read(*args)


def test_narrowing_stops_at_its_budget_and_says_which_ranges_it_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bound that keeps the cheapest phase from costing the whole survey.

    Four blocks like this one outran a survey's 25-minute cap and the run was
    killed before it wrote a document -- so an un-narrowed range has to come
    back marked, not dropped and not narrowed. The alternative that was
    considered and rejected is in `blocks.NARROW_BUDGET`: a per-block budget
    bounds each block and leaves the phase unbounded.
    """
    client = _Slow(seconds=30.0)
    monkeypatch.setattr(blocks, "monotonic", lambda: client.clock)

    outcome = measure(
        client,
        [("firmware_block_battery", "input", 13279, 15)],
        attempts=3,
        rounds=1,
        echo=_silent,
        narrow_budget=120.0,
    )

    assert [key[0] for key in outcome.failing] == ["firmware_block_battery"]
    assert outcome.culprits, "the block failed, so something must be reported"
    # Four reads of 30s fit in 120s; a full narrowing of 15 registers is 29.
    assert client.reads < 29, "the budget did not bound anything"
    unnarrowed = [row for row in outcome.culprits if row[4] == blocks.UNNARROWED]
    assert unnarrowed, "a range the budget cut short must say so"
    for _name, _space, _address, count, _kind, _detail in unnarrowed:
        assert count > 1, "a single register was reached, so it is an answer"


def _narrowing_reads(monkeypatch, blocks_to_test, budget) -> tuple[int, set[str]]:
    """Return reads spent narrowing, and which blocks got any, for one run."""
    client = _Slow()
    monkeypatch.setattr(blocks, "monotonic", lambda: client.clock)
    outcome = measure(
        client,
        blocks_to_test,
        attempts=3,
        rounds=1,
        echo=_silent,
        narrow_budget=budget,
    )
    # The tally reads every block `attempts` times before narrowing begins.
    tally = 3 * len(blocks_to_test)
    return client.reads - tally, {row[0] for row in outcome.culprits}


def test_the_budget_bounds_the_phase_and_not_each_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two failing blocks must not cost twice what one does.

    This is the whole argument for dividing a total instead of bounding each
    block, and it is only visible by comparing two runs: a per-block budget
    passes every single-block test and still lets a device that fails eight
    blocks run eight times as long.

    The second block must also not be starved by the first. A *shared*
    deadline is spent in list order, so it narrows block one to a register
    and never reads block two at all -- and the list order is the register
    plan's, which has nothing to do with which finding matters.
    """
    one, narrowed_one = _narrowing_reads(
        monkeypatch, [("firmware_block_battery", "input", 13279, 15)], 240.0
    )
    two, narrowed_two = _narrowing_reads(
        monkeypatch,
        [
            ("meter_channel_2", "input", 13199, 8),
            ("firmware_block_battery", "input", 13279, 15),
        ],
        240.0,
    )

    assert one > 0, "the one-block run narrowed nothing, so this proves nothing"
    # One attempt group of slack per extra block: each block's own deadline is
    # checked after its last affordable read, so the boundary costs a group.
    assert two <= one + 3, (
        f"the same budget bought {two} narrowing reads across two blocks "
        f"against {one} across one -- it is bounding each block, not the phase"
    )
    assert narrowed_two == {"meter_channel_2", "firmware_block_battery"}, (
        "both blocks must be reached, not just the first"
    )
    assert narrowed_one == {"firmware_block_battery"}


def test_no_budget_narrows_the_whole_way() -> None:
    """0 means unbounded, which is right when this is all that is running."""
    client = Stub(ModbusError("exception 0x02"))
    outcome = measure(
        client,
        [("firmware_block_battery", "input", 13279, 15)],
        attempts=1,
        rounds=1,
        echo=_silent,
        narrow_budget=0,
    )
    assert all(row[3] == 1 for row in outcome.culprits), (
        "unbounded narrowing reaches single registers"
    )
    assert blocks.UNNARROWED not in {row[4] for row in outcome.culprits}


def test_the_block_test_reads_only_the_inverters_own_components() -> None:
    """A regression that happened, and would have corrupted every survey.

    Recording the SBR's and the wallbox's components into `scan_plan.json`
    added eight blocks to the test, on unit ids the test does not use: input
    10740 and 21215 answer 0xFFFF or refuse at the inverter's unit whatever
    the pack and the charge point are doing. All eight would have failed, all
    eight would then have been narrowed at the cost of the narrowing budget,
    and all eight would have been offered to `scripts/layout.py` as register
    faults.

    So the filter is on the plan's own `unit` role rather than on a list of
    names, which means a device added later is excluded by default -- the
    safe direction.
    """
    from portable import load_plan

    plan = load_plan()
    elsewhere = {
        entry["component"] for entry in plan["components"] if entry.get("unit")
    }
    assert elsewhere, "the plan should carry components on other units"

    tested = {name for name, _space, _address, _count in blocks._blocks_of(plan, None)}
    assert not tested & elsewhere, (
        f"the block read test would read {sorted(tested & elsewhere)} at the "
        "inverter's unit id, where they cannot answer"
    )
    # Every inverter component is still tested, or the guard has gone too far.
    inverter = {
        entry["component"]
        for entry in plan["components"]
        if not entry.get("unit") and entry["blocks"]
    }
    assert inverter <= tested


def test_naming_another_devices_component_still_selects_it() -> None:
    """Excluded by default is not excluded outright.

    Somebody testing a pack's cell block against a real pack should be able
    to say so: `blocks.py <host> --unit 200 -c sbr_battery_cells`. The
    default is what had to change, not the capability.
    """
    from portable import load_plan

    selected = blocks._blocks_of(load_plan(), "sbr_battery_cells")
    assert selected == [("sbr_battery_cells", "input", 10756, 8)], selected


def test_narrowing_goes_wherever_the_caller_sends_its_output() -> None:
    """`echo` all the way down, matching `measure`.

    It made no practical difference to `collect.py`, which replaces
    `sys.stdout` with its transcript so a bare `print` landed there anyway.
    It is fixed because a caller that passes `echo` and then finds half the
    output on stdout is a trap, and this file's own tests pass `_silent` --
    so before this, every narrowing line from a test was printed for real.
    """
    lines: list[str] = []
    outcome = measure(
        Stub(ModbusError("exception 0x02")),
        [("fast_input", "input", 5241, 1)],
        attempts=1,
        rounds=1,
        echo=lines.append,
    )
    assert outcome.culprits, "the block failed, so it was narrowed"
    # The narrowed range's own line is in the caller's sink, not on stdout.
    assert any("input 5241 x1" in line for line in lines), lines
