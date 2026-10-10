"""The scanning scripts must run with nothing installed.

A contributor who will not install anything gets the `sungrow_survey` folder and
runs `sungrow_survey.py` with a bare Python. That only works if nothing in the
folder imports anything outside the standard library **at import time** --
and the one thing they would obviously want to import, `sungrow_modbus`, is
exactly what a stranger will not have.

Nothing but discipline enforces it. A single
`from sungrow_modbus import COMPONENTS` at the top of a file would break it,
and this suite would keep passing, because the library is installed here. So
the boundary is asserted the way `test_library_is_standalone.py` asserts its
own: by reading the imports rather than by trusting them.

Imports *inside* functions are fine and are how the scripts use the library
when it happens to be there -- to verify the committed plan, or to drive the
real Modbus stack. The rule is only about what fails before `main()` runs.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
SCAN = REPO / "scripts" / "sungrow_survey"

#: The modules that may be imported at module level, beyond the standard
#: library: each other. They travel together as a folder.
SIBLINGS = {path.stem for path in SCAN.glob("*.py")}


def _module_level_imports(path: Path) -> set[str]:
    """Return the modules a file imports *at import time*.

    The distinction is the whole contract, so it is worth being exact about.
    An import inside a module-level `if` or `try` still runs when the file is
    imported and counts; an import inside a function does not and is how these
    scripts use the library when it happens to be installed.

    `ast.walk` cannot express that -- it descends into function bodies, and
    the first version of this test duly failed on the deliberately-lazy
    imports it was written to permit. So function bodies are skipped
    explicitly, while class bodies are not: those do execute on import.
    """
    roots: set[str] = set()

    def visit(nodes: list[ast.stmt]) -> None:
        for node in nodes:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    roots.add(node.module.split(".")[0])
            else:
                visit(
                    [
                        child
                        for field in ("body", "orelse", "finalbody", "handlers")
                        for child in getattr(node, field, []) or []
                        if isinstance(child, ast.stmt)
                    ]
                )
                for handler in getattr(node, "handlers", []) or []:
                    visit(handler.body)

    visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)).body)
    return roots


def test_the_directory_has_something_to_check() -> None:
    """A glob that quietly matched nothing would make every test below pass."""
    assert SCAN.is_dir()
    assert len(SIBLINGS) >= 3, SIBLINGS


def test_every_scanning_script_imports_only_the_standard_library() -> None:
    allowed = set(sys.stdlib_module_names) | SIBLINGS
    for path in sorted(SCAN.glob("*.py")):
        outside = _module_level_imports(path) - allowed
        assert not outside, (
            f"{path.name} imports {sorted(outside)} at module level, so it "
            "cannot run with nothing installed -- and `sungrow_survey.py`, which "
            "contributors run with a bare Python, imports this folder."
        )


def test_the_committed_plan_travels_with_them() -> None:
    """The scripts read their plan from a file, so the file has to be there."""
    plan = SCAN / "scan_plan.json"
    assert plan.exists(), (
        "scan_plan.json is what replaces the library for somebody who has not "
        "installed it. Without it, the block read test has no plan to test."
    )


#: The scripts somebody runs, as against the modules they import. Found by
#: what the file does rather than listed, so a new script cannot be missed.
SCRIPTS = sorted(
    path
    for path in SCAN.glob("*.py")
    if 'if __name__ == "__main__":' in path.read_text(encoding="utf-8")
)


def test_the_folder_has_a_script_to_run() -> None:
    """A filter that quietly matched nothing would make the test below pass."""
    assert "sungrow_survey" in {path.stem for path in SCRIPTS}, SCRIPTS


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_every_script_can_be_run_the_way_it_is_documented(path) -> None:
    """A shebang and the bit that makes it mean something.

    `sungrow_survey.py` shipped without the executable bit -- the one file in this
    directory that the README, the issue template and `probe.py` itself all
    tell people to run. `./sungrow_survey.py` answered *Permission denied*, which
    reads as "this does not exist" to somebody who was handed a folder and a
    sentence, and the sentence I printed alongside it named an absolute
    `/workspaces/...` path and the interpreter `python`, which many systems
    do not have.

    The bit is checked in git's index rather than on disk, because that is
    what a contributor's copy is unpacked from -- a local `chmod` would
    satisfy a filesystem check and fix nothing for them.
    """
    import subprocess

    assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"), (
        f"{path.name} has no shebang, so `./{path.name}` cannot work"
    )
    entry = subprocess.run(
        ["git", "ls-files", "--stage", str(path.relative_to(REPO))],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout.split()
    assert entry, f"{path.name} is not tracked"
    assert entry[0] == "100755", (
        f"{path.name} is mode {entry[0]} in git, so it unpacks without the "
        "executable bit and `./{path.name}` will say Permission denied"
    )
