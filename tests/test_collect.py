"""The one entry point: `scripts/sungrow_scan/collect.py`.

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
import re
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
SCAN = REPO / "scripts" / "sungrow_scan"
sys.path.insert(0, str(SCAN))

import blocks  # noqa: E402
import collect  # noqa: E402
import probe  # noqa: E402


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
        _function(SCAN / "collect.py", "_ask_all"), "answers"
    ) | _attributes_set(_function(SCAN / "collect.py", "_survey"), "answers")

    assert needed - filled == set(), (
        f"collect.py never sets {sorted(needed - filled)}, which capabilities() reads"
    )


def test_every_exit_code_has_a_sentence() -> None:
    """The last line prints the code *and* what it means: `$?` is lost in a paste."""
    assert set(collect.CODES) == set(collect.SEVERITY)
    for code, sentence in collect.CODES.items():
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
    assert collect._worst(codes) == expected


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
    assert collect._ranges(numbers) == expected


def test_the_private_file_is_not_hidden_outside_a_checkout(
    tmp_path, monkeypatch
) -> None:
    """The hazard a run from an unpacked zip actually produced.

    In the checkout the un-redacted reading belongs in `.testdata/`, which is
    gitignored. Anywhere else, a *hidden* directory holding somebody's serial
    and address -- created inside the folder they were told to send back --
    is how a private file gets forwarded by accident.
    """
    monkeypatch.chdir(tmp_path)
    assert probe._raw_dir() == probe.PRIVATE_DIR
    assert not probe._raw_dir().name.startswith(".")
    documents, private, in_checkout = collect._workspace()
    assert (documents, private, in_checkout) == (tmp_path, tmp_path, False)

    (tmp_path / ".git").mkdir()
    (tmp_path / "scripts").mkdir()
    assert probe._raw_dir() == tmp_path / probe.RAW_DIR
    assert collect._workspace() == (
        tmp_path / ".testdata" / "fingerprints",
        tmp_path / ".testdata",
        True,
    )


def test_a_run_from_inside_the_checkout_still_writes_to_testdata(
    tmp_path, monkeypatch
) -> None:
    """The defect a real run produced, from the obvious directory.

    Both `_workspace` and `_raw_dir` asked whether the **current** directory
    was a checkout. Run from `scripts/sungrow_scan/` -- which is where the
    zip's README tells people to run it, and where a maintainer naturally is
    -- they concluded "unpacked zip" and wrote the document into the source
    tree. `.gitignore` covered the private reading and the transcript; the
    document it did not, so it sat there waiting for the next `git add`.

    Both now ask one function, which walks up.
    """
    (tmp_path / ".git").mkdir()
    (tmp_path / "scripts" / "sungrow_scan").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "scripts" / "sungrow_scan")

    documents, private, in_checkout = collect._workspace()
    assert in_checkout
    assert documents == tmp_path / ".testdata" / "fingerprints"
    assert private == tmp_path / ".testdata"
    # And the private reading lands beside it rather than in the source tree.
    assert probe._raw_dir() == tmp_path / probe.RAW_DIR
    assert "scripts" not in probe._raw_dir().parts


def test_a_directory_that_merely_looks_like_a_checkout_is_not_one(
    tmp_path, monkeypatch
) -> None:
    """`.git` alone is not enough, and neither is a `scripts` directory.

    A contributor who unpacked the zip into some other project's checkout
    would otherwise have their reading filed in that project's `.testdata`.
    """
    (tmp_path / "scripts").mkdir()
    monkeypatch.chdir(tmp_path)
    assert collect._workspace()[2] is False
    assert probe._checkout_root() is None


#: A document shaped like a real one, with the two values that must never
#: reach a summary: the address it was read from and the real serial.
HOST = "192.168.178.114"
SERIAL = "A123456789"
DOCUMENT = {
    "schema": probe.SCHEMA,
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


def _rendered() -> str:
    """Render the summary for one made-up device and return what it printed."""
    written = [Path("doc/device-fingerprints/sh80rt-v112-3p-someone-aa2678.json")]
    result = collect.Outcome(
        found=collect.Found(HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")),
        unit=1,
        document=DOCUMENT,
        written=written,
        transport=collect.Transport(
            True, None, "direct to the inverter's LAN port", False
        ),
        reported_transport="direct_lan",
        block_outcome=None,
        code=0,
    )
    buffer = io.StringIO()
    collect._summary([result], Path(".testdata/sungrow-scan-x.log"), buffer.write)
    return buffer.getvalue()


def test_the_summary_carries_no_address_and_no_real_serial() -> None:
    """Paste-safety as a property, not a hope.

    The summary is written to be pasted into an issue, so it has to be as
    safe as the document it renders -- and it is rendered from that document
    for exactly this reason. The `Found` it is given holds the real host and
    the real serial, so a lapse would show up here.
    """
    text = _rendered()
    assert SERIAL not in text
    assert HOST not in text
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text), (
        "a dotted quad is somebody's network"
    )
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


def test_a_summary_says_which_file_to_send_and_which_to_keep() -> None:
    """The contributor's next action, and the one thing they must not do."""
    text = _rendered()
    assert "send this" in text
    assert "keep this" in text


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        ("direct to the inverter's LAN port", "scripts/layout.py"),
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
    result = collect.Outcome(
        found=collect.Found(HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")),
        unit=1,
        document=DOCUMENT,
        written=[Path("x.json")],
        transport=collect.Transport(False, "WINET-SV200", verdict, True),
        reported_transport="winet_wlan",
        block_outcome=collect.blocks.BlockOutcome(
            tally={}, intermittent=[], failing=[], culprits=[culprit], reconnects=0
        ),
        code=0,
    )
    lines: list[str] = []
    collect._summary_actions(result, lines.append)
    text = " ".join(lines)
    assert expected in text
    # The evidence travels with the advice, either way.
    assert "2629-2643" in text


def _with_blocks(outcome: blocks.BlockOutcome) -> str:
    """Render the summary for a device whose block read test found something.

    Whitespace is collapsed before returning. The advice is wrapped at 68
    columns so it survives being pasted into an issue, and `echo` here is a
    bare `write` -- so a phrase straddling a wrap arrives with the indent
    inside it, which failed two assertions in this file against text that was
    perfectly correct.
    """
    result = collect.Outcome(
        found=collect.Found(HOST, 502, 1, probe.Identity(SERIAL, 0x0E0E, "SH8.0RT")),
        unit=1,
        document=DOCUMENT,
        written=[Path("doc/device-fingerprints/sh80rt-v112-3p-someone-aa2678.json")],
        transport=collect.Transport(
            True, None, "direct to the inverter's LAN port", False
        ),
        reported_transport="direct_lan",
        block_outcome=outcome,
        code=0,
    )
    buffer = io.StringIO()
    collect._summary([result], Path(".testdata/sungrow-scan-x.log"), buffer.write)
    return " ".join(buffer.getvalue().split())


def _outcome(*culprits) -> blocks.BlockOutcome:
    """Return a BlockOutcome holding just the findings a test cares about."""
    failing = [
        (name, space, address, count)
        for name, space, address, count, _k, _d in culprits
    ]
    return blocks.BlockOutcome(
        tally={key: {} for key in failing},
        intermittent=[],
        failing=failing,
        culprits=list(culprits),
        reconnects=0,
    )


def test_an_already_isolated_block_is_not_offered_to_layout_again() -> None:
    """The nine recommendations that were all already done.

    Measured at fwitten on 2026-09-09: four blocks failed and all four were
    the four entries `layout.ISOLATE` already holds, from that same house two
    days earlier. The summary printed nine numbered recommendations to add
    them, and the isolation was in fact *working* -- each failure cost one
    field instead of a whole tier, which is the outcome that module exists
    for. `layout.py` is not in the zip, so the fact travels in
    `scan_plan.json` as `isolated` on the component.
    """
    text = _with_blocks(
        _outcome(
            (
                "firmware_block_inverter",
                "input",
                13249,
                1,
                blocks.REFUSED,
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
                blocks.REFUSED,
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
                blocks.UNNARROWED,
                "narrowing ran out of time here",
            )
        )
    )
    assert "not yet an answer" in text
    assert "names no single register" in text
    # And the command that finishes it, which is the only useful next step.
    assert "-r input:13282:13" in text
    assert "--narrow-budget 0" in text
    assert "scripts/layout.py" not in text


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
                blocks.REFUSED,
                "3/3, read_input_registers(13200, 1): Response timeout after "
                "10.0 seconds for transaction with ID 0x01",
            )
        )
    )
    assert "timing out rather than by refusing" in text
    assert "do not add it to scripts/layout.py" in text
    assert "fails fast" in text
    assert "this is the device refusing" not in text


