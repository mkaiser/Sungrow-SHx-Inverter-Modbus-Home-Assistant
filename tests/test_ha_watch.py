"""The helper a one-off hardware watch restores through.

Why it is tested at all, when it is dev tooling: the thing it replaces left
register 13017 on at the maintainer's house for 50 minutes, and the mistake
was in exactly the kind of code nobody tests -- a `finally` block in a script
written for one afternoon. The rules worth holding are the ones a reader
would otherwise have to trust: the token is minted when it is used and again
for the restore, nothing is pressed that cannot be put back, the note is on
disk before the first write, and a house left changed exits 5.

Nothing here opens a socket. `_Fake` is Home Assistant's two endpoints with a
state machine behind them.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, REPO / "scripts" / "dev" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


watch_module = _load("ha_watch")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass every backoff and every poll at once."""
    monkeypatch.setattr(watch_module.time, "sleep", lambda _seconds: None)


class _Fake(watch_module.Instance):
    """An instance whose states live in a dict, with the mints counted."""

    def __init__(self, states: dict[str, Any] | None = None) -> None:
        super().__init__("http://127.0.0.1:8125", username="dev", password="dev")
        self.states: dict[str, Any] = states or {}
        self.mints = 0
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []
        #: Entities whose service calls do nothing, however often they are made.
        self.deaf: set[str] = set()

    def bearer(self) -> str:
        self.mints += 1
        return f"token-{self.mints}"

    def state(self, entity_id: str) -> dict[str, Any]:
        self.bearer()
        return self.states[entity_id]

    def call(self, domain: str, service: str, entity_id: str, **data: Any) -> None:
        self.bearer()
        self.calls.append((domain, service, entity_id, data))
        if entity_id in self.deaf:
            return
        document = self.states[entity_id]
        if domain == "switch":
            document["state"] = "on" if service == "turn_on" else "off"
        elif domain == "number":
            document["state"] = str(data["value"])
        elif domain == "select":
            document["state"] = data["option"]
        elif domain == "time":
            document["state"] = data["time"]


def _switch(state: str = "off") -> dict[str, Any]:
    return {"state": state, "attributes": {}}


def _summary(running_since: str | None) -> dict[str, Any]:
    return {"state": "running", "attributes": {"running_since": running_since}}


# --- the credential ------------------------------------------------------


def test_the_restore_drops_the_token_before_its_first_write(tmp_path: Path) -> None:
    """The whole point: the restore does not use the token the watch started on.

    The watcher of 2026-11-17 held one from the start, it expired 29 minutes
    in, and every restore attempt came back 401. So the credential the
    restore writes with is minted at that moment, which is this order: the
    press, then the token dropped, then the write that puts it back.
    """
    instance = _Fake({"switch.forced_startup": _switch()})
    order: list[str] = []
    real_fresh = instance.fresh
    real_call = instance.call

    def fresh() -> None:
        order.append("minted again")
        real_fresh()

    def call(domain: str, service: str, entity_id: str, **data: Any) -> None:
        order.append(f"{service} {entity_id}")
        real_call(domain, service, entity_id, **data)

    instance.fresh = fresh  # type: ignore[method-assign]
    instance.call = call  # type: ignore[method-assign]

    def body(watch: Any) -> None:
        watch.press("switch.forced_startup", "turn_on")

    assert watch_module.run(instance, tmp_path / "note.json", "13017", body) == 0
    assert order == [
        "minted again",  # before the body, so a watch that cannot mint presses nothing
        "turn_on switch.forced_startup",
        "minted again",  # the restore's own, 40 minutes in on a real run
        "turn_off switch.forced_startup",
    ]
    assert instance.states["switch.forced_startup"]["state"] == "off"


def test_a_token_older_than_the_maximum_is_minted_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A watch runs for an hour; its calls must not carry a half-hour token."""
    instance = watch_module.Instance(
        "http://127.0.0.1:8125", username="dev", password="dev"
    )
    minted: list[int] = []

    class _Client:
        def __init__(self, _url: str) -> None:
            self.token = f"fresh-{len(minted)}"

        def log_in(self, _user: str, _password: str) -> None:
            minted.append(1)

    monkeypatch.setattr(watch_module, "_login_flow", lambda: _Client)
    clock = [1000.0]
    monkeypatch.setattr(watch_module.time, "monotonic", lambda: clock[0])

    assert instance.bearer() == "fresh-0"
    assert instance.bearer() == "fresh-0"  # still young: the same token
    clock[0] += watch_module.MAX_TOKEN_AGE + 1
    assert instance.bearer() == "fresh-1"
    assert len(minted) == 2


def test_a_long_lived_token_is_never_minted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reading a production instance uses the token it was given, and no login."""
    monkeypatch.setattr(
        watch_module, "_login_flow", lambda: pytest.fail("logged in with a token")
    )
    instance = watch_module.Instance("http://ha.invalid", token="long-lived")

    assert instance.bearer() == "long-lived"
    instance.fresh()
    assert instance.bearer() == "long-lived"


