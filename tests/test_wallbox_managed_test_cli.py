"""The managed wallbox test's driver: consent, files, and the exit code.

`sungrow_managed_wallbox_test.py` is the terminal's side of
`sungrow_modbus.wallbox.managed_test`, driven here with the fake house of
`test_wallbox_managed_test.py`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from sungrow_modbus.hybrid_inverter import ev_charger as ev

from .test_wallbox_capability_test import FakeClock
from .test_wallbox_managed_test import FakeHouse, WallboxSide

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "device-diagnosis"
    / "scripts"
    / "python"
    / "sungrow_managed_wallbox_test.py"
)
sys.path.insert(0, str(SCRIPT.parent))

#: An address that must never reach a file.
HOST = "10.0.0.17"


@pytest.fixture
def cli(tmp_path, monkeypatch):
    """Load the script as a module, writing its files under `tmp_path`."""
    spec = importlib.util.spec_from_file_location("sungrow_managed_wt", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_workspace", lambda: tmp_path)
    return module


def _args(cli, *argv: str):
    return cli._parser().parse_args([HOST, *argv])


async def _go(cli, house: FakeHouse, *argv: str) -> int:
    return await cli._run(_args(cli, *argv), house, WallboxSide(house), FakeClock())


async def test_without_leave_it_is_a_dry_run_that_writes_nothing(cli, tmp_path, capsys):
    house = FakeHouse()
    code = await _go(cli, house)

    assert code == 0
    assert house.writes == []
    assert "dry run" in capsys.readouterr().err
    assert not list(tmp_path.glob("*snapshot*"))


async def test_leave_with_nobody_at_a_terminal_is_a_no(cli, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    house = FakeHouse()
    code = await _go(cli, house, "--leave")

    assert code == cli.CANCELLED
    assert house.writes == []


async def test_a_run_puts_the_house_back_and_keeps_no_address(cli, tmp_path):
    house = FakeHouse()
    code = await _go(cli, house, "--leave", "--yes", "--start-stop")

    assert code == 0
    assert house.block == house.original
    assert house.session
    assert not list(tmp_path.glob("*snapshot*"))
    (report,) = tmp_path.glob("*-managed-wallbox-capability-test.json")
    text = report.read_text()
    assert HOST not in text
    data = json.loads(text)
    assert data["restored"] is True
    assert {step["verdict"] for step in data["steps"]} == {"the car did as it was told"}


async def test_a_house_not_put_back_keeps_its_snapshot_and_exits_5(
    cli, tmp_path, capsys
):
    house = FakeHouse(sleeps_after_stop=True)
    code = await _go(cli, house, "--leave", "--yes", "--start-stop", "--no-floor")

    assert code == 5
    (snapshot,) = tmp_path.glob("*-managed-wallbox-snapshot.json")
    assert json.loads(snapshot.read_text())["raw"][str(ev.MODE)] == ev.FAST
    assert "NOT PUT BACK" in capsys.readouterr().err


async def test_restore_puts_a_saved_snapshot_back(cli, tmp_path):
    house = FakeHouse()
    # A run that died in user-defined mode at 6 A, the charge still on.
    await house.write(ev.MODE, ev.USER_DEFINED)
    await house.write(ev.USER_CURRENT, 60)
    saved = tmp_path / "x-managed-wallbox-snapshot.json"
    saved.write_text(
        json.dumps(
            {
                "raw": {
                    str(ev.CHARGING): ev.ON,
                    str(ev.MODE): ev.FAST,
                    str(ev.USER_CURRENT): 160,
                },
                "charging_at_start": True,
                "touched": [ev.MODE, ev.USER_CURRENT],
            }
        )
    )
    code = await _go(cli, house, "--restore", str(saved))

    assert code == 0
    assert house.block[ev.MODE] == ev.FAST
    assert house.block[ev.USER_CURRENT] == 160
    assert house.session
