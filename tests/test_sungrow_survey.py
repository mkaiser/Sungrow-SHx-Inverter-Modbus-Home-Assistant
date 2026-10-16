"""The one entry point: `device-fingerprints/scripts/python/sungrow_survey.py`.

Its failure modes are not the interesting kind. It asks eight questions, runs
four phases and writes three files, so what goes wrong is that one answer is
never asked for and the run dies at the save step -- after a minute of
reading somebody was walked through -- or that the summary it prints carries
something the document deliberately does not.

Both are checked here without a device and without a prompt: the first by
reading the code, the second by rendering a summary from a document made up
for the purpose.
"""

from __future__ import annotations

import ast
import io
import json
from pathlib import Path
import sys

import pytest

from sungrow_modbus import block_test
from sungrow_modbus.fingerprint import SCHEMA, collected_nothing

REPO = Path(__file__).resolve().parent.parent
SCAN = REPO / "device-fingerprints" / "scripts" / "python"
sys.path.insert(0, str(SCAN))

import blocks  # noqa: E402
import probe  # noqa: E402
import sungrow_survey  # noqa: E402

from .corpus import INVERTER_DOCUMENTS  # noqa: E402


def _function(path: Path, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Return one top-level function's syntax tree."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == name
        ):
            return node
    raise AssertionError(f"{path.name} has no {name}")


def _attributes_read(node: ast.AST, variable: str) -> set[str]:
    """Return every `<variable>.<name>` read anywhere inside a function."""
    found = set()
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name)
            and child.value.id == variable
            and isinstance(child.ctx, ast.Load)
        ):
            found.add(child.attr)
    return found


def _attributes_set(node: ast.AST, variable: str) -> set[str]:
    """Return every `<variable>.<name>` assigned, plus keyword arguments.

    Two ways the wizard fills its Namespace: `answers.transport = ...` and
    `argparse.Namespace(host=..., port=...)`. Both count, and missing either
    would make this test pass while the run breaks.
    """
    found = set()
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Attribute)
            and isinstance(child.value, ast.Name)
            and child.value.id == variable
            and isinstance(child.ctx, ast.Store)
        ):
            found.add(child.attr)
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "Namespace"
        ):
            found.update(keyword.arg for keyword in child.keywords if keyword.arg)
    return found


def test_the_wizard_answers_everything_the_reading_asks_for() -> None:
    """Every `args.x` in `capabilities` must be set before it is called.

    The failure this prevents is the expensive one: `capabilities` reads
    fourteen attributes off the namespace it is handed, and the last of them
    is only touched at the save step. A forgotten answer is therefore an
    `AttributeError` after a full minute of reading, on somebody else's
    inverter, with nothing written.
    """
    needed = _attributes_read(_function(SCAN / "probe.py", "capabilities"), "args")
    filled = _attributes_set(
        _function(SCAN / "sungrow_survey.py", "_ask_all"), "answers"
    ) | _attributes_set(_function(SCAN / "sungrow_survey.py", "_survey"), "answers")

    assert needed - filled == set(), (
        f"sungrow_survey.py never sets {sorted(needed - filled)}, "
        "which capabilities() reads"
    )


def test_every_exit_code_has_a_sentence() -> None:
    """The last line prints the code *and* what it means: `$?` is lost in a paste."""
    assert set(sungrow_survey.CODES) == set(sungrow_survey.SEVERITY)
    for code, sentence in sungrow_survey.CODES.items():
        assert sentence and not sentence.endswith("."), code


@pytest.mark.parametrize(
    ("codes", "expected"),
    [
        ([0, 0], 0),
        ([0, 3], 3),
        ([3, 4], 4),
        ([4, 1], 1),
        ([1, 2], 2),
        # The ordering numeric `max` gets wrong, which is why there is a table.
        ([2, 4], 2),
        ([3, 0, 4], 4),
        ([], 1),
    ],
)
def test_several_devices_exit_the_worst_severity_not_the_highest_number(
    codes, expected
) -> None:
    """`max()` on the codes would call 4 worse than 2, and 2 is worse."""
    assert sungrow_survey._worst(codes) == expected


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([13200, 13201, 13202], "13200-13202"),
        ([5242], "5242"),
        ([2640, 2641, 2700], "2640-2641, 2700"),
    ],
)
def test_consecutive_registers_are_reported_as_a_range(numbers, expected) -> None:
    """Eight comma-separated numbers hide whether they are contiguous."""
    assert block_test.register_ranges(numbers) == expected


