"""The survey runs on the published library, and says so in its header.

A contributor runs `read_only_survey.sh` or `read_only_survey.cmd`, which
hand `sungrow_survey.py` to `uv run --script`; uv reads the script's PEP 723 header
and fetches a Python and exactly the library version it pins. So the header
is the survey's whole install, and two things can quietly break it:

* an import of something the header does not declare, which works here --
  where everything is installed -- and fails on the contributor's machine;
* a pin that has fallen behind the library, which runs the survey on a
  release that lacks whatever it was written against.

Both are asserted the way `test_library_is_standalone.py` asserts its own
boundary: by reading the files rather than by trusting them. The control
test in `scripts/sungrow_control_test/` runs on the published library the
same way, through its own `control_test.{sh,ps1,cmd}`, and is held to the
same rules.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
SCAN = REPO / "scripts" / "sungrow_read_only_survey"
CONTROL = REPO / "scripts" / "sungrow_control_test"

#: Each folder a contributor is handed: its launchers' name, and the script
#: they start. The launchers are built alike, so they are checked alike.
FOLDERS = {
    SCAN: ("read_only_survey", "sungrow_survey.py"),
    CONTROL: ("control_test", "sungrow_control_test.py"),
}

#: Every launcher, as (folder, filename).
LAUNCHERS = [
    (folder, f"{stem}.{suffix}")
    for folder, (stem, _script) in FOLDERS.items()
    for suffix in ("sh", "ps1", "cmd")
]

#: The modules that may be imported at module level, beyond the standard
#: library: each other. They travel together as a folder.
SIBLINGS = {path.stem for path in SCAN.glob("*.py")}

#: Third-party packages a script may import at module level, each with the
#: distribution that provides it -- which is what a PEP 723 header names.
THIRD_PARTY = {
    "sungrow_modbus": "sungrow-modbus",
    "modbus_connection": "modbus-connection",
}

#: Every script that runs on the published library rather than on a checkout.
PINNED_SCRIPTS = tuple(folder / script for folder, (_stem, script) in FOLDERS.items())


def _header(path: Path) -> dict:
    """Return a script's PEP 723 metadata, parsed the way the PEP specifies."""
    import re
    import tomllib

    match = re.search(
        r"(?m)^# /// script$\s(?P<content>(^#(| .*)$\s)+)^# ///$",
        path.read_text(encoding="utf-8"),
    )
    assert match, f"{path.name} has no `# /// script` block"
    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in match.group("content").splitlines(keepends=True)
    )
    return tomllib.loads(content)


def _pins(path: Path) -> dict[str, str]:
    """Return a header's dependencies as {distribution: requirement}."""
    import re

    found = {}
    for requirement in _header(path)["dependencies"]:
        name = re.match(r"[A-Za-z0-9_.-]+", requirement).group(0).lower()
        found[name.replace("_", "-")] = requirement
    return found


