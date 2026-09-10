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

import pytest

sys.path.insert(0, "scripts")

from sync_version import (
    NORMALISES_AWAY,
    VERSION,
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


@pytest.mark.parametrize("version", ["0.1.0a1", "0.1.0b2", "0.1.0rc1", "1.2.3"])
def test_a_normalised_pre_release_is_accepted(version: str) -> None:
    """The preview needs a version pip will not install by accident.

    `pip install sungrow-modbus` skips a pre-release unless asked with
    `--pre`, and HACS treats one as a beta a tester has to opt into. A low
    release number does not do that: `0.0.1` is simply the latest.
    """
    assert VERSION.match(version)


@pytest.mark.parametrize(
    "version",
    ["0.1.0-alpha.1", "0.1.0.beta", "0.1.0alpha1", "0.1.0-rc.1", "0.1.0_b1"],
)
def test_a_pre_release_pip_would_rewrite_is_refused(version: str) -> None:
    """The trap, and the reason this rejects spellings PEP 440 allows.

    pip normalises every one of these to something else -- `0.1.0-alpha.1`
    becomes `0.1.0a1` -- and Home Assistant compares the manifest's pin
    against the version actually *installed*. So a pyproject in one spelling
    and an installed distribution in another stop matching, and the config
    flow dies with `RequirementsNotFound` when somebody clicks Add
    integration. That is the failure this whole script exists to prevent,
    arriving by a new route, which is why these are refused with the reason
    rather than accepted and left to drift.
    """
    assert not VERSION.match(version)
    assert NORMALISES_AWAY.match(version), (
        f"{version} is refused, but without the explanation that names the "
        "normalised form to use instead"
    )


def test_nonsense_is_still_just_refused() -> None:
    """Not every rejection is a pre-release spelling."""
    assert not VERSION.match("nonsense")
    assert not NORMALISES_AWAY.match("nonsense")
