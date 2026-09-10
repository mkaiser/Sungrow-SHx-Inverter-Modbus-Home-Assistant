"""Two producers of one document format, held to one definition.

`scripts/sungrow_scan/probe.py` keeps literal copies of the probe table, the
firmware table, the schema number and the stand-in derivation, because that
directory ships as a zip a stranger runs on bare Python and must not import
this library. The integration reads the library's copies, because it can.

The duplication is a deliberate trade -- a survey that cannot run standalone
is a worse problem than two tables -- and the whole trade rests on this file.
Without it the two drift, and the failure is silent and nasty: a probe label
is part of the published format, so renaming one on one side unrelates every
new reading from every old one in `doc/compatibility.md`, and a divergent
stand-in gives one machine two identities depending on which tool read it.

The same pattern, and the same reasoning, as `IDENTIFY_UNITS` in
`custom_components/sungrow_modbus/const.py`.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

import probe  # noqa: E402

from sungrow_modbus import fingerprint  # noqa: E402


def test_the_two_producers_agree_on_the_probe_table() -> None:
    """Label, space, address, count and axis, in order.

    Order too, because the document is written in this order and a reader
    comparing two files by eye should not have to sort them first.
    """
    assert list(fingerprint.PROBES) == [tuple(row) for row in probe.FINGERPRINT]


def test_the_two_producers_agree_on_the_firmware_table() -> None:
    """Including which name each string is published under."""
    assert list(fingerprint.FIRMWARE_STRINGS) == [tuple(r) for r in probe.FIRMWARE]


def test_the_two_producers_agree_on_the_schema() -> None:
    """A document's schema number is a claim about its shape, not its tool."""
    assert fingerprint.SCHEMA == probe.SCHEMA


def test_the_two_producers_agree_on_the_stand_in() -> None:
    """One device, one stand-in, whichever tool read it.

    Checked over several shapes rather than one: the derivation takes as many
    digits as the real serial had, so a length disagreement would only show
    on some inputs.
    """
    for serial in ("A123456789", "A987654321", "A25A123456", "A1", ""):
        assert fingerprint.stand_in(serial) == probe._fake_serial(serial), serial


def test_the_two_producers_agree_on_what_is_never_published() -> None:
    """The list that keeps a serial out of a key name as well as a value."""
    assert tuple(fingerprint.NEVER_PUBLISH) == tuple(probe.NEVER_PUBLISH)


def test_the_two_producers_agree_on_the_stand_in_prefix() -> None:
    """`anon-` is what makes the value self-describing wherever it lands."""
    assert fingerprint.STAND_IN_PREFIX == probe.STAND_IN_PREFIX


def test_the_two_producers_agree_on_the_unavailable_sentinels() -> None:
    """What "not here" looks like decides what every probe state means."""
    assert set(fingerprint.UNAVAILABLE) == set(probe.UNAVAILABLE)


def test_the_two_producers_agree_on_the_output_types() -> None:
    """Register 5002's words, which no model table can answer."""
    assert dict(fingerprint.OUTPUT_TYPES) == dict(probe.OUTPUT_TYPE)


def test_the_two_producers_agree_on_the_wifi_sentence() -> None:
    """Byte for byte, because a difference here would look like a finding.

    `wifi_or_ethernet` is the same sentence in every document: it says the
    question cannot be answered over Modbus and why latency cannot stand in.
    Two spellings of that would read, to somebody diffing two files, as
    though something had been established.
    """
    assert fingerprint.WIFI_OR_ETHERNET == probe.WIFI_OR_ETHERNET


def test_the_two_producers_agree_on_the_transport_verdict() -> None:
    """All four rows of the truth table, not just the two common ones.

    `doc/compatibility.md` groups readings by this exact string, so two
    spellings of one route would split a comparison in half and the halves
    would each look like insufficient evidence.
    """
    for answered in (True, False):
        for named in (True, False):
            assert fingerprint.transport_verdict(
                answered_6100=answered, module_named=named
            ) == probe.transport_verdict(answered_6100=answered, module_named=named), (
                answered,
                named,
            )


def test_every_probe_state_the_committed_documents_use_is_a_known_one() -> None:
    """The vocabulary is part of the format, so it is closed.

    `refused` and `no answer` are the pair worth keeping apart: one is the
    device saying the register is not there, the other is nothing coming
    back, and only the first is evidence about a register.
    """
    import json

    seen = set()
    for path in (REPO / "doc" / "device-fingerprints").glob("*.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        for entry in (document.get("capability_probes") or {}).values():
            if isinstance(entry, dict) and entry.get("state"):
                seen.add(entry["state"])

    assert seen, "there should be committed documents with probe states"
    assert seen <= {state.value for state in fingerprint.State}, seen


def test_the_probe_addresses_are_protocol_addresses() -> None:
    """One below the register number the label quotes, every time.

    Nine of the labels name their register explicitly, which makes them
    checkable: `device type code (5000)` must read address 4999. This is the
    off-by-one that this project's comments warn about most often, and the
    table is where getting it wrong would be least visible.
    """
    import re

    checked = 0
    for label, _space, address, _count, _axis in fingerprint.PROBES:
        match = re.search(r"\((\d{4,5})", label)
        if match is None:
            continue
        assert address == int(match.group(1)) - 1, label
        checked += 1
    assert checked >= 5, "the self-describing labels should be the majority"
