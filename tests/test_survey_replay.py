"""A survey's `command_line` repeats it without asking a single question.

`sungrow_survey.py` takes a flag for every answer, skips any question whose
flag is given, and publishes the line that gives them all. The line used to
be the equivalent `probe.py capabilities ...`, which repeated the reading but
not the survey: it skipped the block read test, and it could not be handed
to the launcher a contributor actually runs.
"""

from __future__ import annotations

import argparse
import asyncio
import builtins
from pathlib import Path
import shlex
import sys

import pytest

SURVEY = Path(__file__).resolve().parents[1] / "device-survey" / "scripts" / "python"
sys.path.insert(0, str(SURVEY))

import probe  # noqa: E402
import sungrow_survey  # noqa: E402

SCRIPT = "python/sungrow_survey.py"

ANSWERED = [
    "<host>",
    "--unit",
    "2",
    "--pollers",
    "no",
    "--transport",
    "direct_lan",
    "--proxy",
    "no",
    "--other-inverter",
    "yes",
    "--other-inverter-detail",
    "Fronius Symo 8.2",
    "--address",
    "hidden",
    "--reporter",
    "somebody",
    "--comment",
    "the slave's reading",
    "--battery",
    "",
    "--control-test",
    "no",
]


def _answers(**overrides) -> argparse.Namespace:
    """Return the namespace `_ask_all` fills, as a run that answered everything."""
    values = {
        "host": "192.0.2.10",
        "port": 502,
        "unit": 2,
        "timeout": 10.0,
        "passes": 8,
        "pollers": "no",
        "transport": "direct_lan",
        "proxy": "no",
        "other_inverter": "yes",
        "other_inverter_detail": "Fronius Symo 8.2",
        "address": "hidden",
        "reporter": "somebody",
        "comment": "the slave's reading",
        "battery": "",
        "control_test": "no",
    }
    return argparse.Namespace(**{**values, **overrides})


def test_the_line_names_the_survey_and_hides_the_host() -> None:
    line = sungrow_survey.replay_command(_answers())

    assert "192.0.2.10" not in line
    words = shlex.split(line)
    assert words[:2] == [SCRIPT, "<host>"]


def test_the_line_parses_back_to_every_answer() -> None:
    """The round trip that matters: what was answered is what a replay gets."""
    line = sungrow_survey.replay_command(_answers())
    parsed = sungrow_survey._parser().parse_args(shlex.split(line)[1:])

    for name in (
        "unit",
        "pollers",
        "transport",
        "proxy",
        "other_inverter",
        "other_inverter_detail",
        "address",
        "reporter",
        "comment",
        "battery",
        "control_test",
    ):
        assert getattr(parsed, name) == getattr(_answers(), name), name


def test_an_empty_answer_is_still_given_so_it_is_not_asked() -> None:
    """An absent flag means "ask", so a blank comment has to be `--comment ''`."""
    words = shlex.split(sungrow_survey.replay_command(_answers(comment="", battery="")))

    assert words[words.index("--comment") + 1] == ""
    assert words[words.index("--battery") + 1] == ""


def test_shaping_flags_appear_only_away_from_their_defaults() -> None:
    plain = shlex.split(sungrow_survey.replay_command(_answers()))
    slow = shlex.split(
        sungrow_survey.replay_command(_answers(port=503, timeout=20.0, passes=3))
    )

    assert "--port" not in plain and "--timeout" not in plain
    assert slow[slow.index("--port") + 1] == "503"
    assert slow[slow.index("--timeout") + 1] == "20"
    assert slow[slow.index("--passes") + 1] == "3"


def test_no_detail_is_written_for_no_other_inverter() -> None:
    words = shlex.split(
        sungrow_survey.replay_command(
            _answers(other_inverter="no", other_inverter_detail="")
        )
    )

    assert "--other-inverter-detail" not in words


def test_a_copied_folder_names_the_script_alone(monkeypatch, tmp_path) -> None:
    copied = tmp_path / "sungrow_survey" / "sungrow_survey.py"
    copied.parent.mkdir()
    copied.write_text("")
    monkeypatch.setattr(sungrow_survey, "__file__", str(copied))

    assert sungrow_survey._script_name() == "sungrow_survey.py"


