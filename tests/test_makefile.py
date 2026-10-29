"""The Makefile's shortcuts must keep pointing at things that exist.

`make check` is only worth running if it gates on everything CI gates on. The
moment the two lists disagree, a clean local run stops meaning anything and
the Makefile is worse than no Makefile — it is a false all-clear. That is not
hypothetical: the loop this replaced in `doc/development.yaml` ran five of the
ten generators, so a stale `numbers`, `switches`, `selects` or `compatibility`
sailed through locally and failed on push.

The obvious fix is to have CI call `make ci` and keep one list. That is
rejected on purpose: each CI step carries a name that says what broke ("The
compatibility page matches the surveys"), and collapsing thirteen of them into one
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
    """Return the Makefile's GENERATORS paths under scripts/, continuations joined."""
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(r"^GENERATORS :=((?:[^\n\\]*\\\n)*[^\n]*)", text, re.MULTILINE)
    assert match, "the Makefile has no GENERATORS variable"
    return match.group(1).replace("\\\n", " ").split()


def _workflow_checks() -> list[tuple[str, str]]:
    """Return (script, target) for every generator `validate.yml` checks."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["lint-and-test"]["steps"]
    commands = "\n".join(step["run"] for step in steps if "run" in step)
    return re.findall(r"scripts/(generate/[\w/]+\.py)(?: (\w+))? --check", commands)


def workflow_generators() -> list[str]:
    """Return the generator scripts `validate.yml` runs with --check."""
    return sorted({script for script, _target in _workflow_checks()})


def test_make_check_gates_on_exactly_what_ci_gates_on() -> None:
    assert sorted(makefile_generators()) == workflow_generators()


def test_ci_checks_every_description_target() -> None:
    """CI names each of `descriptions.py`'s targets as its own step.

    The Makefile runs the script once with no target, which is all of them;
    CI runs one target per step so a failure says which artefact broke. So
    a target added to the script must be added to CI too, or `make check`
    gates on something CI never runs.
    """
    import sys

    sys.path.insert(0, str(REPO / "scripts" / "generate"))
    from descriptions import TARGETS

    ran = {target for script, target in _workflow_checks() if "descriptions" in script}
    assert ran == set(TARGETS)


def test_no_generator_is_listed_twice_in_the_makefile() -> None:
    generators = makefile_generators()
    assert len(generators) == len(set(generators))


def test_every_generator_exists() -> None:
    missing = [
        name for name in makefile_generators() if not (REPO / "scripts" / name).exists()
    ]
    assert not missing


def test_every_script_the_makefile_runs_exists() -> None:
    """Catches a rename that leaves a target failing only when someone runs it."""
    text = MAKEFILE.read_text(encoding="utf-8")
    # `scripts/$$g` has no extension to match, and the generator checks above
    # cover its loop variable instead.
    referenced = set(re.findall(r"scripts/[\w./]+\.(?:py|sh)", text))
    assert referenced, "no scripts referenced -- the regex stopped matching"
    missing = sorted(
        path
        for path in referenced
        if not (REPO / path).exists() and not (REPO / "device-survey" / path).exists()
    )
    assert not missing


def test_the_shell_scripts_are_executable() -> None:
    """A .sh without its exec bit fails as "permission denied" from make."""
    scripts = sorted((REPO / "scripts").rglob("*.sh"))
    assert scripts, "no shell scripts found"
    assert not [path.name for path in scripts if not os.access(path, os.X_OK)]


def test_the_makefile_is_reachable_from_the_workflow_path_filter() -> None:
    """A Makefile-only change must still trigger the push build that reads it."""
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads a bare `on:` key as the boolean True.
    triggers = document.get("on", document.get(True))
    assert "Makefile" in triggers["push"]["paths"]
