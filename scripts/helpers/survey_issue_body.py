#!/usr/bin/env python3
"""Build the body of the one survey issue (#786).

A GitHub issue cannot embed a file from its repository, so
`.github/workflows/survey-issue.yml` writes this into the pinned issue on
every change to either source: the hand-written call for surveys in
`device-survey/survey-issue.md`, then `device-survey/devices-wanted.md` down
to *Why each one*. Every relative link becomes an absolute one and every
`<img src>` a raw file URL, since a relative path in an issue points
nowhere; it ends with a link to the whole list. Prints to stdout; connects to
nothing.

    python scripts/helpers/survey_issue_body.py [--repo owner/name] [--ref branch]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "device-survey" / "devices-wanted.md"
INTRO = REPO_ROOT / "device-survey" / "survey-issue.md"

#: Where the issue body stops: the detailed reasons stay in the file.
CUT = "## Why each one"

#: A Markdown link or image target that is relative: not a URL, not an
#: anchor, not a mail address.
RELATIVE = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")

#: An HTML image whose source is relative.
IMAGE = re.compile(r'(<img\s[^>]*src=")(?!https?://)([^"]+)(")')


def _resolve(target: str) -> str:
    """Return `target`, relative to `device-survey/`, as a repository path."""
    parts: list[str] = []
    for part in f"device-survey/{target}".split("/"):
        if part == "..":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def _absolute(text: str, repo: str, ref: str) -> str:
    """Point every relative link and image in `text` into `repo` at `ref`."""
    text = RELATIVE.sub(
        lambda m: f"](https://github.com/{repo}/blob/{ref}/{_resolve(m.group(1))})",
        text,
    )
    return IMAGE.sub(
        lambda m: (
            f"{m.group(1)}https://raw.githubusercontent.com/{repo}/{ref}/"
            f"{_resolve(m.group(2))}{m.group(3)}"
        ),
        text,
    )


def body(text: str, repo: str, ref: str, intro: str = "") -> str:
    """Return the issue body: `intro`, then the list `text`, linked into `repo`."""
    full = f"https://github.com/{repo}/blob/{ref}/device-survey/devices-wanted.md"
    head, _sep, _rest = text.partition(CUT)
    head = _absolute(head, repo, ref)
    # The table's anchors point into the part that was cut off.
    head = re.sub(r"\]\(#", f"]({full}#", head)
    banner = (
        "> **This issue is the one place to send a survey.** Attach the "
        "document the survey writes as a comment. This text is written into "
        "the issue from [survey-issue.md]"
        f"(https://github.com/{repo}/blob/{ref}/device-survey/survey-issue.md) "
        f"and [devices-wanted.md]({full}) whenever they change, so edit the "
        "files, not the issue.\n\n"
    )
    opening = _absolute(intro, repo, ref).rstrip() + "\n\n---\n\n" if intro else ""
    return (
        banner
        + opening
        + head.rstrip()
        + f"\n\nThe reasons for each line: [Why each one]({full}#why-each-one).\n"
    )


def main() -> None:
    """Print the body."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", default="mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"
    )
    parser.add_argument("--ref", default="proper-ha-integration")
    args = parser.parse_args()
    print(
        body(
            SOURCE.read_text(encoding="utf-8"),
            args.repo,
            args.ref,
            INTRO.read_text(encoding="utf-8"),
        ),
        end="",
    )


if __name__ == "__main__":
    main()
