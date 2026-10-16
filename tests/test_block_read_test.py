"""The block read test's verdicts, through either client.

`sungrow_modbus.block_test` answers one question -- which read inside a
component fails, and whether that is a register fault or another client
competing for the inverter -- and its answers get written into
`src/sungrow_modbus/inverter/layout.py`, which is only ever added to from a
measurement. So a wrong answer here becomes a permanent wrong fix.

The terminal tool, `device-fingerprints/scripts/python/blocks.py`, shipped
with no test once, and the cost was exactly what that predicts: with the
library client a refused register raised a class nothing caught, and the
tool crashed on the first refusal rather than recording it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusProtocolError,
    ModbusTimeoutError,
)
import pytest

from sungrow_modbus import block_test, raw_client
from sungrow_modbus.block_test import (
    DROPPED,
    INCONSISTENT,
    OK,
    PADDED,
    REFUSED,
    REJECTED,
    TIMED_OUT,
    UNNARROWED,
    WRONG_LENGTH,
    Block,
    Outcome,
    attempt,
    declared,
    measure,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "device-fingerprints" / "scripts" / "python"))

import blocks  # noqa: E402


class Stub:
    """A client whose every read does whatever the test says.

    `attempt` takes a `read` and a reconnect counter, so a stub is the whole
    seam: no socket, no inverter, and every outcome reachable including the
    ones a real device produces about twice a year.
    """

    def __init__(self, *results, reconnect_on=()):
        """Take one result per read, cycling the last one for later reads."""
        self._results = list(results)
        self._reconnect_on = set(reconnect_on)
        self.reads = 0
        self.reconnects = 0

    async def read(self, space, address, count):
        """Return or raise whatever was queued for this read."""
        result = self._results[min(self.reads, len(self._results) - 1)]
        self.reads += 1
        if self.reads in self._reconnect_on:
            self.reconnects += 1
        if isinstance(result, Exception):
            raise result
        return result

    def counter(self):
        """Return the reconnect count, as `attempt` asks for it."""
        return self.reconnects


def _attempt(stub, address=5010, count=25, attempts=3):
    return asyncio.run(
        attempt(stub.read, "input", address, count, attempts, stub.counter)
    )


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ([1, 2, 3], OK),
        (IllegalDataAddressError(2), REFUSED),
        (raw_client.Refused(2), REFUSED),
        (raw_client.Dropped("connection reset"), DROPPED),
        (ModbusConnectionError("connection lost"), DROPPED),
        (OSError("unreachable"), DROPPED),
        (ModbusProtocolError("PDU length mismatch"), REJECTED),
        (raw_client.WrongLength(15, 11), WRONG_LENGTH),
        (raw_client.PaddedFrame(22, 33, 11), PADDED),
        (ModbusTimeoutError("Response timeout after 10.0 seconds"), TIMED_OUT),
        (raw_client.TimedOut("no answer within 8s"), TIMED_OUT),
    ],
)
def test_every_way_a_read_can_fail_is_classified(result, expected) -> None:
    """Each outcome the tool distinguishes, because each implies a different fix."""
    kind, _detail = _attempt(Stub(result))
    assert kind == expected


def test_a_padded_frame_names_the_count_that_reads() -> None:
    """The number that belongs in `layout.COUNTS`, from the raw reply."""
    _kind, detail = _attempt(Stub(raw_client.PaddedFrame(22, 33, 11)))
    assert "declared 11 registers, frame sized for 15; ask for 15" in detail


def test_a_timeout_is_not_a_refusal() -> None:
    """A read nobody answered is labelled as such, never "refused".

    The 10 s timeouts at input 13199 and the firmware strings were published
    as "refused with an exception" -- a claim about the device made from a
    silence that could as well be the VPN.
    """
    kind, detail = _attempt(
        Stub(ModbusTimeoutError("Response timeout after 10.0 seconds")),
        13199,
        8,
        2,
    )
    assert kind == TIMED_OUT
    assert "Response timeout" in detail


def test_a_read_that_only_worked_after_a_reconnect_is_a_failure() -> None:
    """The hazard this tool once hid completely.

    The raw client reconnects and tries again, which is right for a
    fingerprint. It reported "ok (3/3)" for a one-register read of gerd's
    5242 -- a read the integration cannot make, because a `Component` has no
    mid-block retry, so one drop loses every field in the block.
    """
    kind, detail = _attempt(Stub([1], reconnect_on=(1, 2, 3)), 5241, 1)
    assert kind == DROPPED
    assert "reconnect" in detail


def test_one_failure_among_successes_is_named_contention_not_a_fault() -> None:
    """A verdict here would isolate whatever else was polling the inverter."""
    kind, detail = _attempt(Stub(IllegalDataAddressError(2), [1], [1]))
    assert kind == INCONSISTENT
    # The count only: the line is printed per block per round, and has to fit.
    assert detail == "failed 1/3"

    # What it means is said once, by the report, where it cannot be missed.
    block = Block("fast_input", "input", 5010, 25)
    said: list[str] = []
    blocks.report(
        Outcome(tally={block: {OK: 2, INCONSISTENT: 1}}, intermittent=[block]),
        echo=said.append,
    )
    text = "\n".join(said)
    assert "contention rather than a fault" in text
    assert "Re-run when nothing else is polling" in text


def _measure(stub, plan, **kwargs) -> Outcome:
    return asyncio.run(measure(stub.read, plan, reconnects=stub.counter, **kwargs))


def test_a_fault_fails_every_round_and_contention_moves() -> None:
    """The distinction `measure` exists to draw, over several rounds."""
    plan = [
        Block("fast_input", "input", 5010, 25),
        Block("grid_frequency", "input", 5241, 1),
    ]

    class Selective(Stub):
        """Answers everything except one address, which never answers."""

        async def read(self, space, address, count):
            self.reads += 1
            if address == 5241:
                raise IllegalDataAddressError(2)
            return [0] * count

    outcome = _measure(Selective(), plan, attempts=2, rounds=2)
    assert [block.component for block in outcome.failing] == ["grid_frequency"]
    assert outcome.intermittent == []
    # Narrowed to the one register, which is what goes into layout.ISOLATE.
    assert [(row[0].address, row[0].count) for row in outcome.culprits] == [(5241, 1)]


def test_a_block_that_answers_at_least_once_is_not_narrowed() -> None:
    """Bisecting contention wastes reads and invents a culprit."""
    outcome = _measure(
        Stub(IllegalDataAddressError(2), [0] * 25),
        [Block("fast_input", "input", 5010, 25)],
        attempts=2,
        rounds=1,
    )
    assert outcome.failing == [], "contention is not a register fault"
    assert outcome.culprits == [], "and must not be narrowed as one"
    assert [block.component for block in outcome.intermittent] == ["fast_input"]


def test_the_reconnects_are_carried_into_the_outcome() -> None:
    """The document says how often the raw socket reconnected."""
    outcome = _measure(
        Stub([0], reconnect_on=(2,)),
        [Block("fast_input", "input", 5010, 1)],
        attempts=2,
        rounds=1,
    )
    assert outcome.reconnects == 1


class _Slow(Stub):
    """A client whose every read fails, and takes time doing it.

    Which is the case the budget exists for. On a LAN a Sungrow refuses with
    exception 0x02 in milliseconds; over one VPN measured on 2026-09-09 the
    same refusal arrived as a 10-second timeout, so with three attempts a
    single read cost 30 seconds and narrowing one 15-register block cost a
    quarter of an hour.
    """

    def __init__(self, seconds: float = 10.0):
        super().__init__(ModbusTimeoutError("Response timeout after 10.0 seconds"))
        self._seconds = seconds
        self.clock = 0.0

    async def read(self, *args):
        # Charged per read, because that is what a timeout costs. `attempt`
        # makes `attempts` of them, so one verdict costs three times this.
        self.clock += self._seconds
        return await super().read(*args)


def _clocked(monkeypatch, client: _Slow) -> None:
    monkeypatch.setattr(block_test.time, "monotonic", lambda: client.clock)


def test_narrowing_stops_at_its_budget_and_says_which_ranges_it_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bound that keeps the cheapest phase from costing the whole survey.

    Four blocks like this one outran a survey's 25-minute cap and the run was
    killed before it wrote a document -- so an un-narrowed range has to come
    back marked, not dropped and not narrowed. The alternative that was
    considered and rejected is in `block_test.NARROW_BUDGET`: a per-block
    budget bounds each block and leaves the phase unbounded.
    """
    client = _Slow(seconds=30.0)
    _clocked(monkeypatch, client)

    outcome = _measure(
        client,
        [Block("firmware_block_battery", "input", 13279, 15)],
        attempts=3,
        rounds=1,
        narrow_budget=120.0,
    )

    assert [block.component for block in outcome.failing] == ["firmware_block_battery"]
    assert outcome.culprits, "the block failed, so something must be reported"
    # Four reads of 30s fit in 120s; a full narrowing of 15 registers is 29.
    assert client.reads < 29, "the budget did not bound anything"
    unnarrowed = [row for row in outcome.culprits if row[1] == UNNARROWED]
    assert unnarrowed, "a range the budget cut short must say so"
    for block, _kind, _detail in unnarrowed:
        assert block.count > 1, "a single register was reached, so it is an answer"