@pytest.mark.parametrize("start", ["root", "folder", "elsewhere"])
def test_a_run_writes_beside_the_script_from_any_directory(
    tmp_path, monkeypatch, start
) -> None:
    """One place, whoever started it and from where.

    `make scan` runs from the repository root, the launchers `cd` into their
    folder, and somebody else types `python` from wherever they are. All three
    land beside the launcher, under visible names -- never in a hidden
    directory, which is how a private file gets forwarded by accident.
    """
    here = Path(sungrow_survey.__file__).resolve().parents[2]
    monkeypatch.chdir(
        {
            "root": here.parent,
            "folder": here / "scripts" / "python",
            "elsewhere": tmp_path,
        }[start]
    )
    assert sungrow_survey._workspace() == (here, here)
    assert here == probe.HERE


#: A document shaped like a real one, with the two values that must never
#: reach a summary: the address it was read from and the real serial.
HOST = "192.168.178.114"
SERIAL = "A123456789"
DOCUMENT = {
    "schema": SCHEMA,
    "user_inputs": {
        "reporter": "someone",
        "transport": "direct_lan",
        "modbus_proxy": "no",
        "comment": "",
    },
    "ip_address_last_two_octets": "178.114",
    "device": {
        "device_type_code": "0x0E0E",
        "output_type": "three phase 3P4L",
        "serial_anonymized_hashed": "anon-00267885816",
    },
    "readings": {
        "values": {"total_dc_power": 4200, "battery_level": None},
        "components_that_did_not_answer": ["battery_firmware"],
    },
}


def _rendered(control_code: int | None = None) -> str:
    """Render the summary for one made-up device and return what it printed."""
    written = [Path("device-fingerprints/sh80rt-v112-3p-someone-aa2678.json")]
    result = sungrow_survey.Outcome(
        found=sungrow_survey.Found(
            HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")
        ),
        unit=1,
        document=DOCUMENT,
        written=written,
        transport=sungrow_survey.Transport(
            True, None, "direct to the inverter's LAN port", False
        ),
        reported_transport="direct_lan",
        block_outcome=None,
        code=0,
        control_code=control_code,
    )
    buffer = io.StringIO()
    sungrow_survey._summary(
        [result], Path(".testdata/sungrow-scan-x.log"), buffer.write
    )
    return buffer.getvalue()


def test_the_summary_carries_the_control_address_but_no_real_serial() -> None:
    """The local control command may include the address, but not the serial.

    The control command is intentionally executable against the device just
    surveyed. The fingerprint document and the survey transcript retain their
    separate privacy boundaries.
    """
    text = _rendered()
    assert SERIAL not in text
    assert HOST in text
    # And the redacted forms it should carry instead.
    assert "178.114" in text
    assert "anon-00267885816" in text


def test_the_summary_separates_what_was_read_from_what_was_said() -> None:
    """Three markers, so a claim is never read as a reading."""
    text = _rendered()
    assert "  read  model" in text
    assert "  said  transport" in text
    assert "  n/a   wired or WiFi" in text
    # The testimony block names its source rather than presenting it as fact.
    assert "Told to this run, not measured" in text
    assert "said  reporter         someone" in text


def test_a_summary_without_the_control_test_says_how_to_run_it_later() -> None:
    """Declined, the contributor gets the one-launcher line, not a private path."""
    text = _rendered()
    assert "Survey has been written to" in text
    assert "The control test did not run" in text
    assert "./survey.sh control" in text
    assert "--merge-into" in text
    assert "sungrow-scan-" not in text


