"""Folding a write result into a published fingerprint, from the terminal.

`scripts/sungrow_control_test/sungrow_control_test.py --merge-into` edits a document in
`doc/device-fingerprints/`, which is public. So the merge is held to two
things: it never publishes what identifies a house, and the document's schema
number keeps saying what the document can carry.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from sungrow_modbus import export_scale
from sungrow_modbus.export_scale import Result
from sungrow_modbus.fingerprint import SCHEMA

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "sungrow_control_test"
    / "sungrow_control_test.py"
)


@pytest.fixture(scope="module")
def cli():
    """Load the script as a module, the way it is run."""
    spec = importlib.util.spec_from_file_location("sungrow_control_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _block() -> dict:
    return export_scale.document(
        Result(
            1,
            "this firmware stores a written word as handed",
            held=11880,
            wrote=11880,
            response="accepted",
        )
    )


def _document(tmp_path: Path, schema: int) -> Path:
    path = tmp_path / "fingerprint.json"
    path.write_text(json.dumps({"schema": schema, "device": {}}))
    return path


def test_an_export_scale_block_stamps_the_schema_that_admits_it(cli, tmp_path):
    """A document carrying the block claims the number that defines it."""
    path = _document(tmp_path, SCHEMA - 1)

    cli._merge(path, "export_scale", _block(), "A123456789", "192.0.2.10")

    document = json.loads(path.read_text())
    assert document["schema"] == SCHEMA
    assert document["export_scale"]["write_units_per_count"] == 1
    assert document["export_scale"]["answer"] == "stores a written word as handed"


def test_a_document_too_old_for_the_number_is_refused(cli, tmp_path):
    """Stamping 20 on a document from before 19 would claim fields it lacks."""
    path = _document(tmp_path, SCHEMA - 2)
    before = path.read_text()

    with pytest.raises(SystemExit, match="too old"):
        cli._merge(path, "export_scale", _block(), "A123456789", "192.0.2.10")

    assert path.read_text() == before


def test_a_control_test_block_leaves_the_schema_alone(cli, tmp_path):
    """`control_test` has been admitted since 19; merging it changes no claim."""
    path = _document(tmp_path, SCHEMA - 1)

    cli._merge(path, "control_test", {"schema": 2}, "A123456789", "192.0.2.10")

    assert json.loads(path.read_text())["schema"] == SCHEMA - 1


def test_a_block_carrying_the_serial_is_never_written(cli, tmp_path):
    """The block is anonymous by construction; the merge checks anyway."""
    path = _document(tmp_path, SCHEMA - 1)
    block = {**_block(), "reason": "read A123456789"}

    with pytest.raises(SystemExit, match="serial"):
        cli._merge(path, "export_scale", block, "A123456789", "192.0.2.10")

    assert "A123456789" not in path.read_text()


# -- the two prompts before the first write ----------------------------------


def _at_a_terminal(monkeypatch, cli, answers: list[str | type[BaseException]]):
    """Make the script believe a person is typing these answers."""
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    queue = list(answers)

    def typed(_prompt: str = "") -> str:
        answer = queue.pop(0)
        if isinstance(answer, type):
            raise answer
        return answer

    monkeypatch.setattr("builtins.input", typed)


def test_the_restart_is_asked_as_a_permission(cli, monkeypatch, capsys) -> None:
    prompts: list[str] = []
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        "builtins.input", lambda prompt="": prompts.append(prompt) or "y"
    )

    assert cli._ask_restart(None) is True
    assert "Do you permit the test to stop and restart the inverter?" in prompts[0]
    # The measured times, not the guess that was there before measuring.
    assert "3 to 4 minutes" in capsys.readouterr().err


def test_enter_starts_the_run(cli, monkeypatch) -> None:
    _at_a_terminal(monkeypatch, cli, [""])
    assert cli._ready(dry_run=False) is True


@pytest.mark.parametrize("stop", [KeyboardInterrupt, EOFError])
def test_cancelling_at_the_last_prompt_writes_nothing(
    cli, monkeypatch, capsys, stop
) -> None:
    _at_a_terminal(monkeypatch, cli, [stop])
    assert cli._ready(dry_run=False) is False
    assert "Nothing was written" in capsys.readouterr().err


def test_nobody_at_a_terminal_is_not_waited_for(cli, monkeypatch) -> None:
    """A scripted run answers the questions with flags and goes ahead."""
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked anyway"))
    assert cli._ready(dry_run=False) is True
    assert cli._ask_restart(None) is False


def test_a_run_writes_where_the_read_only_survey_writes(cli) -> None:
    """One folder for both tools' results, so nobody has to look in two."""
    import sys

    sys.path.insert(0, str(SCRIPT.parents[1] / "sungrow_read_only_survey"))
    import sungrow_survey

    survey_documents, _transcripts, in_checkout = sungrow_survey._workspace()
    assert in_checkout, "the test suite runs inside the checkout"
    assert cli._workspace() == survey_documents