def _narrowing_reads(monkeypatch, plan, budget) -> tuple[int, set[str]]:
    """Return reads spent narrowing, and which blocks got any, for one run."""
    client = _Slow()
    _clocked(monkeypatch, client)
    outcome = _measure(client, plan, attempts=3, rounds=1, narrow_budget=budget)
    # The tally reads every block `attempts` times before narrowing begins.
    tally = 3 * len(plan)
    return client.reads - tally, {row[0].component for row in outcome.culprits}


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
        monkeypatch, [Block("firmware_block_battery", "input", 13279, 15)], 240.0
    )
    two, narrowed_two = _narrowing_reads(
        monkeypatch,
        [
            Block("meter_channel_2", "input", 13199, 8),
            Block("firmware_block_battery", "input", 13279, 15),
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
    outcome = _measure(
        Stub(IllegalDataAddressError(2)),
        [Block("firmware_block_battery", "input", 13279, 15)],
        attempts=1,
        rounds=1,
        narrow_budget=0,
    )
    assert all(row[0].count == 1 for row in outcome.culprits), (
        "unbounded narrowing reaches single registers"
    )
    assert UNNARROWED not in {row[1] for row in outcome.culprits}


def test_the_block_test_reads_only_the_inverters_own_components() -> None:
    """A regression that happened, and would have corrupted every survey.

    Adding the SBR's and the wallbox's components to the plan added eight
    blocks to the test, on unit ids the test does not use: input 10740 and
    21215 answer 0xFFFF or refuse at the inverter's unit whatever the pack and
    the charge point are doing. All eight would have failed, all eight would
    then have been narrowed at the cost of the narrowing budget, and all
    eight would have been offered to `src/sungrow_modbus/inverter/layout.py` as
    register faults.
    """
    from sungrow_modbus.addresses import device_components

    elsewhere = {
        name
        for device, components in device_components().items()
        if device != "inverter"
        for name in components
    }
    assert elsewhere, "the library should map components on other units"

    tested = {block.component for block in blocks._blocks_of(None)}
    assert not tested & elsewhere, (
        f"the block read test would read {sorted(tested & elsewhere)} at the "
        "inverter's unit id, where they cannot answer"
    )
    # Every polled inverter component is still tested, or the guard has gone
    # too far.
    from sungrow_modbus.inverter.registers import COMPONENTS

    assert {*COMPONENTS, "identity"} <= tested


def test_naming_another_devices_component_still_selects_it() -> None:
    """Excluded by default is not excluded outright.

    Somebody testing a pack's cell block against a real pack should be able
    to say so: `blocks.py <host> --unit 200 -c sbr_battery_cells`. The
    default is what had to change, not the capability.
    """
    selected = blocks._blocks_of("sbr_battery_cells")
    assert selected == [Block("sbr_battery_cells", "input", 10756, 8)], selected


def test_an_unknown_component_is_refused_with_the_known_ones() -> None:
    """A typo names what exists, rather than testing nothing."""
    with pytest.raises(SystemExit, match="fast_input"):
        blocks._blocks_of("no_such_component")


def test_a_failing_address_is_named_by_the_field_that_declares_it() -> None:
    """The library's own map names the register, or says nothing reads it."""
    assert declared("input", 4989).startswith("serial_number (in ")
    assert "nothing reads this" in declared("input", 39999)


def test_the_terminal_prints_each_read_where_the_caller_sends_it() -> None:
    """`echo` all the way down, narrowing included.

    `sungrow_survey.py` passes its transcript's `echo`; a line that went to
    stdout instead would be missing from the file a contributor keeps.
    """
    stub = Stub(IllegalDataAddressError(2))
    client = blocks.Client("stub", stub.read, stub.counter, _no_close)
    lines: list[str] = []
    outcome = asyncio.run(
        blocks.measure(
            client,
            [Block("fast_input", "input", 5241, 1)],
            attempts=1,
            rounds=1,
            echo=lines.append,
        )
    )
    assert outcome.culprits, "the block failed, so it was narrowed"
    assert any("fast_input" in line and "refused" in line for line in lines), lines
    # The narrowed range's own line is in the caller's sink, not on stdout.
    assert any(line.strip().startswith("input 5241 x1") for line in lines), lines


async def _no_close() -> None:
    """Nothing to close."""


def test_the_raw_client_only_knows_read_function_codes() -> None:
    """The survey's promise is that nothing it runs can write.

    `raw_client` builds its own frames, so the promise is checked on its
    source: the function codes it knows are 3 and 4, and nothing else.
    """
    source = Path(raw_client.__file__).read_text(encoding="utf-8")
    codes = {
        line.split("=")[1].strip()
        for line in source.splitlines()
        if line.startswith("_FC_") and "=" in line
    }
    assert codes == {"3", "4"}


async def _read_through(reply: bytes, count: int) -> list[int]:
    """Ask a local server that answers every request with `reply`."""

    async def handle(reader, writer):
        try:
            while await reader.readexactly(12):
                writer.write(reply)
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    client = raw_client.RawClient("127.0.0.1", port, 1, timeout=2.0)
    try:
        return await client.read("input", 2612, count)
    finally:
        await client.close()
        server.close()
        await server.wait_closed()


async def test_the_raw_client_reads_a_consistent_frame(socket_enabled: None) -> None:
    reply = bytes.fromhex("000100000007010404") + bytes.fromhex("00010002")
    assert await _read_through(reply, 2) == [1, 2]


async def test_the_raw_client_names_the_count_a_padded_frame_needs(
    socket_enabled: None,
) -> None:
    """The reference SH10RT at 2613: eleven declared, fifteen sent."""
    reply = bytes.fromhex("000100000021") + bytes([1, 4, 22]) + bytes(30)
    with pytest.raises(raw_client.PaddedFrame) as raised:
        await _read_through(reply, 11)
    assert raised.value.consistent_count == 15


async def test_the_raw_client_reports_an_exception_response_as_refused(
    socket_enabled: None,
) -> None:
    reply = bytes.fromhex("000100000003018402")
    with pytest.raises(raw_client.Refused) as raised:
        await _read_through(reply, 2)
    assert raised.value.exception_code == 2


def _finding(kind: str, detail: str, component="fast_input", through=False):
    outcome = Outcome(
        culprits=[(Block(component, "input", 2612, 15), kind, detail)],
    )
    (found,) = block_test.findings(outcome, through_module=through)
    return found


def test_a_padded_frame_is_layout_evidence_not_a_timeout() -> None:
    """The advice once read the detail's words and missed this one.

    A padded frame's detail says "declared 11 registers, frame sized for 15"
    -- none of the words the old check looked for -- so the case
    `layout.COUNTS` exists for was told "this failed by timing out, do not
    add it to layout.py".
    """
    detail = "3/3, declared 11 registers, frame sized for 15; ask for 15"
    assert _finding(PADDED, detail).advice is block_test.Advice.ISOLATE


def test_a_deterministic_hangup_is_evidence_and_a_timeout_is_not() -> None:
    assert _finding(DROPPED, "3/3, connection reset").advice is (
        block_test.Advice.ISOLATE
    )
    assert _finding(TIMED_OUT, "3/3, Response timeout").advice is (
        block_test.Advice.NOT_EVIDENCE
    )
    # A drop the link reported as a timeout is still the link.
    assert _finding(DROPPED, "3/3, timed out").advice is (
        block_test.Advice.NOT_EVIDENCE
    )


def test_a_refusal_through_a_dongle_may_be_a_forwarding_limit() -> None:
    assert _finding(REFUSED, "3/3, exception 0x02", through=True).advice is (
        block_test.Advice.FORWARDING_LIMIT
    )


def test_eight_refused_addresses_in_one_block_are_one_finding() -> None:
    outcome = Outcome(
        culprits=[
            (Block("meter", "input", address, 1), REFUSED, "3/3, exception 0x02")
            for address in range(13199, 13207)
        ],
    )
    (found,) = block_test.findings(outcome, through_module=False)
    assert found.registers == "13200-13207"
