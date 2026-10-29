"""The wiki in `.wiki/` keeps llmwiki's format, and keeps up with its sources.

The repository is organised after microsoft/llmwiki: raw sources nobody
rewrites, a wiki compiled from them, and a schema in `.wiki/AGENTS.md`. The
extension's `@wiki /lint` checks the format, but only for whoever has the
extension open, so these are its rules in plain Python and in CI -- plus the
three this project adds, which are what keep the wiki from going stale:
every source resolves to a tracked file, every committed survey has a
page, and every repository path a page names still exists.

The format is llmwiki's own (`@llmwiki/core` 0.1.2): frontmatter parsed as
YAML, index entries as `- [Title](path) — summary #tag`, and links as
relative Markdown links ending in `.md`.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WIKI_ROOT = REPO / ".wiki"
WIKI = WIKI_ROOT / "wiki"

#: The page types llmwiki's lint accepts.
TYPES = {"entity", "concept", "source", "summary", "query"}

#: Required everywhere, and by type. llmwiki requires only `type` and
#: `title` and recommends `tags` and `created`; here all four are required.
REQUIRED = {"type", "title", "tags", "created"}
REQUIRED_BY_TYPE = {
    "source": {"source_path", "ingested"},
    "query": {"query", "results_count"},
}

#: The only frontmatter keys llmwiki's schema names. Anything else belongs in
#: the body, so the extension's own tools keep reading the pages.
ALLOWED = REQUIRED | {
    "updated",
    "sources",
    "source_path",
    "ingested",
    "query",
    "results_count",
}

#: llmwiki's link pattern (`getPageLinksDetailed` in wiki.ts).
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

#: llmwiki's index entry pattern (`parseEntryLine` in index-ops.ts).
INDEX_ENTRY = re.compile(r"^-\s+\[((?:[^\]\\]|\\.)+)\]\(((?:[^)\\]|\\.)+)\)(.*)$")

#: A repository path in backticks, which is how a page cites a file.
REPO_PATH = re.compile(
    r"`((?:src|custom_components|doc|device-survey|tests|scripts|legacy|plans|\.wiki)"
    r"/[^`\s]+)`"
)

#: Where surveys are committed, each of which must have a source page.
DOCUMENT_DIRS = ("device-survey/inverter", "device-survey/wallbox")


def _tracked() -> set[str]:
    """Return every path git tracks, staged additions included."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    ).stdout
    return {name for name in out.split("\0") if name}


def _pages() -> list[Path]:
    """Return every wiki page but the index and the log, as llmwiki lints."""
    skip = ("index.md", "log.md")
    return sorted(
        p for p in WIKI.rglob("*.md") if p.relative_to(WIKI).as_posix() not in skip
    )


def _split(page: Path) -> tuple[dict, str]:
    """Return a page's frontmatter and body."""
    text = page.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{_rel(page)} has no frontmatter"
    _, front, body = text.split("---\n", 2)
    meta = yaml.safe_load(front)
    assert isinstance(meta, dict), f"{_rel(page)}: frontmatter is not a mapping"
    return meta, body


def _rel(page: Path) -> str:
    return page.relative_to(WIKI).as_posix()


def _slugify(filename: str) -> str:
    """Slugify as llmwiki does (utils.ts): drop the extension, kebab-case the rest."""
    stem = re.sub(r"\.[^.]+$", "", filename).lower()
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", stem))


def _index() -> list[str]:
    """Return the page paths the index lists, in order."""
    paths = []
    for line in (WIKI / "index.md").read_text(encoding="utf-8").splitlines():
        match = INDEX_ENTRY.match(line.strip())
        if match:
            paths.append(match.group(2))
    return paths


PAGES = _pages()


def test_the_wiki_is_scaffolded() -> None:
    """The layout llmwiki's init creates, which its tools look for."""
    for path in ("AGENTS.md", "raw", "wiki/index.md", "wiki/log.md"):
        assert (WIKI_ROOT / path).exists(), f".wiki/{path} is missing"
    assert PAGES, "the wiki has no pages"


@pytest.mark.parametrize("page", PAGES, ids=_rel)
def test_frontmatter(page: Path) -> None:
    """frontmatter-validation, with tags and created required."""
    meta, _ = _split(page)
    assert meta.get("type") in TYPES, f"{_rel(page)}: type {meta.get('type')!r}"
    missing = (REQUIRED | REQUIRED_BY_TYPE.get(meta["type"], set())) - set(meta)
    assert not missing, f"{_rel(page)} lacks {', '.join(sorted(missing))}"
    extra = set(meta) - ALLOWED
    assert not extra, (
        f"{_rel(page)} has frontmatter keys llmwiki does not know: "
        f"{', '.join(sorted(extra))}. Put them in the body."
    )
    assert isinstance(meta["tags"], list), f"{_rel(page)}: tags is not a list"