def test_the_advice_survives_a_plan_it_could_not_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """By summary time the documents are written; nothing may take it down.

    The plan is only needed for the "already isolated" half of one sentence,
    and a summary is the last thing owed to whoever sat through the scan.
    """
    monkeypatch.setattr(
        collect.portable,
        "load_plan",
        lambda: (_ for _ in ()).throw(RuntimeError("no plan here")),
    )
    text = _with_blocks(
        _outcome(
            (
                "fast_input",
                "input",
                5241,
                1,
                blocks.REFUSED,
                "3/3, Modbus Exception 0x02 for function code 0x04",
            )
        )
    )
    assert "What this scan found" in text
    assert "Add the field(s) these belong to" in text


def test_the_sweep_looks_at_the_ihomemanager_ports() -> None:
    """Three ports, and each one means a different device.

    502 is where nearly everything answers. 503 is where a Logger lives and
    where an iHomeManager is **documented** -- neither has ever answered on
    any network this project has surveyed. 516 is the one added last, from
    other people's work rather than from a reading.
    """
    ports = {port for port, _means, _readable in collect.SWEEP_PORTS}
    assert ports == {502, 503, 516}

    readable = {port for port, _means, readable in collect.SWEEP_PORTS if readable}
    assert readable == {502, 503}, (
        "516 carries Modbus over TLS, so a plain socket meets a handshake "
        "where it expects an MBAP header -- it can be found and not read"
    )
    # Each port says what it means, because a list of numbers explains
    # nothing to somebody deciding whether to wait for three sweeps.
    for port, means, _readable in collect.SWEEP_PORTS:
        assert means.strip(), port
        assert not means.startswith(str(port)), "the number is printed already"