def test_with_every_flag_given_nothing_is_asked(monkeypatch) -> None:
    """The point of the line: a replay runs unattended."""

    def asked(*_args, **_kwargs):
        raise AssertionError("a question was asked")

    monkeypatch.setattr(builtins, "input", asked)
    for name in (
        "_ask",
        "_ask_yes",
        "_ask_menu",
        "_ask_about_pollers",
        "_ask_transport",
        "_ask_proxy",
        "_ask_other_inverter",
        "_ask_address",
        "_ask_battery",
    ):
        monkeypatch.setattr(probe, name, asked)

    args = sungrow_survey._parser().parse_args(["192.0.2.10", *ANSWERED[1:]])
    entry = sungrow_survey.Found("192.0.2.10", 502, 2, None)
    answers = asyncio.run(sungrow_survey._ask_all(entry, args, lambda *_: None))

    assert answers.command_line == shlex.join([SCRIPT, *ANSWERED]).replace(
        "'<host>'", "<host>"
    )
    assert answers.transport_given


def test_without_flags_every_question_is_asked(monkeypatch) -> None:
    """And the answers typed are the ones the line carries."""
    monkeypatch.setattr(probe, "_ask_about_pollers", lambda: "yes")
    monkeypatch.setattr(probe, "_ask_transport", lambda: "winet_wlan")
    monkeypatch.setattr(probe, "_ask_proxy", lambda: "unknown")
    monkeypatch.setattr(probe, "_ask_other_inverter", lambda: ("no", ""))
    monkeypatch.setattr(probe, "_ask_address", lambda _host: "two_octets")
    typed = iter(["1", "gerd", ""])
    monkeypatch.setattr(probe, "_ask", lambda *_a, **_k: next(typed))

    async def battery(*_args):
        return "Pylontech"

    monkeypatch.setattr(probe, "_ask_battery", battery)
    # At a terminal, so the control-test question is asked rather than
    # answered no for want of anybody to ask.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(probe, "_ask_yes", lambda *_a, **_k: True)

    args = sungrow_survey._parser().parse_args(["192.0.2.10"])
    entry = sungrow_survey.Found("192.0.2.10", 502, 1, None)
    answers = asyncio.run(sungrow_survey._ask_all(entry, args, lambda *_: None))

    words = shlex.split(answers.command_line)
    assert words == [
        SCRIPT,
        "<host>",
        "--address-tail",
        "002.010",
        "--unit",
        "1",
        "--pollers",
        "yes",
        "--transport",
        "winet_wlan",
        "--proxy",
        "unknown",
        "--other-inverter",
        "no",
        "--address",
        "two_octets",
        "--reporter",
        "gerd",
        "--comment",
        "",
        "--battery",
        "Pylontech",
        "--control-test",
        "yes",
    ]
    assert not answers.transport_given


@pytest.mark.parametrize("given", [True, False])
def test_a_transport_given_as_a_flag_is_kept_against_the_measurement(
    monkeypatch, given
) -> None:
    """A replay must not stop to ask; typed in, the question still comes."""
    asked = []

    def ask_yes(*_args, **_kwargs):
        asked.append(True)
        return True

    monkeypatch.setattr(probe, "_ask_yes", ask_yes)

    class _Refusing:
        async def close(self):
            return None

        def for_unit(self, _unit):
            return self

        read_input_registers = read_holding_registers = None

    monkeypatch.setattr(probe, "ModbusConnection", lambda *_a, **_k: _Refusing())

    async def refused(*_args, **_kwargs):
        raise probe.ModbusExceptionError(2)

    async def refused_6100(*_args, **_kwargs):
        return "refused"

    monkeypatch.setattr(sungrow_survey, "async_read_6100", refused_6100)

    async def closed(*_args):
        return False

    monkeypatch.setattr(probe, "_tcp_open", closed)

    # A cable answer, against a refused 6100 and a named module: a dongle.
    async def module(_unit):
        return "WINET-SV200"

    monkeypatch.setattr(sungrow_survey, "async_read_module", module)

    answers = _answers(transport="direct_lan", transport_given=given)
    entry = sungrow_survey.Found("192.0.2.10", 502, 1, None)
    asyncio.run(sungrow_survey._check_transport(entry, answers, lambda *_: None))

    if given:
        assert not asked
        assert answers.transport == "direct_lan"
    else:
        assert asked
        assert answers.transport == "winet"


def test_nobody_at_a_terminal_is_a_no(monkeypatch) -> None:
    """Leave to write is never assumed: a piped run does not run the test."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(probe, "_ask_yes", lambda *_a, **_k: pytest.fail("asked"))
    args = sungrow_survey._parser().parse_args(["192.0.2.10"])

    assert sungrow_survey._ask_control_test(args) == "no"


def test_the_question_defaults_to_no(monkeypatch) -> None:
    """Enter at the question must not give leave to restart somebody's inverter."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda *_a: "")
    args = sungrow_survey._parser().parse_args(["192.0.2.10"])

    assert sungrow_survey._ask_control_test(args) == "no"