def test_a_summary_after_the_control_test_says_what_it_found() -> None:
    from sungrow_modbus.control_test import CODES

    text = _rendered(control_code=4)
    assert CODES[4] in text
    assert "./survey.sh control" not in text


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        ("direct to the inverter's LAN port", "src/sungrow_modbus/inverter/layout.py"),
        (
            "through a communication module (WiNet-S, WiNet-S2 or Logger)",
            "forwarding limit",
        ),
    ],
)
def test_a_refusal_is_advised_on_differently_per_transport(verdict, expected) -> None:
    """The same refusal means different things over a cable and over a dongle.

    Measured on gerd's SH8.0RT-V112: input 2612 and 2628 refuse three times
    out of three through its WiNet-S and read perfectly over the inverter's
    own LAN port four minutes later. Advising `layout.ISOLATE` for that would
    make every direct-LAN user pay a per-field read for a dongle's behaviour,
    and would still leave a dongle user without the fields.
    """
    culprit = (
        "battery_firmware",
        "input",
        2628,
        15,
        "refused with an exception",
        "3/3",
    )
    result = sungrow_survey.Outcome(
        found=sungrow_survey.Found(
            HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")
        ),
        unit=1,
        document=DOCUMENT,
        written=[Path("x.json")],
        transport=sungrow_survey.Transport(False, "WINET-SV200", verdict, True),
        reported_transport="winet_wlan",
        block_outcome=_outcome(culprit),
        code=0,
    )
    lines: list[str] = []
    sungrow_survey._summary_actions(result, lines.append)
    text = " ".join(lines)
    assert expected in text
    # The evidence travels with the advice, either way.
    assert "2629-2643" in text


def _with_blocks(outcome: block_test.Outcome) -> str:
    """Render the summary for a device whose block read test found something.

    Whitespace is collapsed before returning. The advice is wrapped at 68
    columns so it survives being pasted into an issue, and `echo` here is a
    bare `write` -- so a phrase straddling a wrap arrives with the indent
    inside it, which failed two assertions in this file against text that was
    perfectly correct.
    """
    result = sungrow_survey.Outcome(
        found=sungrow_survey.Found(
            HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")
        ),
        unit=1,
        document=DOCUMENT,
        written=[Path("device-fingerprints/sh80rt-v112-3p-someone-aa2678.json")],
        transport=sungrow_survey.Transport(
            True, None, "direct to the inverter's LAN port", False
        ),
        reported_transport="direct_lan",
        block_outcome=outcome,
        code=0,
    )
    buffer = io.StringIO()
    sungrow_survey._summary(
        [result], Path(".testdata/sungrow-scan-x.log"), buffer.write
    )
    return " ".join(buffer.getvalue().split())


def _outcome(*culprits) -> block_test.Outcome:
    """Return an Outcome holding just the findings a test cares about.

    Each culprit is (component, space, address, count, outcome, detail).
    """
    rows = [
        (block_test.Block(name, space, address, count), kind, detail)
        for name, space, address, count, kind, detail in culprits
    ]
    failing = [block for block, _kind, _detail in rows]
    return block_test.Outcome(
        tally={block: {} for block in failing},
        failing=failing,
        culprits=rows,
    )


def test_an_already_isolated_block_is_not_offered_to_layout_again() -> None:
    """The nine recommendations that were all already done.

    Measured at fwitten on 2026-09-09: four blocks failed and all four were
    the four entries `layout.ISOLATE` already holds, from that same house two
    days earlier. The summary printed nine numbered recommendations to add
    them, and the isolation was in fact *working* -- each failure cost one
    field instead of a whole tier, which is the outcome that module exists
    for. The summary reads `layout.ISOLATE` to tell the two apart.
    """
    text = _with_blocks(
        _outcome(
            (
                "firmware_block_inverter",
                "input",
                13249,
                1,
                block_test.REFUSED,
                "3/3, Modbus Exception 0x02 for function code 0x04",
            )
        )
    )
    assert "already isolated" in text
    assert "nothing to do" in text
    assert "Add the field(s) these belong to" not in text, (
        "it is already there; saying so again is the bug"
    )


