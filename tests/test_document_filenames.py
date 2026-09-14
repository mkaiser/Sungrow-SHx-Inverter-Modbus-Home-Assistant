"""A document from the button is named the way this repository names one.

Two tools write this format: `scripts/sungrow_scan/collect.py` from a
terminal, and the survey button inside Home Assistant. They already agree on
the schema, the probe table, the stand-in and the vocabulary. The filename was
the last thing they did not agree on, and it is the one a maintainer sees
first — twenty documents in a downloads folder sort by name or they do not
sort at all, and `doc/device-fingerprints/` should be able to take one without
renaming it.

`fingerprint.label_for` derives that name from the **published document
alone**, where the scanner derives it from the structures it holds before
publishing. The proof that the two arrive at the same answer is not a pair of
unit tests: it is the corpus. Every fingerprint this repository has committed
was named by the scanner, so re-deriving each name from its own file is a
check against nine real readings from four houses, including the awkward ones
— a slave with no battery of its own, a third-party pack, a dongle read twice.
"""

import json
from pathlib import Path

import pytest

from sungrow_modbus.fingerprint import label_for

FINGERPRINTS = sorted(
    (Path(__file__).resolve().parent.parent / "doc" / "device-fingerprints").glob(
        "*.json"
    )
)


def test_there_are_fingerprints_to_check_against() -> None:
    """Otherwise the parametrised test below passes by having nothing to do."""
    assert len(FINGERPRINTS) >= 5


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem[:40])
def test_a_committed_fingerprint_derives_its_own_filename(path: Path) -> None:
    """The name on disk, rebuilt from what is inside the file.

    A committed name may carry one extra part that the label never does: when
    a directory already holds that name from a *different* address, the
    scanner appends the address tail rather than overwriting. That is a
    property of the directory and not of the document — one dongle read on
    both its interfaces produces two legitimate readings with one label — so
    the suffix is allowed for, and nothing else is.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    label = label_for(document)

    assert path.stem == label or path.stem.startswith(f"{label}-"), (
        f"{path.name} does not derive from its own contents"
    )


def test_a_name_never_carries_the_real_serial_or_a_full_address() -> None:
    """The guard that matters, asserted on the deriver rather than on files.

    A filename is published exactly as a document is, and it is the easier
    place to leak: the document's fields were designed around what may be
    said, while a name is assembled from whatever is to hand. So the
    stand-in is used only when it says it is one — `anon-` cannot occur in a
    Sungrow serial — and a serial handed over in the wrong field is dropped
    rather than slugified into something that slides past a search for it.
    """
    document = {
        "device": {
            "device_type_code": "0x0E03",
            "output_type": "three phase 3P4L",
            # Not a stand-in: the shape of a real serial, in the field the
            # stand-in belongs in. The name must refuse it.
            "serial_anonymized_hashed": "A123456789",
        },
        "user_inputs": {"reporter": "somebody", "transport": "direct_lan"},
        "connection": {"verdict": "direct to the inverter's LAN port"},
        "capability_probes": {},
    }

    label = label_for(document)

    assert "a123456789" not in label
    assert "A123456789" not in label
    # And the parts that are safe are still there, so the refusal is
    # specific rather than the whole name collapsing.
    assert label.startswith("sh10rt-3p-somebody")
