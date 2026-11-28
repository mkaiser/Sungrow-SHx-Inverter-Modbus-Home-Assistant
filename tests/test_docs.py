"""The hand-written documents name things that exist.

Prose drifts from the code unless something holds it, the way
`test_wiki.py`'s `test_repository_paths_exist` holds the wiki to the tree.
These are the mechanical checks, fast and with no network: a repository path
a document names exists, a `make` target it names is in the `Makefile`,
`doc/development.md`'s *Every script* and `scripts/` list the same files,
every action is in `doc/integration_help.md` and every option the options
flow shows is in `doc/integration_options.md`. Whether a count or a sentence
about behaviour is still true is for a reader, not for this file.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import re
import subprocess

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "doc"
INTEGRATION = REPO / "custom_components" / "sungrow_modbus"


def _documents() -> list[Path]:
    """Return the Markdown a reader is sent to, hand-written and generated."""
    return sorted(
        [
            REPO / "README.md",
            REPO / "AGENTS.md",
            *DOC.glob("*.md"),
            *(REPO / "device-diagnosis").glob("*.md"),
            *(REPO / ".claude" / "skills").glob("*/SKILL.md"),
        ]
    )


DOCUMENTS = _documents()


def _rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


#: A repository path in backticks: one of the tree's top-level directories,
#: then at least one more segment.
REPO_PATH = re.compile(
    r"`((?:src|custom_components|doc|device-diagnosis|tests|scripts|plans"
    r"|\.wiki|\.github|\.claude|\.devcontainer)/[^`\s]+)`"
)

#: A relative Markdown link's target, before any anchor.
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)")


def _strip(path: str) -> str:
    """Drop what follows a path but is not part of it: `:line`, `::test`."""
    path = path.split("::", 1)[0]
    path = re.sub(r":\d+(?:-\d+)?$", "", path)
    return path.rstrip(".,:;)")


def _named_paths(document: Path) -> Iterator[Path]:
    """Every repository file a document names, by backticks or by a link."""
    text = document.read_text(encoding="utf-8")
    for path in REPO_PATH.findall(text):
        if any(c in path for c in "<>*{…") or "..." in path:
            continue
        yield REPO / _strip(path)
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or any(c in target for c in "<>{"):
            continue
        resolved = (document.parent / _strip(target)).resolve()
        # Above the checkout is GitHub's page for it (`../../issues`).
        if resolved.is_relative_to(REPO):
            yield resolved


@pytest.mark.parametrize("document", DOCUMENTS, ids=_rel)
def test_named_paths_exist(document: Path) -> None:
    """A renamed or deleted file shows up as a stale document."""
    missing = sorted(
        {_rel(path) for path in _named_paths(document) if not path.exists()}
    )
    assert not missing, f"{_rel(document)} names what does not exist: {missing}"


def _makefile_targets() -> set[str]:
    text = (REPO / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Za-z0-9_-]+):", text, re.MULTILINE))


#: Code: inline spans and fenced blocks. `make` outside them is a verb.
CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
MAKE = re.compile(r"(?:^|[\s;&|(`$])make\s+([a-z][a-z0-9_-]*)", re.MULTILINE)
#: In the YAML runbook, where everything is code and comments are prose: a
#: command starts a line, a value or a comment.
MAKE_IN_YAML = re.compile(
    r"(?:^[\s-]*|[:#;&|(]\s*)make\s+([a-z][a-z0-9_-]*)", re.MULTILINE
)


def _make_targets_named(document: Path) -> set[str]:
    text = document.read_text(encoding="utf-8")
    if document.suffix == ".yaml":
        return set(MAKE_IN_YAML.findall(text))
    return {target for span in CODE.findall(text) for target in MAKE.findall(span)}


@pytest.mark.parametrize("document", [*DOCUMENTS, DOC / "development.yaml"], ids=_rel)
def test_make_targets_exist(document: Path) -> None:
    """Every `make <target>` a document gives is one the Makefile has."""
    named = _make_targets_named(document)
    unknown = sorted(named - _makefile_targets())
    assert not unknown, (
        f"{_rel(document)} names make targets that do not exist: {unknown}"
    )


def _every_script() -> set[str]:
    """Return the files `doc/development.md`'s *Every script* table lists."""
    text = (DOC / "development.md").read_text(encoding="utf-8")
    section = text.split("\n## Every script\n", 1)[1].split("\n## ", 1)[0]
    listed: set[str] = set()
    prefix = ""
    for line in section.splitlines():
        if heading := re.match(r"^\| \*\*`(scripts/[^`]+/)`\*\*", line):
            prefix = heading.group(1)
        elif row := re.match(r"^\| `([^`]+)` \|", line):
            assert prefix, f"a row before any directory heading: {line}"
            listed.add(prefix + row.group(1))
    return listed


def _scripts() -> set[str]:
    """Every tracked script and input table under `scripts/`.

    The simulator's seeds are data a script reads, not a script: the
    *Simulator* section names them.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "scripts"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return {
        name
        for name in tracked
        if not (name.startswith("scripts/dev/simulator_") and name.endswith(".json"))
    }


def test_every_script_is_listed() -> None:
    """A new script gets a row in *Every script*."""
    missing = sorted(_scripts() - _every_script())
    assert not missing, f"doc/development.md's Every script lacks {missing}"


def test_every_listed_script_exists() -> None:
    """A row in *Every script* names a file that is there."""
    stale = sorted(path for path in _every_script() if not (REPO / path).is_file())
    assert not stale, f"doc/development.md's Every script names {stale}"


def test_every_action_is_in_the_help() -> None:
    """Every action in `services.yaml` is described in `integration_help.md`."""
    services = yaml.safe_load(
        (INTEGRATION / "services.yaml").read_text(encoding="utf-8")
    )
    help_text = (DOC / "integration_help.md").read_text(encoding="utf-8")
    missing = sorted(
        name for name in services if f"sungrow_modbus.{name}" not in help_text
    )
    assert not missing, f"doc/integration_help.md lacks the actions {missing}"


def _option_labels() -> set[str]:
    """Every field label the options flow shows, as `strings.json` words it."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    labels: set[str] = set()
    for step in strings["options"]["step"].values():
        labels.update(step.get("data", {}).values())
        for section in step.get("sections", {}).values():
            labels.update(section.get("data", {}).values())
    return labels


def test_every_option_is_documented() -> None:
    """Every option the options flow shows has its label on the options page."""
    text = (DOC / "integration_options.md").read_text(encoding="utf-8")
    missing = sorted(label for label in _option_labels() if label not in text)
    assert not missing, f"doc/integration_options.md lacks the options {missing}"
