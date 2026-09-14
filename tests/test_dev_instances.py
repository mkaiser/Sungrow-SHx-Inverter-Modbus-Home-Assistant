"""The two helpers the boot scripts run before Home Assistant starts.

Both are dev tooling, and both are now in the path of `make dev` and
`make hacs` -- so a bug in either is a dev instance that will not come up,
found at the worst moment. These tests cover the parts that decide something:
which onboarding steps are outstanding, and what gets written into the HTTP
store.

Nothing here starts Home Assistant or touches a real config directory.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parent.parent


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


onboard = _load("ha_onboard")
http_port = _load("ha_http_port")


def _store(port: int, *, pending: dict[str, object] | None = None) -> dict[str, object]:
    """Build a `.storage/http` document shaped the way Home Assistant writes one."""
    return {
        "version": http_port.VERSION,
        "minor_version": http_port.MINOR_VERSION,
        "key": "http",
        "data": {
            "stable": {**http_port.DEFAULTS, "server_port": port, "error": None},
            "pending": pending,
            "yaml_migration_done": True,
        },
    }


def _write(tmp_path: Path, document: dict[str, object]) -> Path:
    storage = tmp_path / ".storage"
    storage.mkdir(parents=True, exist_ok=True)
    (storage / "http").write_text(json.dumps(document), encoding="utf-8")
    return tmp_path


# --- which onboarding steps are left -------------------------------------


def test_a_fresh_instance_needs_every_step_in_order():
    status = [{"step": step, "done": False} for step in onboard.ORDER]
    assert onboard.remaining(status) == list(onboard.ORDER)


def test_the_account_comes_first_because_the_rest_need_its_token():
    assert (
        onboard.remaining(
            [{"step": "analytics", "done": False}, {"step": "user", "done": False}]
        )[0]
        == "user"
    )


def test_a_finished_instance_needs_nothing():
    assert onboard.remaining([{"step": s, "done": True} for s in onboard.ORDER]) == []


def test_a_step_this_script_cannot_drive_is_left_alone():
    """A future Home Assistant may add one; guessing at it is worse than not."""
    assert onboard.remaining([{"step": "quantum_tunnel", "done": False}]) == []


# --- what goes into the HTTP store ---------------------------------------


def test_the_port_is_written_and_the_pending_config_cleared(tmp_path, capsys):
    """Pending is what arms the five-minute revert, so it must not survive."""
    config = _write(tmp_path, _store(8123, pending={"server_port": 9999}))
    assert http_port.pin(config, 8124) == 0

    data = json.loads((config / ".storage" / "http").read_text())["data"]
    assert data["stable"]["server_port"] == 8124
    assert data["pending"] is None
    assert data["stable"]["error"] is None
    assert "8123 -> 8124" in capsys.readouterr().out


def test_other_settings_survive(tmp_path):
    document = _store(8123)
    document["data"]["stable"]["ip_ban_enabled"] = False
    document["data"]["stable"]["cors_allowed_origins"] = ["https://example.invalid"]
    config = _write(tmp_path, document)

    http_port.pin(config, 8124)

    stable = json.loads((config / ".storage" / "http").read_text())["data"]["stable"]
    assert stable["ip_ban_enabled"] is False
    assert stable["cors_allowed_origins"] == ["https://example.invalid"]


def test_pinning_twice_changes_nothing(tmp_path, capsys):
    config = _write(tmp_path, _store(8124))
    assert http_port.pin(config, 8124) == 0
    assert "already pinned" in capsys.readouterr().out


def test_an_unrecognised_schema_is_refused_rather_than_forced(tmp_path, capsys):
    """A mangled store is a Home Assistant that cannot serve anything."""
    document = _store(8123)
    document["minor_version"] = http_port.MINOR_VERSION + 1
    config = _write(tmp_path, document)

    assert http_port.pin(config, 8124) == 2
    assert "refusing to edit" in capsys.readouterr().err
    # And it really did not write.
    after = json.loads((config / ".storage" / "http").read_text())
    assert after["data"]["stable"]["server_port"] == 8123


def test_no_store_yet_is_not_an_error(tmp_path, capsys):
    """Before a first boot there is nothing to correct and no schema to check."""
    assert http_port.pin(tmp_path, 8124) == 0
    assert "does not exist yet" in capsys.readouterr().out


def test_a_nonsense_port_is_rejected(capsys):
    assert http_port.main([str(REPO), "70000"]) == 2
    assert "not a port" in capsys.readouterr().err


def test_the_public_credentials_are_refused_off_loopback(capsys):
    """`dev` / `dev` on a machine somebody else can reach is an open door."""
    assert onboard.main(["--url", "http://192.168.1.50:8123"]) == 2
    assert "loopback" in capsys.readouterr().err