def test_a_block_that_is_not_yet_isolated_still_gets_the_recommendation() -> None:
    """The guard must not silence the case the tool exists for."""
    text = _with_blocks(
        _outcome(
            (
                "fast_input",
                "input",
                5241,
                1,
                block_test.REFUSED,
                "3/3, Modbus Exception 0x02 for function code 0x04",
            )
        )
    )
    assert "Add the field(s) these belong to" in text
    assert "already isolated" not in text


def test_a_range_the_budget_cut_short_is_not_offered_as_a_register() -> None:
    """`layout.py` takes an exact register, and this is not one yet."""
    text = _with_blocks(
        _outcome(
            (
                "firmware_block_battery",
                "input",
                13282,
                13,
                block_test.UNNARROWED,
                "narrowing ran out of time here",
            )
        )
    )
    assert "not yet an answer" in text
    assert "names no single register" in text
    # And the command that finishes it, which is the only useful next step.
    assert "-r input:13282:13" in text
    assert "--narrow-budget 0" in text
    assert "src/sungrow_modbus/inverter/layout.py" not in text


def test_a_timeout_only_failure_is_not_evidence_about_the_register() -> None:
    """The caveat written into layout.py this morning, enforced in the advice.

    Every entry in `ISOLATE` is an exception code, a deterministic hangup or
    a padded frame. A timeout is none of those: at fwitten the same four
    blocks closed the connection on a LAN on 2026-09-07 and timed out over a
    VPN on 2026-09-09 -- same registers, same machines. So the sentence is
    the link's and only a refusal is the device's.
    """
    text = _with_blocks(
        _outcome(
            (
                "meter_channel_2",
                "input",
                13200,
                1,
                block_test.REFUSED,
                "3/3, read_input_registers(13200, 1): Response timeout after "
                "10.0 seconds for transaction with ID 0x01",
            )
        )
    )
    assert "timing out rather than by refusing" in text
    assert "do not add it to src/sungrow_modbus/inverter/layout.py" in text
    assert "fails fast" in text
    assert "this is the device refusing" not in text


def test_the_sweep_looks_at_the_ihomemanager_ports() -> None:
    """Three ports, and each one means a different device.

    502 is where nearly everything answers. 503 is where a Logger lives and
    where an iHomeManager is **documented** -- neither has ever answered on
    any network this project has surveyed. 516 is the one added last, from
    other people's work rather than from a reading.
    """
    ports = {port for port, _means, _readable in sungrow_survey.SWEEP_PORTS}
    assert ports == {502, 503, 516}

    readable = {
        port for port, _means, readable in sungrow_survey.SWEEP_PORTS if readable
    }
    assert readable == {502, 503}, (
        "516 carries Modbus over TLS, so a plain socket meets a handshake "
        "where it expects an MBAP header -- it can be found and not read"
    )
    # Each port says what it means, because a list of numbers explains
    # nothing to somebody deciding whether to wait for three sweeps.
    for port, means, _readable in sungrow_survey.SWEEP_PORTS:
        assert means.strip(), port
        assert not means.startswith(str(port)), "the number is printed already"


def test_a_port_that_cannot_be_read_is_reported_rather_than_dropped() -> None:
    """The finding, and it is a finding rather than a warning.

    Measured: 516 on a WiNet-S is Modbus over TLS and it works, so a user
    told there is nothing there would be told something false. What the
    survey cannot do is read it, having no TLS client -- and the message says
    which of those two it means.
    """
    sungrow_survey._UNREADABLE.clear()
    sungrow_survey._UNREADABLE.append(("192.0.2.7", 516))
    try:
        buffer = io.StringIO()
        sungrow_survey._summary_unreadable(buffer.write)
        text = " ".join(buffer.getvalue().split())
    finally:
        sungrow_survey._UNREADABLE.clear()

    assert "192.0.2.7:516" in text
    assert "cannot read" in text
    assert "TLS" in text
    # And it says the port is not a fault, which is what measurement showed:
    # on a WiNet-S 516 works and serves the same registers as 502.
    assert "not a fault" in text


