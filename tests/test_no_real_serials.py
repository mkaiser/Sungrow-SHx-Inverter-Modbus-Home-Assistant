"""No real device serial may reach the tracked tree.

The fingerprint documents were designed around this: every published one
carries a **stand-in**, `serial_anonymized_hashed`, and the real serial goes
only to `.testdata/`, which is gitignored. `RAW_DIR` is fixed in `probe.py`
so `--save doc/device-fingerprints` cannot put a real one there even if asked.

None of that covered the **source tree**, and that gap nearly published six
of them. Over one session, real serials from four houses -- three of them
other people's -- arrived in test fixtures and in docstrings illustrating a
bug, and were about to be pushed to a public repository. Every one was a
fixture or an example; not one needed to be real.

So this asserts the property directly, over every file git tracks. It embeds
no real serial -- doing that would be the thing it is preventing -- and
instead matches the **shape** of one and requires each hit to be on a list of
strings known to be fabricated. A new serial in a test therefore fails until
somebody adds it here deliberately, which is the moment to ask whether it is
real.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

import pytest

REPO = Path(__file__).resolve().parent.parent

#: What a Sungrow serial looks like: `A`, then ten upper-case alphanumerics.
#:
#: Matched by shape rather than by value, because the alternative is a list of
#: the real ones -- in the file whose job is to keep them out.
SERIAL_SHAPE = re.compile(r"\bA[0-9A-Z]{10}\b")

#: Serial-shaped strings that are known to be invented, and why each exists.
#:
#: Adding to this list is a deliberate act. If a new one appears because a
#: real device was read, it does not belong here -- it belongs in
#: `.testdata/`, and the fixture belongs in this list instead.
FABRICATED = {
    # Deliberately unmistakable, and deliberately reused: one placeholder
    # across conftest, the simulator seed, probe.py's docstrings and the
    # two-inverter topology tests. An earlier round gave each site its own
    # plausible-looking serial, which is exactly the wrong shape for a
    # fixture -- a reader cannot tell an invented serial from a real one when
    # it is shaped like a real one, and neither can a reviewer. Nothing in
    # this project depends on a serial being plausible.
    #
    # (Naming an example of one here would fail this file's own first test,
    # which is the guard working: a serial-shaped string is not allowed in a
    # tracked file merely because the prose around it says it is fake.)
    "A123456789": "the placeholder serial, everywhere one is needed",
    # A second one, because several tests assert that two devices differ.
    "A987654321": "a distinct second serial, for the 'not equal' assertions",
    # Wallbox serials begin `A25A`, and one test decodes that prefix.
    "A25A123456": "a wallbox, whose serials start A25A",
    # Not a device serial at all: what the abandoned letter-preserving
    # anonymiser produced from a serial, kept as the illustration of why it
    # was abandoned. Recomputed when the input became the placeholder above,
    # so the illustration stays true to its own algorithm.
    "A5155200572": "the wrong stand-in the `anon-` prefix replaced",
}


def _tracked() -> list[Path]:
    """Return every file git tracks, which is exactly what a push publishes."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    ).stdout
    return [REPO / name for name in out.split("\0") if name]


@pytest.mark.parametrize("path", _tracked(), ids=lambda p: p.name)
def test_no_unrecognised_serial_shaped_string_is_tracked(path: Path) -> None:
    """Every serial-shaped string in the tree is one we know we invented."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        pytest.skip("not readable as text")

    unknown = sorted(set(SERIAL_SHAPE.findall(text)) - set(FABRICATED))
    assert not unknown, (
        f"{path.relative_to(REPO)} contains {', '.join(unknown)}, which looks "
        "like a device serial and is not on the fabricated list in "
        "tests/test_no_real_serials.py.\n\n"
        "If it came off real hardware it must not be committed: the real "
        "serial belongs in .testdata/, and a fingerprint publishes the "
        "stand-in instead. If you invented it, add it to FABRICATED with a "
        "note saying what it is for."
    )


def test_the_fabricated_list_has_no_dead_entries() -> None:
    """An entry left behind by a rename would stop guarding anything.

    And worse than nothing: it would sit there looking like an assurance that
    some string is accounted for, when nothing uses it any more.
    """
    tracked = " ".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in _tracked()
        if path.is_file()
    )
    dead = sorted(serial for serial in FABRICATED if serial not in tracked)
    assert not dead, f"no longer used anywhere: {', '.join(dead)}"


def test_the_published_fingerprints_carry_stand_ins_and_nothing_else() -> None:
    """The documents' own rule, restated where the tree-wide one lives.

    `test_fingerprint_label.py` asserts this per document as part of the
    publishing gate. Repeated here because this file is where somebody will
    look after a near-miss, and the two halves belong together: a stand-in in
    the document, and nothing serial-shaped in the source.
    """
    documents = sorted((REPO / "doc" / "device-fingerprints").glob("*.json"))
    assert documents, "there should be committed fingerprints to check"
    for path in documents:
        text = path.read_text(encoding="utf-8")
        assert "serial_anonymized_hashed" in text, path.name
        unknown = sorted(set(SERIAL_SHAPE.findall(text)) - set(FABRICATED))
        assert not unknown, f"{path.name} carries {unknown}"
