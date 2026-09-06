"""The integration's version strings must never drift apart.

Home Assistant checks the installed version of every `requirements` entry on
start-up, and pip-installs the package if the manifest asks for a version that
is not present. With the device library installed editable from this repo, a
manifest that disagrees with `pyproject.toml` therefore breaks start-up — so
this is a release-blocking invariant, not a tidiness rule.

The release workflow runs the same check against the git tag.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "scripts")

from sync_version import (
    check,
    manifest_data,
    manifest_requirement_version,
    project_version,
)


def test_manifest_version_matches_pyproject() -> None:
    assert manifest_data()["version"] == project_version()


def test_manifest_pins_the_library_at_the_same_version() -> None:
    assert manifest_requirement_version(manifest_data()) == project_version()


def test_check_reports_success() -> None:
    assert check() == 0


def test_check_rejects_a_mismatched_release_tag() -> None:
    assert check("99.99.99") == 1