def test_nothing_is_said_when_every_port_could_be_read() -> None:
    """Silence about what did not happen, which is the house style here.

    A section headed "answered a port this tool cannot read" on every scan
    that found nothing of the kind would train people to skip it.
    """
    sungrow_survey._UNREADABLE.clear()
    buffer = io.StringIO()
    sungrow_survey._summary_unreadable(buffer.write)
    assert buffer.getvalue() == ""


def test_the_survey_uses_rounds_and_not_only_attempts() -> None:
    """The weaker of the two measurements was the one being used.

    Attempts are back-to-back reads of one block; rounds go round the whole
    plan and come back. Contention correlates in time, so three attempts can
    all land inside one busy moment and be filed as a deterministic fault --
    which is what happened at a house where Home Assistant was still polling,
    and it produced nine recommendations to change the register map.

    A poller like that is not a moment but a state: the fastest tier polls
    every five seconds indefinitely. Rounds, with the other blocks in
    between, are what tell the two apart -- and `blocks.py`'s own help has
    said so all along.
    """
    assert sungrow_survey.ROUNDS > 1, (
        "one round is the measurement least able to tell contention from a "
        "fault, and it is the one this survey was using"
    )
    # Six reads per block either way, spread rather than bunched.
    assert sungrow_survey.ROUNDS * sungrow_survey.ATTEMPTS == 6
    assert sungrow_survey.ATTEMPTS >= 2, (
        "a single attempt cannot see an intermittent block at all"
    )


def test_the_block_read_test_reaches_the_published_document() -> None:
    """The measurement layout.py is changed from has to be in the file.

    For a whole schema it was not. It lived in the transcript, and the
    transcript is the file a contributor is told to **keep** rather than
    send, because it carries their real address -- so a submitted document
    had no block evidence in it at all and a maintainer could not see which
    of the integration's reads that device would fail.
    """
    Block = block_test.Block
    failing = [Block("meter_channel_2", "input", 13199, 8)]
    intermittent = [Block("fast_input", "input", 5010, 25)]
    answered = [Block("realtime_input", "input", 12999, 10)]
    outcome = block_test.Outcome(
        tally={k: {block_test.REFUSED: 3} for k in failing}
        | {k: {block_test.OK: 2, block_test.INCONSISTENT: 1} for k in intermittent}
        | {k: {block_test.OK: 3} for k in answered},
        intermittent=intermittent,
        failing=failing,
        culprits=[
            (
                Block("meter_channel_2", "input", 13200, 1),
                block_test.REFUSED,
                "3/3, Modbus Exception 0x02 for function code 0x04",
            )
        ],
    )
    document = sungrow_survey._block_document(
        outcome, "modbus-connection (the one the integration uses)"
    )
    assert document is not None

    # The three lists are kept apart, because confusing them is how a wrong
    # fix gets committed: a fault belongs in layout.py and contention does not.
    assert [row["component"] for row in document["never_answered"]] == [
        "meter_channel_2"
    ]
    assert [row["component"] for row in document["intermittent"]] == ["fast_input"]
    assert [row["component"] for row in document["answered"]] == ["realtime_input"]

    # Register **numbers**, not protocol addresses, because everything a
    # person reads in this project is a register number.
    assert document["never_answered"][0]["register"] == 13200
    assert document["narrowed"][0]["register"] == 13201

    # How it was measured, since that decides what it means.
    assert document["rounds"] == sungrow_survey.ROUNDS
    assert document["attempts"] == sungrow_survey.ATTEMPTS
    assert "modbus-connection" in document["client"]


def test_a_run_without_a_block_test_says_so_by_absence() -> None:
    """Absent, not empty.

    An empty section would say the test ran and found nothing, which is a
    different claim from its not having run at all.
    """
    assert sungrow_survey._block_document(None) is None