def test_the_dev_instance_refuses_an_address_somebody_else_can_reach() -> None:
    """`dev` / `dev` on a reachable instance is an open door."""
    with pytest.raises(ValueError, match="not loopback"):
        watch_module.dev_instance("http://192.168.1.50:8123")
    assert watch_module.dev_instance("http://localhost:8125").url.endswith("8125")


# --- what may be pressed -------------------------------------------------


def test_what_cannot_be_put_back_is_not_pressed(tmp_path: Path) -> None:
    """There is no way to write a `button` or a `sensor` back where it was."""
    instance = _Fake({"button.diagnosis_start": _switch()})
    watch = watch_module.Watch(instance, tmp_path / "note.json", "x")

    with pytest.raises(ValueError, match="cannot be put back"):
        watch.press("button.diagnosis_start", "press")

    assert instance.calls == []
    assert not (tmp_path / "note.json").exists()


def test_an_entity_that_reads_unknown_is_not_pressed(tmp_path: Path) -> None:
    """Where it should go back to is not known, so it does not move."""
    instance = _Fake({"switch.forced_startup": _switch("unavailable")})
    watch = watch_module.Watch(instance, tmp_path / "note.json", "x")

    with pytest.raises(ValueError, match="not known"):
        watch.press("switch.forced_startup", "turn_on")

    assert instance.calls == []


def test_the_note_is_on_disk_before_the_write(tmp_path: Path) -> None:
    """No note, no writes: it is what another process restores from."""
    note = tmp_path / "note.json"
    instance = _Fake({"switch.forced_startup": _switch()})
    watch = watch_module.Watch(instance, note, "13017 watch")
    written: list[bool] = []
    real = instance.call

    def record(domain: str, service: str, entity_id: str, **data: Any) -> None:
        written.append(note.exists())
        real(domain, service, entity_id, **data)

    instance.call = record  # type: ignore[method-assign]
    watch.press("switch.forced_startup", "turn_on")

    assert written == [True]
    document = json.loads(note.read_text(encoding="utf-8"))
    assert document["what"] == "13017 watch"
    assert document["pressed"] == [
        {"entity_id": "switch.forced_startup", "state": "off"}
    ]


# --- looking before pressing ---------------------------------------------


