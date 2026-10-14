"""Folding a write result into a published fingerprint, from the terminal.

`scripts/sungrow_control_test/sungrow_control_test.py --merge-into` edits a document in
`doc/device-fingerprints/`, which is public. So the merge is held to two
things: it never publishes what identifies a house, and the document's schema
number keeps saying what the document can carry.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from modbus_connection.mock import MockModbusUnit
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


def test_a_run_writes_beside_itself(cli, tmp_path, monkeypatch) -> None:
    """Beside the launcher, whatever folder the run was started from."""
    monkeypatch.chdir(tmp_path)
    assert cli._workspace() == SCRIPT.parent


# -- the snapshot: written before the first write, gone once all is back ------


class _Clock:
    """Advance instead of waiting, so a ten-minute budget costs no time."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds


class _Connection:
    async def close(self) -> None:
        pass


def _args(**overrides) -> argparse.Namespace:
    values = {
        "host": "192.0.2.10",
        "port": 502,
        "unit": 1,
        "timeout": 1.0,
        "dry_run": False,
        "allow_dark": False,
        "enable_export_limit": False,
        "restart": False,
        "start_only": False,
        "restart_only": False,
        "export_scale": False,
        "simulated": True,
        "restore": None,
        "merge_into": None,
    }
    return argparse.Namespace(**{**values, **overrides})


@pytest.fixture
def wired(cli, monkeypatch, tmp_path, sungrow_unit: MockModbusUnit):
    """Point `_run` at a mock inverter and a temporary folder.

    Returns a list the snapshot paths are recorded in as they are written, so a
    test can tell "never written" from "written and then removed".
    """
    sungrow_unit.input[5621] = 0
    sungrow_unit.input[5622] = 1000
    sungrow_unit.input[5627] = 50

    async def connect(*_args):
        return _Connection(), sungrow_unit

    written: list[Path] = []

    class Recording(cli.ControlTest):
        def __init__(self, *args, on_snapshot=None, **kwargs):
            async def record(snapshot):
                await on_snapshot(snapshot)
                written.extend(tmp_path.glob("*-snapshot.json"))

            super().__init__(
                *args,
                clock=_Clock(),
                on_snapshot=None if on_snapshot is None else record,
                **kwargs,
            )

    monkeypatch.setattr(cli, "_connect", connect)
    monkeypatch.setattr(cli, "_workspace", lambda: tmp_path)
    monkeypatch.setattr(cli, "ControlTest", Recording)
    return written


async def test_a_clean_run_removes_its_snapshot(cli, wired, tmp_path) -> None:
    code = await cli._run(_args())

    assert code != 5
    assert wired, "the snapshot is written before the first write"
    assert not list(tmp_path.glob("*-snapshot.json"))
    assert list(tmp_path.glob("*-control_test.json"))


async def test_a_run_that_left_something_keeps_its_snapshot(
    cli, wired, tmp_path, monkeypatch, capsys
) -> None:
    """The snapshot is the way out, so it stays until the house is back."""
    original = cli.ControlTest

    class Stubborn(original):
        async def async_run(self):
            outcome = await super().async_run()
            stuck = outcome.restores[0]._replace(restored=False)
            return outcome._replace(code=5, restores=(stuck, *outcome.restores[1:]))

    monkeypatch.setattr(cli, "ControlTest", Stubborn)

    code = await cli._run(_args())

    assert code == 5
    (snapshot,) = tmp_path.glob("*-snapshot.json")
    assert f"--restore {snapshot}" in capsys.readouterr().err


async def test_a_dry_run_never_writes_a_snapshot(cli, wired, tmp_path) -> None:
    await cli._run(_args(dry_run=True))

    assert not wired
    assert not list(tmp_path.glob("*-snapshot.json"))


async def test_a_dry_run_does_not_claim_its_checks_ran(cli, wired, tmp_path) -> None:
    """A dry run's 0 says "the plan resolved", never "every check ran".

    Measured: a dry run against a real inverter printed "every planned check
    ran and every readback matched (exit 0)" over a table of "not run" rows.
    """
    import json

    from sungrow_modbus import control_test

    assert cli.DRY_RUN_MEANS == control_test.DRY_RUN_MEANS
    code = await cli._run(_args(dry_run=True))

    assert code == 0
    (result,) = tmp_path.glob("*-control_test.json")
    document = json.loads(result.read_text())
    assert document["outcome_means"] == control_test.DRY_RUN_MEANS
    assert cli._means(0, True) == control_test.DRY_RUN_MEANS
    assert cli._means(0, False) == control_test.CODES[0]