def test_the_block_document_carries_no_address_and_no_serial() -> None:
    """It is published, so it is held to the same rule as everything else."""
    import re

    outcome = block_test.Outcome(
        tally={block_test.Block("fast_input", "input", 5010, 25): {block_test.OK: 3}},
        reconnects=1,
    )
    text = json.dumps(sungrow_survey._block_document(outcome, blocks.LIBRARY_LABEL))

    assert SERIAL not in text
    assert HOST not in text
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text), (
        "a dotted quad is somebody's network"
    )


def _answering(monkeypatch: pytest.MonkeyPatch, *answers: str) -> list[str]:
    """Feed `probe._ask` the given answers in turn; return what was echoed."""
    queue = list(answers)
    monkeypatch.setattr(
        probe, "_ask", lambda question, default="": queue.pop(0) or default
    )
    monkeypatch.setattr(probe, "_default_network", lambda: "192.168.178.0/24")
    return []


@pytest.mark.parametrize("typo", ["192.168.3", "192.168.178.300/24", "home"])
def test_a_network_that_cannot_be_swept_is_asked_again(
    monkeypatch: pytest.MonkeyPatch, typo: str
) -> None:
    echoed = _answering(monkeypatch, typo, "192.168.178.3/24")
    assert sungrow_survey._ask_network(echoed.append) == "192.168.178.3/24"
    assert any("is not a network" in line for line in echoed)


def test_a_network_too_large_to_sweep_is_asked_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    echoed = _answering(monkeypatch, "10.0.0.0/8", "")
    assert sungrow_survey._ask_network(echoed.append) == "192.168.178.0/24"
    assert any("over the limit" in line for line in echoed)


def test_an_address_with_a_part_missing_is_asked_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The resolver would read 192.168.3 as 192.168.0.3 and connect there.
    echoed = _answering(monkeypatch, "192.168.3", "192.168.178.3")
    assert sungrow_survey._ask_host(echoed.append) == "192.168.178.3"
    assert any("not a whole address" in line for line in echoed)


@pytest.mark.parametrize("typed", ["", "inverter.local", "192.168.178.3"])
def test_a_hostname_or_a_whole_address_or_nothing_is_taken_as_typed(
    monkeypatch: pytest.MonkeyPatch, typed: str
) -> None:
    _answering(monkeypatch, typed)
    assert sungrow_survey._ask_host(lambda line: None) == typed


def test_a_run_that_read_nothing_exits_1_not_3() -> None:
    """A document of nothing is "nothing was collected", not a thin document.

    Measured: a VPN that went away before the first read left every field
    missing, and the run exited 3 -- "the filename under-claims" -- with the
    empty file announced as the one to send.
    """
    from types import SimpleNamespace

    empty = {
        "readings": {"values": {"device_type_code": None}},
        "register_dump": {"input": {"4999": None}, "holding": {}},
    }
    reading = probe.Reading({}, {}, empty, [], ["device_type_code"])
    answers = SimpleNamespace(transport="direct_lan")

    assert sungrow_survey._code_for(reading, None, answers) == 1


@pytest.mark.parametrize(
    "path",
    INVERTER_DOCUMENTS,
    ids=lambda path: path.stem,
)
def test_no_published_document_counts_as_collecting_nothing(path: Path) -> None:
    """The guard must never fire on a real reading, however thin."""
    assert not collected_nothing(json.loads(path.read_text()))


@pytest.mark.parametrize(
    ("error", "state"),
    [
        ("IllegalDataAddressError", "refused"),
        ("ModbusTimeoutError", "no answer"),
        ("ModbusConnectionError", "no answer"),
        ("ModbusDesyncError", "no answer"),
    ],
)
def test_only_an_exception_response_is_published_as_refused(error, state) -> None:
    """A lost link is "no answer", never "refused".

    Measured: a VPN that dropped mid-run printed every capability probe as
    "refused (ModbusConnectionError)" -- a claim about the device that only
    the device can make.
    """
    import modbus_connection

    kind = getattr(modbus_connection, error)
    err = kind(2) if error == "IllegalDataAddressError" else kind("lost")
    from sungrow_modbus.survey import failure_state

    assert failure_state(err) == state


