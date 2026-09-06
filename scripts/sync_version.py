#!/usr/bin/env python3
"""Keep the integration's two version strings in lockstep.

The version lives in exactly one place — ``pyproject.toml`` — and is mirrored
into ``custom_components/sungrow_modbus/manifest.json``. They must be identical:
Home Assistant checks the installed version of the ``requirements`` entry on
every start and will try to pip-install the library if the manifest asks for a
version that is not installed. In a devcontainer, where the library is
installed editable from this repo, that means a broken start-up.

This script is the single place that knows that rule, and it is used three
ways:

    scripts/sync_version.py            # write pyproject's version into the manifest
    scripts/sync_version.py --check    # verify they agree; exit 1 if not (CI)
    scripts/sync_version.py --set 0.2.0    # bump both, for a release

Tag ``vX.Y.Z`` on top of a ``--set`` commit and the release workflow verifies
the tag against these files before it publishes anything.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

REPO = Path(__file__).resolve().parent.parent
PYPROJECT = REPO / "pyproject.toml"
MANIFEST = REPO / "custom_components" / "sungrow_modbus" / "manifest.json"

#: The library is pinned exactly in the manifest's requirements, so that string
#: has to move with the version too.
REQUIREMENT_NAME = "sungrow-modbus"

SEMVER = re.compile(r"^\d+\.\d+\.\d+([-.][0-9A-Za-z.]+)?$")


def _read(path: Path) -> tuple[str, str]:
    """Return a file's text plus the line ending it uses.

    This repo has a Windows history and holds a mix of LF and CRLF files.
    Rewriting one with the wrong ending turns a one-line version bump into a
    whole-file diff, so every write here round-trips what it found.
    """
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n"), newline


def _write(path: Path, text: str, newline: str) -> None:
    """Write text back with the line ending the file already had."""
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def installed_version() -> str | None:
    """Return the version of the library installed in this environment."""
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - importlib.metadata is stdlib
        return None
    try:
        return version(REQUIREMENT_NAME)
    except PackageNotFoundError:
        return None


def reinstall_editable(version: str) -> None:
    """Re-install the library so its metadata matches the new version.

    Bumping pyproject.toml does not touch the metadata of an already-installed
    editable package, and Home Assistant compares the manifest's pin against
    what is *installed*. So a bump alone leaves the devcontainer asking pip for
    a version that does not exist yet on PyPI, and the config flow dies with
    `RequirementsNotFound` at the moment somebody clicks Add integration —
    nowhere near the version bump that caused it.

    Doing it here rather than warning about it, because there is no case where
    you want the bump without it.
    """
    if installed_version() is None:
        return
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps", "-q"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            f"Could not re-install the library at {version}. Home Assistant "
            f"will fail to load the integration until you run:\n"
            f"  python -m pip install -e . --no-deps\n{result.stderr}",
            file=sys.stderr,
        )
        return
    print(f"Re-installed the library so the environment reports {version} too")


def project_version() -> str:
    """Return the version declared in pyproject.toml."""
    text, _ = _read(PYPROJECT)
    return str(tomllib.loads(text)["project"]["version"])


def manifest_data() -> dict:
    """Return the integration manifest as a dict."""
    text, _ = _read(MANIFEST)
    return json.loads(text)


def manifest_requirement_version(manifest: dict) -> str | None:
    """Return the version pinned for the device library in `requirements`."""
    for requirement in manifest.get("requirements", []):
        name, _, version = requirement.partition("==")
        if name.strip() == REQUIREMENT_NAME:
            return version.strip() or None
    return None


def write_pyproject(version: str) -> None:
    """Rewrite only the project's own version line, leaving the rest alone."""
    text, newline = _read(PYPROJECT)
    new_text, count = re.subn(
        r'(?m)^version = "[^"]*"$', f'version = "{version}"', text, count=1
    )
    if count != 1:
        raise SystemExit(f"Could not find a version line to replace in {PYPROJECT}")
    _write(PYPROJECT, new_text, newline)


def write_manifest(version: str) -> None:
    """Mirror the version into the manifest, keeping key order and formatting.

    Home Assistant's hassfest enforces manifest key order, so this edits the
    text in place rather than re-serialising the parsed dict.
    """
    text, newline = _read(MANIFEST)
    text, version_count = re.subn(
        r'(?m)^(\s*"version":\s*")[^"]*(")', rf"\g<1>{version}\g<2>", text, count=1
    )
    text, requirement_count = re.subn(
        rf'("{REQUIREMENT_NAME}==)[^"]*(")', rf"\g<1>{version}\g<2>", text, count=1
    )
    if version_count != 1:
        raise SystemExit(f'No "version" key found in {MANIFEST}')
    if requirement_count != 1:
        raise SystemExit(f"No pinned {REQUIREMENT_NAME} requirement in {MANIFEST}")
    _write(MANIFEST, text, newline)


def check(expected: str | None = None) -> int:
    """Report whether every version string agrees. Returns a process exit code."""
    version = project_version()
    manifest = manifest_data()
    problems: list[str] = []

    installed = installed_version()
    if installed is not None and installed != version:
        problems.append(
            f"the installed library is {installed!r}, the files say {version!r} "
            "-- Home Assistant will try to pip-install the pinned version and "
            "fail; run: python -m pip install -e . --no-deps"
        )
    if manifest.get("version") != version:
        problems.append(
            f'manifest "version" is {manifest.get("version")!r}, '
            f"pyproject.toml says {version!r}"
        )
    pinned = manifest_requirement_version(manifest)
    if pinned != version:
        problems.append(
            f"manifest pins {REQUIREMENT_NAME}=={pinned}, "
            f"pyproject.toml says {version!r}"
        )
    if expected is not None and expected != version:
        problems.append(f"release tag says {expected!r}, the files say {version!r}")

    if problems:
        print(f"Version mismatch ({len(problems)}):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nRun scripts/sync_version.py to mirror pyproject.toml into the "
            "manifest, or scripts/sync_version.py --set X.Y.Z to bump both.",
            file=sys.stderr,
        )
        return 1

    print(f"Version {version} is consistent across pyproject.toml and manifest.json")
    return 0


def main() -> int:
    """Sync, check or set the version."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--check",
        action="store_true",
        help="verify the versions agree without writing anything",
    )
    group.add_argument("--set", metavar="X.Y.Z", help="set the version everywhere")
    parser.add_argument(
        "--expect",
        metavar="X.Y.Z",
        help="with --check, also require this version (used by the release workflow)",
    )
    args = parser.parse_args()

    if args.set:
        if not SEMVER.match(args.set):
            raise SystemExit(f"Not a version number: {args.set}")
        write_pyproject(args.set)
        write_manifest(args.set)
        print(f"Set version {args.set} in pyproject.toml and manifest.json")
        reinstall_editable(args.set)
        return 0

    if args.check:
        return check(args.expect)

    version = project_version()
    write_manifest(version)
    print(f"Mirrored version {version} into {MANIFEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
