"""The Makefile's shortcuts must keep pointing at things that exist.

`make check` is only worth running if it gates on everything CI gates on. The
moment the two lists disagree, a clean local run stops meaning anything and
the Makefile is worse than no Makefile — it is a false all-clear. That is not
hypothetical: the loop this replaced in `doc/development.yaml` ran five of the
ten generators, so a stale `numbers`, `switches`, `selects`, `scan_plan` or
`compatibility` sailed through locally and failed on push.

The obvious fix is to have CI call `make ci` and keep one list. That is
rejected on purpose: each CI step carries a name that says what broke ("The
scan plan matches the library"), and collapsing thirteen of them into one
opaque `make ci` trades a readable failure for a log to go and read. So the
two lists stay, and this asserts they agree.

The path checks are the other half. A renamed script leaves a Makefile target
that fails only when somebody runs it, which for `refs` or `blocks` could be
months.
"""

from __future__ import annotations

import os
from pathlib import Path
import re

import yaml

REPO = Path(__file__).resolve().parents[1]
MAKEFILE = REPO / "Makefile"
WORKFLOW = REPO / ".github/workflows/validate.yml"


def makefile_generators() -> list[str]:
    """Return the Makefile's GENERATORS names, line continuations joined."""
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(r"^GENERATORS :=((?:[^\n\\]*\\\n)*[^\n]*)", text, re.MULTILINE)
    assert match, "the Makefile has no GENERATORS variable"
    return match.group(1).replace("\\\n", " ").split()


def workflow_generators() -> list[str]:
    """Return the generators `validate.yml` runs with --check, in its own order."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["lint-and-test"]["steps"]
    commands = "\n".join(step["run"] for step in steps if "run" in step)
    return re.findall(r"scripts/generate_(\w+)\.py --check", commands)


def test_make_check_gates_on_exactly_what_ci_gates_on() -> None:
    assert sorted(makefile_generators()) == sorted(workflow_generators())


def test_no_generator_is_listed_twice_in_the_makefile() -> None:
    generators = makefile_generators()
    assert len(generators) == len(set(generators))


def test_every_generator_exists() -> None:
    missing = [
        name
        for name in makefile_generators()
        if not (REPO / f"scripts/generate_{name}.py").exists()
    ]
    assert not missing


def test_every_script_the_makefile_runs_exists() -> None:
    """Catches a rename that leaves a target failing only when someone runs it."""
    text = MAKEFILE.read_text(encoding="utf-8")
    # Requiring the extension skips `scripts/generate_$$g.py`, whose loop
    # variable the generator checks above cover instead.
    referenced = set(re.findall(r"scripts/[\w./]+\.(?:py|sh)", text))
    assert referenced, "no scripts referenced -- the regex stopped matching"
    missing = sorted(path for path in referenced if not (REPO / path).exists())
    assert not missing


def test_the_shell_scripts_are_executable() -> None:
    """A .sh without its exec bit fails as "permission denied" from make."""
    scripts = sorted((REPO / "scripts").glob("*.sh"))
    assert scripts, "no shell scripts found"
    assert not [path.name for path in scripts if not os.access(path, os.X_OK)]


def test_the_makefile_is_reachable_from_the_workflow_path_filter() -> None:
    """A Makefile-only change must still trigger the push build that reads it."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads a bare `on:` key as the boolean True.
    triggers = document.get("on", document.get(True))
    assert "Makefile" in triggers["push"]["paths"]