def test_a_6100_nobody_answered_decides_no_route() -> None:
    """With 6100 unanswered, the verdict claims nothing and contradicts no one.

    Measured: the same lost link read 6100 as refused, the verdict became a
    dongle, and the survey offered the owner of a cable to change a correct
    answer to match it.
    """
    from sungrow_modbus.fingerprint import TRANSPORT_NOT_DETERMINED

    verdict = TRANSPORT_NOT_DETERMINED
    from sungrow_modbus.fingerprint import claim_of

    assert claim_of(verdict) is None
    document = {
        "device": {"device_type_code": "0x0E0F"},
        "connection": {"verdict": verdict},
        "user_inputs": {},
    }
    from sungrow_modbus.fingerprint import label_for

    assert not label_for(document).endswith(("winet", "logger"))


@pytest.mark.parametrize(
    ("direct_url", "says"),
    [
        (None, "1.2.3, the PyPI package"),
        (
            '{"url": "file:///src/tree", "dir_info": {"editable": true}}',
            "1.2.3 from the source /src/tree -- NOT a release",
        ),
        (
            '{"url": "file:///dist/x.whl", "archive_info": {}}',
            "1.2.3 from the wheel /dist/x.whl -- NOT a release",
        ),
    ],
)
def test_the_preamble_says_whether_the_library_is_a_release(
    monkeypatch, direct_url, says
) -> None:
    """Tell a local library from the published one by where it came from.

    A tree carries the version of the release it is heading for, so the
    version cannot; where the installer says it came from can.
    """
    import importlib.metadata

    class Dist:
        version = "1.2.3"

        def read_text(self, name: str) -> str | None:
            return direct_url if name == "direct_url.json" else None

    monkeypatch.setattr(importlib.metadata, "distribution", lambda _name: Dist())
    assert sungrow_survey._library() == says


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        # The replay line carries both; the host given outright is used.
        (["192.168.178.35", "--address-tail", "178.035"], ["192.168.178.35"]),
        # A tail that names another device is refused, not mixed in.
        (["192.168.178.36", "--address-tail", "178.035"], None),
        # A tail alone is rebuilt on the local prefix, and says so.
        (["--address-tail", "178.035"], ["10.1.178.35"]),
    ],
)
def test_a_host_given_outright_wins_over_the_address_tail(
    monkeypatch, capsys, argv, expected
) -> None:
    """The local prefix is a guess, and in a container it is the bridge's.

    `--address-tail 178.035` beside `192.168.178.35` once sent a whole survey
    to `172.17.178.35`: the tail replaced the host, rebuilt on the Docker
    bridge's prefix. The survey prints both in its own replay line.
    """
    seen: list[list[str]] = []

    async def fake_run(args) -> int:
        seen.append(args.host)
        return 0

    monkeypatch.setattr(sys, "argv", ["sungrow_survey.py", *argv])
    monkeypatch.setattr(sungrow_survey, "run", fake_run)
    monkeypatch.setattr(probe, "local_ipv4_for", lambda target: "10.1.2.3")

    code = sungrow_survey.main()

    if expected is None:
        assert code == 2
        assert not seen
        assert "does not match" in capsys.readouterr().out
    else:
        assert code == 0
        assert seen == [expected]


class _Reading:
    def __init__(self, written: list[Path]) -> None:
        self.document = DOCUMENT
        self.written = written
        self.missing: list[str] = []


