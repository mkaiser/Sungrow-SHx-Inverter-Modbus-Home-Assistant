"""The Modbus backend's connection log stays off the terminal, and is counted.

`tmodbus` logs every connection it opens and every one the inverter drops,
and re-opens the link by itself. On a contended inverter that is a line every
few seconds -- "Async TCP connection lost due to error: [WinError 64] ..." --
in the middle of a run that is carrying on fine. Both terminal tools keep it
off the screen and say once, before the exit line, how often the link
dropped; the diagnosis's document records the count, because it is the useful
part: frequent drops usually mean another client is polling the inverter.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "device-diagnosis" / "scripts" / "python"))

import probe  # noqa: E402
import sungrow_diagnosis  # noqa: E402

CAPABILITY_TEST = (
    REPO / "device-diagnosis" / "scripts" / "python" / "sungrow_capability_test.py"
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
    """Yield the backend logger, and put `tmodbus` and the counter back."""
    logger = logging.getLogger("tmodbus")
    handlers, propagate = list(logger.handlers), logger.propagate
    installed = probe.LINK_DROPS.installed
    probe.LINK_DROPS.count = 0
    yield logging.getLogger("tmodbus.transport.async_tcp")
    logger.handlers[:] = handlers
    logger.propagate = propagate
    probe.LINK_DROPS.installed = installed
    probe.LINK_DROPS.count = 0


@pytest.fixture
def capability_test():
    """Load the capability test script as a module, the way it is run."""
    spec = importlib.util.spec_from_file_location(
        "sungrow_capability_test", CAPABILITY_TEST
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _emit(logger: logging.Logger) -> None:
    for level, message in BACKEND_LINES:
        logger.log(level, message)


def test_the_diagnosis_counts_drops_and_prints_none_of_them(backend, capsys) -> None:
    probe.LINK_DROPS.installed = False
    probe.count_link_drops()
    _emit(backend)

    captured = capsys.readouterr()
    assert "Async TCP" not in captured.out + captured.err
    assert probe.LINK_DROPS.count == 2, "a loss and a close, not the opens"

    said: list[str] = []
    sungrow_diagnosis._finish(0, said.append)
    assert "dropped the connection 2 time(s)" in said[0]
    # Not only "something else is polling": a port can drop on its own.
    assert "drops by itself" in said[0]
    assert said[-1].startswith("exit 0"), "the exit line stays last"


def test_a_diagnosis_without_drops_says_nothing_about_them(backend) -> None:
    said: list[str] = []
    sungrow_diagnosis._finish(0, said.append)
    assert said == ["exit 0 -- " + sungrow_diagnosis.CODES[0] + "."]


def test_the_document_records_the_drops_only_when_counted(backend) -> None:
    """None is not zero: a document says 0 only when somebody counted."""
    connection = {"verdict": "direct to the inverter's LAN port"}
    probe.LINK_DROPS.installed = False
    assert probe.with_link_drops(connection) == connection

    probe.count_link_drops()
    _emit(backend)
    assert probe.with_link_drops(connection) == {**connection, "link_drops": 2}
    assert "link_drops" not in connection, "the measured section is not mutated"


def test_the_capability_test_counts_drops_and_prints_none_of_them(
    backend, capability_test, capsys
) -> None:
    probe.LINK_DROPS.installed = False
    drops = capability_test.probe.count_link_drops()
    _emit(backend)

    captured = capsys.readouterr()
    assert "Async TCP" not in captured.out + captured.err
    assert drops.count == 2

    capability_test._say_drops(drops)
    assert "dropped the connection 2 time(s)" in capsys.readouterr().err