def test_a_run_in_flight_is_waited_for_not_pressed_through(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A script interrupted auto repeat's own run 21 seconds in, on 2026-11-17."""
    summary = _summary("2026-11-19T19:00:00+01:00")
    instance = _Fake({"sensor.test_summary": summary})
    watch = watch_module.Watch(instance, tmp_path / "note.json", "x")
    polls = [0]

    def answer(entity_id: str) -> dict[str, Any]:
        polls[0] += 1
        if polls[0] >= 3:
            summary["attributes"]["running_since"] = None
        return summary

    instance.state = answer  # type: ignore[method-assign]
    watch.wait_for_quiet("sensor.test_summary", poll=1)

    assert polls[0] == 3
    assert "in flight since 2026-11-19T19:00:00+01:00" in capsys.readouterr().out


def test_a_quiet_instance_is_not_waited_for(tmp_path: Path) -> None:
    instance = _Fake({"sensor.test_summary": _summary(None)})
    watch = watch_module.Watch(instance, tmp_path / "note.json", "x")

    assert watch.run_in_flight("sensor.test_summary") is None
    watch.wait_for_quiet("sensor.test_summary", poll=1)


# --- putting it back -----------------------------------------------------


@pytest.mark.parametrize(
    ("entity_id", "before", "service", "data"),
    [
        ("switch.forced_startup", "on", "turn_off", {}),
        ("number.battery_max_soc", "90.0", "set_value", {"value": 80}),
        ("select.ems_mode", "self_consumption", "select_option", {"option": "forced"}),
        ("time.forced_charging_start_1", "02:00:00", "set_value", {"time": "03:30:00"}),
    ],
)
def test_every_platform_it_presses_goes_back_the_way_it_came(
    tmp_path: Path, entity_id: str, before: str, service: str, data: dict[str, Any]
) -> None:
    """A platform is in the table only where the state read back can be written."""
    instance = _Fake({entity_id: {"state": before, "attributes": {}}})
    changed: list[str] = []

    def body(watch: Any) -> None:
        watch.press(entity_id, service, **data)
        changed.append(instance.states[entity_id]["state"])

    assert watch_module.run(instance, tmp_path / "note.json", "x", body) == 0
    assert changed and changed[0] != before
    assert instance.states[entity_id]["state"] == before
    assert instance.calls[-1][0] == entity_id.split(".")[0]


def test_the_restore_keeps_trying_until_it_reads_back(tmp_path: Path) -> None:
    """It ends when the register reads back, not when a budget runs out.

    The inverter goes deaf when the restore starts -- which is what a WiNet-S
    under contention does -- and answers again four attempts later.
    """
    instance = _Fake({"switch.forced_startup": _switch()})
    attempts = [0]
    real_call = instance.call
    real_fresh = instance.fresh

    def deafen() -> None:
        instance.deaf = {"switch.forced_startup"}
        real_fresh()

    def flaky(domain: str, service: str, entity_id: str, **data: Any) -> None:
        attempts[0] += 1
        if attempts[0] > 4:
            instance.deaf = set()
        real_call(domain, service, entity_id, **data)

    def body(watch: Any) -> None:
        watch.press("switch.forced_startup", "turn_on")
        assert instance.states["switch.forced_startup"]["state"] == "on"
        instance.fresh = deafen  # type: ignore[method-assign]
        instance.call = flaky  # type: ignore[method-assign]

    assert watch_module.run(instance, tmp_path / "note.json", "x", body) == 0
    assert instance.states["switch.forced_startup"]["state"] == "off"
    assert attempts[0] == 5


def test_a_house_left_changed_is_said_loudly_and_exits_five(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 5 is the one code that means a house is left changed.

    Nothing but a person ends a restore that will not take, so this one is
    ended by a Ctrl-C after three attempts.
    """
    note = tmp_path / "note.json"
    instance = _Fake({"switch.forced_startup": _switch()})
    real_fresh = instance.fresh
    stop = [0]

    def deafen() -> None:
        instance.deaf = {"switch.forced_startup"}
        real_fresh()

    def give_up(_seconds: float) -> None:
        stop[0] += 1
        if stop[0] > 3:
            raise KeyboardInterrupt

    def body(watch: Any) -> None:
        watch.press("switch.forced_startup", "turn_on")
        instance.fresh = deafen  # type: ignore[method-assign]
        monkeypatch.setattr(watch_module.time, "sleep", give_up)

    assert (
        watch_module.run(instance, note, "13017 watch", body)
        == watch_module.EXIT_LEFT_CHANGED
    )
    shouted = capsys.readouterr().err
    assert "THE HOUSE IS LEFT CHANGED" in shouted
    assert "switch.forced_startup" in shouted
    assert f"--restore {note}" in shouted
    # The note survives a failed restore: it is what finishes the job.
    assert json.loads(note.read_text(encoding="utf-8"))["pressed"]


def test_the_note_goes_when_everything_is_back(tmp_path: Path) -> None:
    """A leftover note means a house still carrying a value, so it must not lie."""
    note = tmp_path / "note.json"
    instance = _Fake({"switch.forced_startup": _switch()})

    def body(watch: Any) -> None:
        watch.press("switch.forced_startup", "turn_on")

    assert watch_module.run(instance, note, "x", body) == 0
    assert not note.exists()


def test_the_body_failing_restores_first_and_then_raises(tmp_path: Path) -> None:
    """Every way out of the watch goes through the restore."""
    instance = _Fake({"switch.forced_startup": _switch()})

    def body(watch: Any) -> None:
        watch.press("switch.forced_startup", "turn_on")
        raise ZeroDivisionError("the measurement fell over")

    with (
        pytest.raises(ZeroDivisionError),
        watch_module.watching(instance, tmp_path / "note.json", "x") as watch,
    ):
        body(watch)

    assert instance.states["switch.forced_startup"]["state"] == "off"


def test_nothing_is_pressed_where_no_credential_can_be_minted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A watch that could not restore later fails before it writes anything."""
    instance = _Fake({"switch.forced_startup": _switch()})

    def refuse() -> str:
        raise RuntimeError("no access token")

    monkeypatch.setattr(instance, "bearer", refuse)

    with (
        pytest.raises(RuntimeError, match="no access token"),
        watch_module.watching(instance, tmp_path / "note.json", "x"),
    ):
        pytest.fail("the body ran without a credential")

    assert instance.calls == []


def test_a_dead_watchs_note_is_restored_from_another_process(tmp_path: Path) -> None:
    """The way out when the watcher is gone, as `--restore <snapshot>` is."""
    note = tmp_path / "note.json"
    note.write_text(
        json.dumps(
            {
                "url": "http://127.0.0.1:8125",
                "what": "13017 watch",
                "pressed": [{"entity_id": "switch.forced_startup", "state": "off"}],
            }
        ),
        encoding="utf-8",
    )
    instance = _Fake({"switch.forced_startup": _switch("on")})

    assert watch_module.restore_note(instance, note) == 0
    assert instance.states["switch.forced_startup"]["state"] == "off"
    assert not note.exists()


def test_the_newest_press_goes_back_first(tmp_path: Path) -> None:
    """Interlocking settings are undone in the order they were made, reversed.

    `battery_min_soc` and `battery_max_soc` are refused if they cross, so a
    restore that writes them in press order can be refused on the first word.
    """
    instance = _Fake(
        {
            "number.battery_min_soc": {"state": "10.0", "attributes": {}},
            "number.battery_max_soc": {"state": "90.0", "attributes": {}},
        }
    )

    def body(watch: Any) -> None:
        watch.press("number.battery_min_soc", "set_value", value=20)
        watch.press("number.battery_max_soc", "set_value", value=80)

    assert watch_module.run(instance, tmp_path / "note.json", "x", body) == 0
    restored = [
        call[2] for call in instance.calls if call[3].get("value") in (10.0, 90.0)
    ]
    assert restored == ["number.battery_max_soc", "number.battery_min_soc"]
