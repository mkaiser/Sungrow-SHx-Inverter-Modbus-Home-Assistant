"""The wallbox capability test's driver: consent, files, and what it never publishes.

`sungrow_wallbox_capability_test.py` is the terminal's side of
`sungrow_modbus.wallbox.capability_test`. What it adds is what a library has no
business doing: asking, writing files and choosing an exit code. These tests
drive it with the fake wallbox of `test_wallbox_capability_test.py`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from sungrow_modbus.wallbox import capability_test as wct

from .test_wallbox_capability_test import FakeClock, FakeWallbox

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "device-diagnosis"
    / "scripts"
    / "python"
    / "sungrow_wallbox_capability_test.py"
)
sys.path.insert(0, str(SCRIPT.parent))

#: An address that must never reach a file.
HOST = "192.168.178.23"


@pytest.fixture
def cli(tmp_path, monkeypatch):
    """Load the script as a module, writing its files under `tmp_path`."""
    spec = importlib.util.spec_from_file_location("sungrow_wallbox_ct", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_workspace", lambda: tmp_path)
    return module


def _args(cli, *argv: str):
    return cli._parser().parse_args([HOST, *argv])


async def test_without_leave_it_is_a_dry_run_that_writes_nothing(cli, tmp_path, capsys):
    box = FakeWallbox()
    code = await cli._run(_args(cli), box, FakeClock())

    assert code == 0
    assert box.writes == []
    assert "dry run" in capsys.readouterr().err
    assert not list(tmp_path.glob("*snapshot*"))


async def test_leave_with_nobody_at_a_terminal_is_a_no(cli, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    box = FakeWallbox()
    code = await cli._run(_args(cli, "--leave"), box, FakeClock())

    assert code == cli.CANCELLED
    assert box.writes == []
    assert "no --yes" in capsys.readouterr().err


async def test_a_declined_question_writes_nothing(cli, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    box = FakeWallbox()
    code = await cli._run(_args(cli, "--leave"), box, FakeClock())

    assert code == cli.CANCELLED
    assert box.writes == []


async def test_a_run_with_leave_restores_and_keeps_no_address(cli, tmp_path):
    box = FakeWallbox()
    code = await cli._run(_args(cli, "--leave", "--yes"), box, FakeClock())

    assert code == 0
    assert box.holding == box.original
    # The snapshot did its job and is gone; the report is what is left.
    assert not list(tmp_path.glob("*snapshot*"))
    (report,) = tmp_path.glob("*-wallbox-capability-test.json")
    text = report.read_text()
    assert HOST not in text
    document = json.loads(text)
    assert document["document"] == "wallbox_capability_test"
    assert document["code"] == 0
    assert document["leave"] is True


async def test_the_snapshot_is_on_disk_before_the_first_write(cli, tmp_path):
    """Seen from inside the first write: the file is already there."""
    box = FakeWallbox()
    seen: list[bool] = []
    real_write = box.write

    async def write(address: int, word: int) -> None:
        seen.append(bool(list(tmp_path.glob("*-wallbox-snapshot.json"))))
        await real_write(address, word)

    box.write = write  # type: ignore[method-assign]
    await cli._run(_args(cli, "--leave", "--yes"), box, FakeClock())

    assert seen
    assert seen[0] is True


async def test_a_run_that_cannot_restore_keeps_its_snapshot_and_exits_5(cli, tmp_path):
    box = FakeWallbox(restore_fails=True)
    code = await cli._run(_args(cli, "--leave", "--yes"), box, FakeClock())

    assert code == 5
    assert list(tmp_path.glob("*-wallbox-snapshot.json"))


async def test_restore_mode_puts_a_saved_snapshot_back(cli, tmp_path):
    box = FakeWallbox()
    box.holding[wct.OUTPUT_CURRENT] = 100  # left behind by a run that died
    saved = tmp_path / "snapshot.json"
    saved.write_text(
        json.dumps(
            {
                "raw": {str(wct.OUTPUT_CURRENT): 160},
                "touched": [wct.OUTPUT_CURRENT],
            }
        )
    )
    args = _args(cli, "--restore", str(saved))
    code = await cli._run(args, box, FakeClock())

    assert code == 0
    assert box.holding[wct.OUTPUT_CURRENT] == 160


def test_the_address_is_required(cli):
    with pytest.raises(SystemExit):
        cli.main([])


def test_the_default_cap_is_the_librarys(cli):
    assert _args(cli).max_amps == wct.DEFAULT_MAX_AMPS
    assert _args(cli).leave is False
