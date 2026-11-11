#!/usr/bin/env python3
"""Find tracked files whose working copy has CRLF where the repository has LF.

The usual cause: the repository was cloned by Git for Windows, whose
`core.autocrlf=true` writes CRLF on checkout, and then opened in the
devcontainer. Inside Linux every such file shows as modified, a script's
shebang line breaks and a test comparing bytes fails. `.gitattributes` now
asks for LF everywhere, which a fresh checkout honours; this repairs one made
before it.

A file is wrong when Git stores it with LF and the working copy has CRLF,
unless `.gitattributes` asks for CRLF (`*.cmd`, `*.ps1`). A file Git stores
with CRLF is left as it is: the raw diagnoses are kept byte for byte.

    python3 scripts/dev/check_line_endings.py          # list; exit 1 if any
    python3 scripts/dev/check_line_endings.py --fix    # strip the CRs

`--fix` changes nothing but line endings, so uncommitted work in a file
survives it. It then refreshes the index entry of every file Git reports as
changed whose content matches the repository's: after a conversion the index
still holds the CRLF file's size, and Git counts a file whose size changed
as modified without comparing its content. A file with uncommitted changes
keeps its entry, so nothing is ever staged.

The devcontainer's `scripts/dev/setup.sh` runs it with `--fix`, and
`make quick` runs the check.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]


def wrong_endings() -> list[Path]:
    """Return the tracked files checked out with CRLF that Git stores as LF."""
    listing = subprocess.run(
        ["git", "ls-files", "--eol", "-z"],
        cwd=REPO,
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    found: list[Path] = []
    for record in filter(None, listing.split("\0")):
        info, _, name = record.partition("\t")
        # `i/lf w/crlf attr/text eol=crlf`: the attributes are the rest,
        # and may be more than one word.
        index, worktree, *attributes = info.split()
        if index == "i/lf" and worktree in ("w/crlf", "w/mixed"):
            if "eol=crlf" in attributes:
                continue
            found.append(REPO / name)
    return found


def _git(*args: str, data: str | None = None) -> str:
    """Run git in the repository and return its output."""
    return subprocess.run(
        ["git", *args],
        cwd=REPO,
        input=data,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def refresh_unchanged(paths: list[Path]) -> int:
    """Refresh the index entries of `paths` whose content is the index's.

    Returns how many were refreshed. Content is compared by blob id, the
    working copy's through Git's own clean filter, so the comparison is the
    one `git add` would make; only an identical file's entry is rewritten,
    which changes its stat data and nothing else.
    """
    names = [str(path.relative_to(REPO)) for path in paths]
    if not names:
        return 0
    staged = {}
    for line in _git("ls-files", "-s", "-z", "--", *names).split("\0"):
        if line:
            info, _, name = line.partition("\t")
            staged[name] = info.split()[1]
    working = _git("hash-object", "--stdin-paths", data="\n".join(names) + "\n")
    same = [
        name
        for name, blob in zip(names, working.split(), strict=True)
        if staged.get(name) == blob
    ]
    for start in range(0, len(same), 200):
        _git("update-index", "-q", "--", *same[start : start + 200])
    return len(same)


def fix() -> tuple[int, int]:
    """Strip the CRs, then refresh stale index entries: (converted, refreshed)."""
    found = wrong_endings()
    for path in found:
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    changed = [
        REPO / name
        for name in _git("diff-files", "--name-only", "-z").split("\0")
        if name and (REPO / name).is_file()
    ]
    return len(found), refresh_unchanged(changed)


def main() -> int:
    """List the files, or fix them; exit 1 when some are wrong and unfixed."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fix", action="store_true", help="strip the CRs")
    args = parser.parse_args()

    if args.fix:
        converted, refreshed = fix()
        if converted or refreshed:
            print(
                f"Converted {converted} file(s) from CRLF to LF; refreshed "
                f"{refreshed} index entr{'y' if refreshed == 1 else 'ies'}"
            )
        return 0
    found = wrong_endings()
    if found:
        for path in found:
            print(path.relative_to(REPO))
        print(
            f"{len(found)} file(s) checked out with CRLF where the repository "
            "has LF. Fix: python3 scripts/dev/check_line_endings.py --fix",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
