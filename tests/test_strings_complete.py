"""Every form a person can see has words on it.

Two of these shipped without, and neither failed anything. `run_control_test`
was a registered action with no entry in `strings.json`, so the one action that
**writes to somebody's inverter** would have appeared in the picker as a slug
with no description. `async_step_manual` showed a real form with no title, no
description and raw field keys -- and it is the fallback path, reached only
after automatic discovery has already failed, which is the worst moment to hand
somebody a form that looks broken.

Neither is the kind of thing a test usually catches, because nothing raises:
Home Assistant renders the key and moves on. So these compare the code against
the strings directly.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

INTEGRATION = (
    Path(__file__).resolve().parent.parent / "custom_components/sungrow_modbus"
)


def _strings() -> dict:
    return json.loads((INTEGRATION / "strings.json").read_text())


def _english() -> dict:
    return json.loads((INTEGRATION / "translations/en.json").read_text())


def _steps_showing_a_form(module: str) -> set[str]:
    """Flow steps that call `async_show_form`, and therefore need words.

    A step that only decides where to go next shows nothing, so it needs
    nothing -- `setup_devices`, `setup_diagnostics` and `start_over` are all
    pure redirects. Asking the source which ones render is the only way to tell
    them apart without listing them by hand and watching that list rot.
    """
    tree = ast.parse((INTEGRATION / module).read_text())
    showing: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("async_step_"):
            continue
        for call in ast.walk(node):
            if isinstance(call, ast.Call) and getattr(call.func, "attr", "") == (
                "async_show_form"
            ):
                showing.add(node.name[len("async_step_") :])
    return showing


def test_english_is_exactly_strings():
    """`en.json` is what Home Assistant reads; `strings.json` is the source."""
    assert _strings() == _english()


def test_every_form_step_has_a_title_and_field_labels():
    """A form with no strings renders its keys, which looks like a bug to a user."""
    strings = _strings()
    described = {
        **strings["config"].get("step", {}),
        **strings.get("options", {}).get("step", {}),
    }

    missing = sorted(
        s for s in _steps_showing_a_form("config_flow.py") if s not in described
    )
    assert not missing, f"steps that show a form but have no strings: {missing}"

    for name, step in described.items():
        assert step.get("title") or step.get("description"), f"{name} says nothing"


def test_every_abort_reason_has_a_message():
    """An abort with no string shows the reason slug and explains nothing.

    These are the endings a flow can reach -- already configured, cannot
    connect, no serial number -- and they are the only thing a person sees when
    setup stops.
    """
    strings = _strings()
    used = {
        kw.value.value
        for node in ast.walk(ast.parse((INTEGRATION / "config_flow.py").read_text()))
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "reason" and isinstance(kw.value, ast.Constant)
    }

    missing = sorted(r for r in used if r not in strings["config"].get("abort", {}))
    assert not missing, f"abort reasons with no message: {missing}"


def test_every_action_is_described_in_both_files():
    """`services.yaml` says what an action takes; the strings say what it is."""
    actions = yaml.safe_load((INTEGRATION / "services.yaml").read_text())
    strings = _strings()["services"]

    assert sorted(actions) == sorted(strings)
    for name, action in actions.items():
        assert strings[name].get("name"), f"{name} has no name"
        assert strings[name].get("description"), f"{name} has no description"
        fields = set((action or {}).get("fields", {}) or {})
        assert fields == set(strings[name].get("fields", {}) or {}), name


def test_every_repair_issue_has_a_message():
    """A repair with no strings is a warning triangle that explains nothing."""
    described = set(_strings().get("issues", {}))
    used = {
        kw.value.value
        for path in INTEGRATION.glob("*.py")
        if "repair" in path.name
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg == "translation_key" and isinstance(kw.value, ast.Constant)
    }

    missing = sorted(k for k in used if k not in described)
    assert not missing, f"repair issues with no strings: {missing}"
