"""`quality_scale.yaml` says where the integration stands, and stays true.

Home Assistant's hassfest checks this file only for core integrations, so here
nothing would notice a `done` that stopped holding or a rule Home Assistant
added. These tests take the rule list from the installed Home Assistant -- the
union of what its own integrations declare -- so a new rule fails here on the
first run against the release that brings it. Every rule a test can decide from
the code is decided, in both directions: a `done` that does not hold fails, and
so does a `todo` that already does, so the file cannot drift either way.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
import json
from pathlib import Path
import tomllib

import pytest
import yaml

import homeassistant

REPO = Path(__file__).resolve().parent.parent
INTEGRATION = REPO / "custom_components/sungrow_modbus"
STATUSES = {"done", "todo", "exempt"}
# Home Assistant's errors a person can see: the action ones, and the setup and
# update ones it shows on the integration's page.
TRANSLATABLE = {
    "ConfigEntryAuthFailed",
    "ConfigEntryError",
    "ConfigEntryNotReady",
    "HomeAssistantError",
    "ServiceValidationError",
    "UpdateFailed",
}
PLATFORMS = ("binary_sensor", "button", "number", "select", "sensor", "switch", "time")


def _declared() -> dict[str, dict[str, str]]:
    """Return every rule as {"status": ..., "comment": ...}."""
    rules = yaml.safe_load((INTEGRATION / "quality_scale.yaml").read_text())["rules"]
    return {
        name: value if isinstance(value, dict) else {"status": value}
        for name, value in rules.items()
    }


def _home_assistant_rules() -> set[str]:
    """Return every rule Home Assistant's own integrations are held to."""
    components = Path(homeassistant.__file__).parent / "components"
    rules: set[str] = set()
    for path in components.glob("*/quality_scale.yaml"):
        rules |= set((yaml.safe_load(path.read_text()) or {}).get("rules") or {})
    return rules


def _tree(name: str) -> ast.Module:
    return ast.parse((INTEGRATION / name).read_text())


def _defines(name: str, function: str) -> bool:
    return any(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == function
        for node in ast.walk(_tree(name))
    )


def _raises_without_translation() -> list[str]:
    """Return `file:line` of each user-facing error raised with bare text."""
    found = []
    for path in sorted(INTEGRATION.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                continue
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name not in TRANSLATABLE:
                continue
            if not any(k.arg == "translation_key" for k in node.exc.keywords):
                found.append(f"{path.name}:{node.lineno}")
    return found


def _parallel_updates_everywhere() -> bool:
    return all(
        any(
            isinstance(node, ast.Assign)
            and any(getattr(t, "id", None) == "PARALLEL_UPDATES" for t in node.targets)
            for node in _tree(f"{platform}.py").body
        )
        for platform in PLATFORMS
    )


def _mypy_checks_integration() -> bool:
    config = tomllib.loads((REPO / "pyproject.toml").read_text())["tool"]["mypy"]
    return config.get("strict") is True and "custom_components/sungrow_modbus" in (
        config.get("files") or []
    )


def _no_hass_data() -> bool:
    return "hass.data[DOMAIN]" not in "".join(
        path.read_text() for path in INTEGRATION.glob("*.py")
    )


CHECKS: dict[str, Callable[[], bool]] = {
    "config-entry-unloading": lambda: _defines("__init__.py", "async_unload_entry"),
    "diagnostics": lambda: _defines(
        "diagnostics.py", "async_get_config_entry_diagnostics"
    ),
    "exception-translations": lambda: not _raises_without_translation(),
    "icon-translations": lambda: (INTEGRATION / "icons.json").is_file(),
    "integration-owner": lambda: bool(
        json.loads((INTEGRATION / "manifest.json").read_text()).get("codeowners")
    ),
    "parallel-updates": _parallel_updates_everywhere,
    "reconfiguration-flow": lambda: _defines(
        "config_flow.py", "async_step_reconfigure"
    ),
    "repair-issues": lambda: (INTEGRATION / "repairs.py").is_file(),
    "runtime-data": _no_hass_data,
    "stale-devices": lambda: _defines(
        "__init__.py", "async_remove_config_entry_device"
    ),
    "strict-typing": _mypy_checks_integration,
}


def test_every_rule_home_assistant_has_is_declared() -> None:
    known = _home_assistant_rules()
    if not known:
        pytest.skip("this Home Assistant ships no quality_scale.yaml to compare with")
    declared = set(_declared())
    assert not known - declared, f"rules to add: {sorted(known - declared)}"
    assert not declared - known, (
        f"rules Home Assistant no longer has: {sorted(declared - known)}"
    )


def test_statuses_are_known_and_exemptions_say_why() -> None:
    for name, rule in _declared().items():
        assert rule["status"] in STATUSES, name
        if rule["status"] == "exempt":
            assert rule.get("comment"), f"{name} is exempt without a reason"


@pytest.mark.parametrize("rule", sorted(CHECKS))
def test_checkable_rules_match_the_code(rule: str) -> None:
    status = _declared()[rule]["status"]
    holds = CHECKS[rule]()
    if status == "done":
        assert holds, f"{rule} is marked done but the code does not meet it"
    elif status == "todo":
        assert not holds, f"{rule} is met by the code; mark it done"


def test_icons_name_only_actions_and_entities_that_exist() -> None:
    icons = json.loads((INTEGRATION / "icons.json").read_text())
    actions = set(yaml.safe_load((INTEGRATION / "services.yaml").read_text()))
    assert set(icons["services"]) == actions
    entities = json.loads((INTEGRATION / "strings.json").read_text())["entity"]
    for platform, keys in icons["entity"].items():
        assert not set(keys) - set(entities[platform]), platform
