#!/usr/bin/env python3
"""Build the body of the one survey issue from `device-survey/devices-wanted.md`.

A GitHub issue cannot embed a file from its repository, so
`.github/workflows/survey-issue.yml` writes this into the pinned issue on
every change to the list. It takes the list down to *Why each one*, which is
what a visitor needs; turns every relative link into an absolute one, since
a relative link in an issue points nowhere; and ends with a link to the whole
file. Prints to stdout; connects to nothing.

    python scripts/helpers/survey_issue_body.py [--repo owner/name] [--ref branch]
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "device-survey" / "devices-wanted.md"

#: Where the issue body stops: the detailed reasons stay in the file.
CUT = "## Why each one"

#: A Markdown link or image target that is relative: not a URL, not an
#: anchor, not a mail address.
RELATIVE = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)")


def body(text: str, repo: str, ref: str) -> str:
    """Return the issue body for the list `text`, linked into `repo` at `ref`."""
    base = f"https://github.com/{repo}/blob/{ref}/device-survey/"
    full = f"{base}devices-wanted.md"
    head, _sep, _rest = text.partition(CUT)

    def absolute(match: re.Match[str]) -> str:
        target = match.group(1)
        parts = []
        for part in f"device-survey/{target}".split("/"):
            if part == "..":
                parts.pop()
            elif part != ".":
                parts.append(part)
        return f"](https://github.com/{repo}/blob/{ref}/{'/'.join(parts)})"

    head = RELATIVE.sub(absolute, head)
    # The table's anchors point into the part that was cut off.
    head = re.sub(r"\]\(#", f"]({full}#", head)
    banner = (
        "> **This issue is the one place to send a survey.** Attach the "
        "document the survey writes as a comment. The list below is written "
        f"into this issue from [devices-wanted.md]({full}) whenever it "
        "changes, so edit the file, not the issue.\n\n"
    )
    return (
        banner
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
    print(body(SOURCE.read_text(encoding="utf-8"), args.repo, args.ref), end="")


if __name__ == "__main__":
    main()