@pytest.mark.parametrize("page", [*PAGES, WIKI / "index.md"], ids=_rel)
def test_links_resolve_to_wiki_pages(page: Path) -> None:
    """broken-links, and the rule that a repository file is cited, not linked.

    llmwiki treats every `.md` link as a wiki page, so a link to
    `doc/architecture.md` would be one of its broken links. Any other
    relative link points outside the wiki, where its lint cannot follow.
    """
    for _, target in LINK.findall(page.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#")):
            continue
        assert target.endswith(".md"), (
            f"{_rel(page)} links to {target}. Name a repository file in "
            "backticks instead of linking it."
        )
        resolved = (page.parent / target).resolve()
        assert resolved.is_relative_to(WIKI) and resolved.is_file(), (
            f"{_rel(page)} links to {target}, which is not a wiki page"
        )


def test_every_page_is_indexed_and_every_entry_exists() -> None:
    """index-completeness, stale-entries, and so orphan-pages too."""
    listed = _index()
    pages = {_rel(p) for p in PAGES}
    unlisted = sorted(pages - set(listed))
    stale = sorted(set(listed) - pages)
    assert not unlisted, f"not in index.md: {unlisted}"
    assert not stale, f"index.md lists missing pages: {stale}"
    assert len(listed) == len(set(listed)), "index.md lists a page twice"


def test_the_log_is_in_llmwiki_format() -> None:
    """Every entry heading parses as llmwiki's readLog parses it."""
    heading = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] (\S+) \| (.+)$")
    lines = (WIKI / "log.md").read_text(encoding="utf-8").splitlines()
    headings = [line for line in lines if line.startswith("## ")]
    assert headings, "log.md has no entries"
    for line in headings:
        assert heading.match(line), (
            f"log.md: {line!r} is not '## [date] verb | subject'"
        )


@pytest.mark.parametrize(
    "page", [p for p in PAGES if _split(p)[0].get("type") == "source"], ids=_rel
)
def test_a_source_is_a_tracked_file(page: Path) -> None:
    """source-exists: never a transcript, a snapshot or anything gitignored."""
    meta, _ = _split(page)
    path = (WIKI_ROOT / meta["source_path"]).resolve()
    assert path.is_file(), f"{_rel(page)}: {meta['source_path']} does not exist"
    assert path.relative_to(REPO).as_posix() in _tracked(), (
        f"{_rel(page)}: {meta['source_path']} is not tracked. A wiki source "
        "must be a file the repository publishes, never a transcript."
    )


def test_every_document_has_a_source_page() -> None:
    """survey-ingested: a document lands with its page, in one commit."""
    missing = [
        name
        for name in sorted(_tracked())
        if name.startswith(DOCUMENT_DIRS)
        and name.endswith(".json")
        and not (WIKI / "sources" / f"{_slugify(Path(name).name)}-summary.md").is_file()
    ]
    assert not missing, (
        "surveys with no wiki page (see the ingest workflow in "
        f".wiki/AGENTS.md): {missing}"
    )


def test_no_published_address_reaches_the_wiki() -> None:
    """A survey's address octets are its owner's to publish, not the wiki's.

    The owner agreed to `ip_address_last_two_octets` in one document. An
    owner's free-text comment can repeat them, and an ingest that quotes the
    comment would carry them onto a page that never asked.
    """
    octets = set()
    for name in _tracked():
        if name.startswith(DOCUMENT_DIRS) and name.endswith(".json"):
            value = json.loads((REPO / name).read_text(encoding="utf-8")).get(
                "ip_address_last_two_octets"
            )
            if value:
                octets.add(value)
    for page in [*PAGES, WIKI / "index.md", WIKI / "log.md"]:
        text = page.read_text(encoding="utf-8")
        found = sorted(
            o
            for o in octets
            if re.search(rf"(?<![\w.]){re.escape(o)}(?![\w.]|\.\d)", text)
        )
        assert not found, f"{_rel(page)} carries the address octets {found}"


@pytest.mark.parametrize("page", PAGES, ids=_rel)
def test_repository_paths_exist(page: Path) -> None:
    """repo-paths-exist: a renamed or deleted file shows up as a stale page."""
    for path in REPO_PATH.findall(page.read_text(encoding="utf-8")):
        if any(c in path for c in "<>*{"):
            continue
        assert (REPO / path.rstrip(".,:;")).exists(), (
            f"{_rel(page)} names {path}, which does not exist"
        )