def test_a_port_that_cannot_be_read_is_reported_rather_than_dropped() -> None:
    """The finding, and it is a finding rather than a warning.

    Measured: 516 on a WiNet-S is Modbus over TLS and it works, so a user
    told there is nothing there would be told something false. What the
    survey cannot do is read it, having no TLS client -- and the message says
    which of those two it means.
    """
    collect._UNREADABLE.clear()
    collect._UNREADABLE.append(("192.0.2.7", 516))
    try:
        buffer = io.StringIO()
        collect._summary_unreadable(buffer.write)
        text = " ".join(buffer.getvalue().split())
    finally:
        collect._UNREADABLE.clear()

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
    collect._UNREADABLE.clear()
    buffer = io.StringIO()
    collect._summary_unreadable(buffer.write)
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
    assert collect.ROUNDS > 1, (
        "one round is the measurement least able to tell contention from a "
        "fault, and it is the one this survey was using"
    )
    # Six reads per block either way, spread rather than bunched.
    assert collect.ROUNDS * collect.ATTEMPTS == 6
    assert collect.ATTEMPTS >= 2, (
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
    failing = [("meter_channel_2", "input", 13199, 8)]
    intermittent = [("fast_input", "input", 5010, 25)]
    answered = [("realtime_input", "input", 12999, 10)]
    outcome = blocks.BlockOutcome(
        tally={k: {blocks.REFUSED: 3} for k in failing}
        | {k: {blocks.OK: 2, blocks.INCONSISTENT: 1} for k in intermittent}
        | {k: {blocks.OK: 3} for k in answered},
        intermittent=intermittent,
        failing=failing,
        culprits=[
            (
                "meter_channel_2",
                "input",
                13200,
                1,
                blocks.REFUSED,
                "3/3, Modbus Exception 0x02 for function code 0x04",
            )
        ],
        reconnects=0,
    )
    collect._CLIENT_LABEL[:] = ["modbus-connection (the one the integration uses)"]
    document = collect._block_document(outcome)
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
    assert document["rounds"] == collect.ROUNDS
    assert document["attempts"] == collect.ATTEMPTS
    assert "modbus-connection" in document["client"]


def test_a_run_without_a_block_test_says_so_by_absence() -> None:
    """Absent, not empty.

    An empty section would say the test ran and found nothing, which is a
    different claim from its not having run at all.
    """
    assert collect._block_document(None) is None


def test_the_block_document_carries_no_address_and_no_serial() -> None:
    """It is published, so it is held to the same rule as everything else."""
    import re

    outcome = blocks.BlockOutcome(
        tally={("fast_input", "input", 5010, 25): {blocks.OK: 3}},
        intermittent=[],
        failing=[],
        culprits=[],
        reconnects=1,
    )
    collect._CLIENT_LABEL[:] = ["this directory's own client -- nothing installed"]
    text = json.dumps(collect._block_document(outcome))

    assert SERIAL not in text
    assert HOST not in text
    assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", text), (
        "a dotted quad is somebody's network"
    )