@pytest.fixture
def surveyed(monkeypatch, tmp_path):
    """Run `_survey` with every phase before the control test stubbed out.

    Returns the control test's calls, as the parsed arguments it was handed.
    """
    document = tmp_path / "doc.json"
    document.write_text("{}")
    calls: list = []
    result = {"code": 0}

    async def ask_all(entry, args, echo):
        answers = sungrow_survey.argparse.Namespace(
            host=entry.host,
            port=entry.port,
            unit=entry.unit,
            timeout=10.0,
            transport="direct_lan",
            control_test=args.control_test,
        )
        return answers

    async def check_transport(*_args):
        return None

    async def block_test(*_args):
        return None

    async def capabilities(_answers):
        return _Reading([document])

    async def control(args, _drops):
        calls.append(args)
        return result["code"]

    async def no_sleep(_seconds):
        pass

    monkeypatch.setattr(sungrow_survey, "_ask_all", ask_all)
    monkeypatch.setattr(sungrow_survey, "_check_transport", check_transport)
    monkeypatch.setattr(sungrow_survey, "_block_test", block_test)
    monkeypatch.setattr(sungrow_survey.probe, "capabilities", capabilities)
    monkeypatch.setattr(sungrow_survey.sungrow_control_test, "async_main", control)
    monkeypatch.setattr(sungrow_survey.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(sungrow_survey, "_workspace", lambda: (tmp_path, tmp_path))

    async def run(*flags: str, code: int = 0):
        result["code"] = code
        args = sungrow_survey._parser().parse_args([HOST, *flags])
        entry = sungrow_survey.Found(HOST, 502, 1, None)
        return await sungrow_survey._survey(entry, args, lambda *_: None)

    return run, calls, document


async def test_a_declined_control_test_never_starts(surveyed) -> None:
    run, calls, _document = surveyed
    outcome = await run("--control-test", "no")

    assert not calls
    assert outcome.control_code is None


async def test_leave_given_runs_everything_the_question_named(surveyed) -> None:
    """One yes is the restart and the export-limit lift, and no second prompt."""
    run, calls, document = surveyed
    outcome = await run("--control-test", "yes", code=4)

    (args,) = calls
    assert args.host == HOST
    assert args.restart is True
    assert args.enable_export_limit is True
    assert args.allow_dark is True
    assert args.yes is True
    assert args.dry_run is False
    assert args.merge_into == str(document)
    assert outcome.control_code == 4
    # A decade finding is a result about the inverter, not about the scan.
    assert outcome.code == 0


async def test_a_house_left_changed_is_the_surveys_exit_code(surveyed) -> None:
    run, _calls, _document = surveyed
    outcome = await run("--control-test", "yes", code=5)

    assert outcome.code == 5
    assert sungrow_survey._worst([0, 4, 5, 1]) == 5


async def test_a_simulator_gets_no_restart(surveyed) -> None:
    run, calls, _document = surveyed
    await run("--control-test", "yes", "--simulated")

    (args,) = calls
    assert args.simulated is True
    assert args.restart is False


def test_control_hands_the_rest_to_the_control_test(monkeypatch) -> None:
    """The one launcher reaches the restore, the way out of exit 5."""
    handed: list = []
    monkeypatch.setattr(
        sungrow_survey.sungrow_control_test,
        "main",
        lambda argv: handed.append(argv) or 0,
    )

    assert sungrow_survey.main(["control", HOST, "--restore", "x.json"]) == 0
    assert handed == [[HOST, "--restore", "x.json"]]


def test_a_reset_connection_is_not_printed_and_anything_else_still_is() -> None:
    """Windows reports a peer's reset during close as a loop error.

    `[WinError 10054]` printed a traceback in the middle of identification
    that changed nothing and read as a failure. Only that is kept quiet: any
    other error the loop reports still reaches the default handler.
    """
    seen: list[dict] = []

    class Loop:
        def default_exception_handler(self, context: dict) -> None:
            seen.append(context)

    loop = Loop()
    reset = {"message": "_call_connection_lost", "exception": ConnectionResetError()}
    other = {"message": "something else", "exception": RuntimeError()}
    probe._ignore_resets(loop, reset)
    probe._ignore_resets(loop, other)
    assert seen == [other]


def test_the_scripts_run_with_the_handler_installed() -> None:
    """`probe.run` returns the coroutine's result, with the handler set."""
    import asyncio

    async def handler_in_place() -> object:
        return asyncio.get_running_loop().get_exception_handler()

    assert probe.run(handler_in_place()) is probe._ignore_resets
