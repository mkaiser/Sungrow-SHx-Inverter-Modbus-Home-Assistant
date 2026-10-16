"""The Modbus backend's connection log stays off the terminal, and is counted.

`tmodbus` logs every connection it opens and every one the inverter drops,
and re-opens the link by itself. On a contended inverter that is a line every
few seconds -- "Async TCP connection lost due to error: [WinError 64] ..." --
in the middle of a run that is carrying on fine. Both terminal tools keep it
off the screen and say once, before the exit line, how often the link
dropped: that count is the useful part, because frequent drops mean another
client is polling the inverter.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "device-fingerprints" / "scripts" / "python"))

import sungrow_survey  # noqa: E402

CONTROL_TEST = (
    REPO / "device-fingerprints" / "scripts" / "python" / "sungrow_control_test.py"
)

#: What `tmodbus.transport.async_tcp` actually logs, at the levels it uses.
BACKEND_LINES = (
    (logging.INFO, "Async TCP connection established: 192.0.2.1:502"),
    (logging.ERROR, "Async TCP connection lost due to error: [WinError 64] gone"),
    (logging.INFO, "Async TCP connection closed by remote host."),
    (logging.INFO, "Modbus TCP protocol connection established."),
)


@pytest.fixture
def backend():
    """Yield the backend logger, and put `tmodbus` back the way it was."""
    logger = logging.getLogger("tmodbus")
    handlers, propagate = list(logger.handlers), logger.propagate
    yield logging.getLogger("tmodbus.transport.async_tcp")
    logger.handlers[:] = handlers
    logger.propagate = propagate


@pytest.fixture
def control_test():
    """Load the control test script as a module, the way it is run."""
    spec = importlib.util.spec_from_file_location("sungrow_control_test", CONTROL_TEST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _emit(logger: logging.Logger) -> None:
    for level, message in BACKEND_LINES:
        logger.log(level, message)


def test_the_survey_counts_drops_and_prints_none_of_them(backend, capsys) -> None:
    sungrow_survey._DROPS.count = 0
    sungrow_survey._quiet_backend()
    _emit(backend)

    captured = capsys.readouterr()
    assert "Async TCP" not in captured.out + captured.err
    assert sungrow_survey._DROPS.count == 2, "a loss and a close, not the opens"

    said: list[str] = []
    sungrow_survey._finish(0, said.append)
    assert "dropped the connection 2 time(s)" in said[0]
    assert said[-1].startswith("exit 0"), "the exit line stays last"
    sungrow_survey._DROPS.count = 0


def test_a_survey_without_drops_says_nothing_about_them() -> None:
    sungrow_survey._DROPS.count = 0
    said: list[str] = []
    sungrow_survey._finish(0, said.append)
    assert said == ["exit 0 -- " + sungrow_survey.CODES[0] + "."]


def test_the_control_test_counts_drops_and_prints_none_of_them(
    backend, control_test, capsys
) -> None:
    drops = control_test._quiet_backend()
    _emit(backend)

    captured = capsys.readouterr()
    assert "Async TCP" not in captured.out + captured.err
    assert drops.count == 2

    control_test._say_drops(drops)
    assert "dropped the connection 2 time(s)" in capsys.readouterr().err