def _module_level_imports(path: Path) -> set[str]:
    """Return the modules a file imports *at import time*.

    An import inside a module-level `if` or `try` still runs when the file is
    imported and counts; an import inside a function does not, and is how
    `probe.py mdns` reaches `zeroconf`, which a survey has no use for. So
    function bodies are skipped explicitly, while class bodies are not: those
    do execute on import.
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


def test_every_scanning_script_imports_only_what_the_header_declares() -> None:
    allowed = set(sys.stdlib_module_names) | SIBLINGS | set(THIRD_PARTY)
    for path in [*sorted(SCAN.glob("*.py")), *sorted(CONTROL.glob("*.py"))]:
        outside = _module_level_imports(path) - allowed
        assert not outside, (
            f"{path.name} imports {sorted(outside)} at module level. The survey "
            "is installed by its PEP 723 header and nothing else, so a "
            "contributor running it through uv would not have that."
        )


@pytest.mark.parametrize("path", PINNED_SCRIPTS, ids=lambda p: p.name)
def test_the_header_declares_every_package_the_script_needs(path: Path) -> None:
    """Including what the siblings it imports need, for the survey."""
    needed = _module_level_imports(path)
    if path.parent == SCAN:
        for sibling in SCAN.glob("*.py"):
            needed |= _module_level_imports(sibling)
    declared = _pins(path)
    for module, distribution in THIRD_PARTY.items():
        if module in needed:
            assert distribution in declared, (
                f"{path.name} imports {module}, which its header does not "
                f"declare as {distribution}"
            )


@pytest.mark.parametrize("path", PINNED_SCRIPTS, ids=lambda p: p.name)
def test_the_header_pins_the_library_this_tree_builds(path: Path) -> None:
    """Exactly, so uv resolves a pre-release without being told to.

    `scripts/release/sync_version.py` moves the pin with every release; this
    is the guard that it did, in the suite rather than only in CI.
    """
    import tomllib

    version = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    assert _pins(path)["sungrow-modbus"] == f"sungrow-modbus=={version}"


@pytest.mark.parametrize("path", PINNED_SCRIPTS, ids=lambda p: p.name)
def test_the_header_asks_for_the_python_the_library_needs(path: Path) -> None:
    """A lower floor would have uv pick a Python the library refuses."""
    import tomllib

    library = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["requires-python"]
    assert _header(path)["requires-python"] == library


def test_the_header_asks_for_the_modbus_backend_the_scripts_use() -> None:
    """The library depends on bare `modbus-connection`; the scripts need tmodbus."""
    for path in PINNED_SCRIPTS:
        assert "[tmodbus]" in _pins(path)["modbus-connection"], path.name


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


def _launcher_id(case: tuple[Path, str]) -> str:
    return f"{case[0].name}/{case[1]}"


@pytest.mark.parametrize("case", LAUNCHERS, ids=_launcher_id)
def test_the_launchers_are_there(case: tuple[Path, str]) -> None:
    """What a contributor is told to run, on each system, in each folder."""
    folder, name = case
    assert (folder / name).is_file()


@pytest.mark.parametrize("folder", list(FOLDERS), ids=lambda f: f.name)
def test_the_shell_launcher_can_be_run_the_way_it_is_documented(folder: Path) -> None:
    """A shebang, and the executable bit in git's index, as for the scripts."""
    import subprocess

    path = folder / f"{FOLDERS[folder][0]}.sh"
    assert path.read_text(encoding="utf-8").startswith("#!/bin/sh\n")
    entry = subprocess.run(
        ["git", "ls-files", "--stage", str(path.relative_to(REPO))],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO,
    ).stdout.split()
    assert entry, f"{path.name} is not tracked"
    assert entry[0] == "100755", f"{path.name} unpacks without the executable bit"


@pytest.mark.parametrize("case", LAUNCHERS, ids=_launcher_id)
def test_the_launchers_read_the_pin_rather_than_carrying_one(
    case: tuple[Path, str],
) -> None:
    """One place for the version: the header the launchers read it from."""
    import tomllib

    folder, name = case
    version = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    assert version not in (folder / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("folder", list(FOLDERS), ids=lambda f: f.name)
def test_each_launcher_starts_a_file_that_is_there(folder: Path) -> None:
    """The `.cmd` names its `.ps1`, and both shells name the Python script.

    A rename that misses one of these leaves a launcher that starts and then
    fails to find the next file, which nothing but a run on that system shows.
    """
    stem, script = FOLDERS[folder]
    cmd = (folder / f"{stem}.cmd").read_text(encoding="utf-8")
    assert f'"%~dp0{stem}.ps1"' in cmd
    assert f"SCRIPT={script}\n" in (folder / f"{stem}.sh").read_text(encoding="utf-8")
    assert f"$Script = '{script}'" in (folder / f"{stem}.ps1").read_text(
        encoding="utf-8"
    )
    assert (folder / script).is_file()


def test_the_two_folders_launchers_differ_only_where_they_must() -> None:
    """Built alike, so a fix to one is a fix to the other.

    Compared with the comments and the user-facing sentences set aside: what
    is left is the logic -- find uv, check a Python, ask before installing --
    and that has to be the same in both.
    """

    def logic(path: Path, comment: str) -> list[str]:
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(comment):
                continue
            lines.append(
                stripped.replace("sungrow_survey.py", "SCRIPT")
                .replace("sungrow_control_test.py", "SCRIPT")
                .replace("control test", "NOUN")
                .replace("survey", "NOUN")
                .replace(" <host> --dry-run", "")
            )
        return lines

    for suffix, comment in (("sh", "#"), ("ps1", "#")):
        survey = logic(SCAN / f"read_only_survey.{suffix}", comment)
        control = logic(CONTROL / f"control_test.{suffix}", comment)
        assert survey == control, suffix


def test_the_line_endings_are_fixed_for_the_launchers() -> None:
    """cmd.exe misreads a batch file with bare LF line endings; sh chokes on CR."""
    attributes = (REPO / ".gitattributes").read_text(encoding="utf-8")
    for rule in ("*.sh text eol=lf", "*.cmd text eol=crlf", "*.ps1 text eol=crlf"):
        assert rule in attributes, rule
