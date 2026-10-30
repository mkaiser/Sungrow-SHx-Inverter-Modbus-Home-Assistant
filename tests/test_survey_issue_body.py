"""The survey issue's body: the call for surveys and the list's top, linked."""

from __future__ import annotations

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "helpers"))

import survey_issue_body

REPO = "owner/name"
REF = "branch"


def _body() -> str:
    text = survey_issue_body.SOURCE.read_text(encoding="utf-8")
    intro = survey_issue_body.INTRO.read_text(encoding="utf-8")
    return survey_issue_body.body(text, REPO, REF, intro)


def test_the_body_stops_before_the_reasons() -> None:
    body = _body()
    assert "## Most wanted" in body
    assert "## Why each one" not in body
    assert len(body) < 65536, "GitHub refuses an issue body over 65536 characters"


def test_no_link_in_the_body_is_relative() -> None:
    targets = re.findall(r"\]\(([^)\s]+)\)", _body())
    assert targets
    assert all(t.startswith(("https://", "mailto:")) for t in targets), [
        t for t in targets if not t.startswith(("https://", "mailto:"))
    ]


def test_a_parent_link_resolves_to_the_file_it_names() -> None:
    body = survey_issue_body.body("[c](../doc/compatibility.md)\n", REPO, REF)
    assert f"https://github.com/{REPO}/blob/{REF}/doc/compatibility.md" in body


def test_every_absolute_link_names_a_file_that_exists() -> None:
    prefix = f"https://github.com/{REPO}/blob/{REF}/"
    repo_root = survey_issue_body.REPO_ROOT
    for target in re.findall(r"\]\(([^)\s]+)\)", _body()):
        if target.startswith(prefix):
            path = target[len(prefix) :].split("#")[0]
            assert (repo_root / path).exists(), path


def test_the_call_for_surveys_comes_first() -> None:
    body = _body()
    assert body.index("Hi everyone!") < body.index("## Most wanted")


def test_an_image_becomes_a_raw_file_url() -> None:
    body = survey_issue_body.body(
        "", REPO, REF, '<img src="images/a.png" width="400">\n'
    )
    raw = f"https://raw.githubusercontent.com/{REPO}/{REF}"
    assert f'src="{raw}/device-survey/images/a.png"' in body
