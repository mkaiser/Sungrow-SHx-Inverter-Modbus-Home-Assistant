"""Which capabilities can be pinned on a firmware version, and which cannot.

The question the fingerprint collection exists to answer, asked by the
maintainer in the plan: *collect as many device fingerprints as possible to
be able to identify firmware-related capabilities.* Sungrow publishes no
release notes and its register specification has been proven unreliable in
both directions, so the only way to know is to compare readings.

Answering it needs a **pair**: two readings agreeing on model and transport
and differing only in firmware. This file tests the machinery that finds
those pairs and reports the differences -- including the case the committed
documents are actually in, which is that no such pair exists yet.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from generate_compatibility import (  # noqa: E402
    _attribution,
    _capability_marks,
    _comparable,
)

FINGERPRINTS = sorted((REPO / "doc" / "device-fingerprints").glob("*.json"))


def _document(**overrides) -> dict:
    """Return a minimal fingerprint, with the fields this analysis reads."""
    document = {
        "device": {"device_type_code": "0x0E03"},
        "user_inputs": {"transport": "direct_lan"},
        "firmware": {"inverter": "SAPPHIRE-H_B001.V000.P020"},
        "capability_probes": {
            "MPPT3 voltage": {"state": "unavailable"},
            "battery level": {"state": "present"},
        },
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key] = {**document[key], **value}
        else:
            document[key] = value
    return document


def test_a_reading_is_comparable_on_model_transport_and_firmware() -> None:
    """Three things have to be held still, because all three matter here.

    This project has measured every one of them changing what a device
    answers: the model decides which trackers exist, the transport decides
    what a WiNet-S forwards, and the firmware is the axis under test. Hold
    two and the third is attributable; hold fewer and nothing is.
    """
    assert _comparable(_document()) == (
        "SH10RT",
        "direct_lan",
        "SAPPHIRE-H_B001.V000.P020",
    )
    # A document whose firmware block did not read says so rather than
    # pretending -- four of the nine committed ones are in exactly that
    # state, refusing input 13249.
    assert _comparable(_document(firmware={"inverter": None}))[2] == "unknown"


def test_nothing_is_attributed_where_no_pair_exists() -> None:
    """The state the committed documents are in, and it is a finding.

    Every model here appears with exactly one firmware, so a difference
    between any two readings is also a model difference. Saying "nothing
    yet" is honest; saying nothing at all would let a reader assume the
    comparison had been made.
    """
    reports = [
        ("one", _document()),
        # A different model *and* a different firmware: not comparable.
        (
            "two",
            _document(
                device={"device_type_code": "0x0E13"},
                firmware={"inverter": "SAPPHIRE-H_B001.V000.P022"},
            ),
        ),
    ]
    text = "\n".join(_attribution(reports))
    assert "Nothing, yet" in text
    assert "cannot be" in text and "separated" in text
    # And it names what would unlock it, rather than asking for anything.
    # Matched on the words either side of the emphasis, since the sentence
    # reads "is **not** a new model".
    assert "a new model" in text
    assert "second reading of a model already here" in text
    # Each recorded model is named with the firmware it is stuck on, which is
    # the actionable half.
    assert "Any other firmware on one" in text


def test_a_pair_reports_only_what_actually_differs() -> None:
    """The half that will matter once somebody sends the second reading.

    Two readings, same model, same transport, different firmware. Only the
    probes whose answers differ are listed -- a table repeating twenty
    identical rows would bury the one that moved.
    """
    reports = [
        ("old", _document()),
        (
            "new",
            _document(
                firmware={"inverter": "SAPPHIRE-H_B001.V000.P022"},
                capability_probes={
                    "MPPT3 voltage": {"state": "present"},
                    "battery level": {"state": "present"},
                },
            ),
        ),
    ]
    text = "\n".join(_attribution(reports))

    assert "SH10RT, direct_lan" in text
    assert "MPPT3 voltage" in text, "the probe that moved must be listed"
    assert "battery level" not in text, (
        "a probe that answered the same way on both is not a firmware finding"
    )
    # Both versions are column headings, so a reader sees which way it moved.
    assert "SAPPHIRE-H_B001.V000.P020" in text
    assert "SAPPHIRE-H_B001.V000.P022" in text


def test_a_pair_that_differs_in_nothing_says_so() -> None:
    """A firmware change that moved nothing is worth recording too.

    It is the result that stops the next person re-measuring, and it is the
    likelier outcome: most firmware releases will not touch the registers
    this project reads.
    """
    reports = [
        ("old", _document()),
        ("new", _document(firmware={"inverter": "SAPPHIRE-H_B001.V000.P022"})),
    ]
    text = "\n".join(_attribution(reports))
    assert "No capability differs" in text
    assert "moved nothing this project reads" in text


def test_an_unknown_firmware_never_makes_a_pair() -> None:
    """Two readings whose firmware did not read are not a comparison.

    They would look like a pair -- same model, same transport, both
    "unknown" -- and any difference between them would be attributed to a
    firmware change that nobody has established. Four of the nine committed
    documents are in this state.
    """
    reports = [
        ("a", _document(firmware={"inverter": None})),
        (
            "b",
            _document(
                firmware={"inverter": None},
                capability_probes={"MPPT3 voltage": {"state": "present"}},
            ),
        ),
    ]
    text = "\n".join(_attribution(reports))
    assert "Nothing, yet" in text, text[:400]


def test_the_committed_documents_are_analysed_without_error() -> None:
    """The generator runs over the real corpus, whatever shape it is in."""
    reports = [
        (path.stem, json.loads(path.read_text(encoding="utf-8")))
        for path in FINGERPRINTS
    ]
    text = "\n".join(_attribution(reports))
    assert "What can be attributed to firmware" in text
    # Every committed document contributes a row to the "what exists" table.
    for _label, document in reports:
        model, transport, _firmware = _comparable(document)
        assert model in text, model
        assert transport in text, transport
    # And the marks helper reads real documents.
    for _label, document in reports:
        marks = _capability_marks(document)
        assert marks, "a committed fingerprint carries curated probes"
