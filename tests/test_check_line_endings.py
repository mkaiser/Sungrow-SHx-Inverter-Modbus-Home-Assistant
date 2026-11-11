"""`scripts/dev/check_line_endings.py`, on a throwaway repository.

The repository is built the way a Windows checkout leaves one: committed with
LF, then written back with CRLF, beside a file whose CRLF `.gitattributes`
asks for, one committed with CRLF, and one with an uncommitted change.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent / "scripts" / "dev" / "check_line_endings.py"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a repository committed with LF and checked out with CRLF."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / ".gitattributes").write_bytes(b"*.cmd text eol=crlf\nraw/** -text\n")
    (tmp_path / "plain.py").write_bytes(b"a = 1\nb = 2\n")
    (tmp_path / "edited.py").write_bytes(b"a = 1\n")
    (tmp_path / "run.cmd").write_bytes(b"@echo off\r\necho hi\r\n")
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "document.json").write_bytes(b"{\r\n}\r\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "LF")
    # Checked out again as Git for Windows does, which records the CRLF
    # file's size in the index; then an owner's own edit.
    for name in ("plain.py", "edited.py"):
        (tmp_path / name).unlink()
    subprocess.run(
        ["git", "-c", "core.autocrlf=true", "checkout", "--", "."],
        cwd=tmp_path,
        check=True,
    )
    assert (tmp_path / "plain.py").read_bytes() == b"a = 1\r\nb = 2\r\n"
    with (tmp_path / "edited.py").open("ab") as handle:
        handle.write(b"c = 3\r\n")
    return tmp_path


@pytest.fixture
def script(repo: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_line_endings", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO", repo)
    return module


def _status(repo: Path) -> set[str]:
    return {line[3:] for line in _git(repo, "status", "--porcelain").splitlines()}


def test_it_finds_crlf_where_the_repository_has_lf(
    repo: Path, script: ModuleType
) -> None:
    found = {path.name for path in script.wrong_endings()}
    # Not the launcher that asks for CRLF, nor the raw document stored so.
    assert found == {"plain.py", "edited.py"}


def test_fix_converts_and_leaves_only_real_changes(
    repo: Path, script: ModuleType
) -> None:
    converted, refreshed = script.fix()

    assert converted == 2
    assert (repo / "plain.py").read_bytes() == b"a = 1\nb = 2\n"
    assert (repo / "edited.py").read_bytes() == b"a = 1\nc = 3\n"
    assert (repo / "run.cmd").read_bytes() == b"@echo off\r\necho hi\r\n"
    assert (repo / "raw" / "document.json").read_bytes() == b"{\r\n}\r\n"
    assert script.wrong_endings() == []
    # The edit survives, unstaged; the converted file is clean again.
    assert _status(repo) == {"edited.py"}
    assert _git(repo, "diff", "--cached", "--name-only") == ""
    assert refreshed >= 1


def test_fix_on_a_clean_tree_does_nothing(repo: Path, script: ModuleType) -> None:
    _git(repo, "checkout", "--", "plain.py", "edited.py")
    assert script.fix() == (0, 0)
    assert _status(repo) == set()
