"""The committed wallbox documents, held to what the survey promises of one.

A wallbox read at its own address is published beside the inverter documents
in `device-survey/`, but it has no `device`, so neither `label_for`
nor the compatibility table can read it (`tests/corpus.py` splits the two).
The checks the inverter corpus gets from `test_document_filenames.py` and
`test_no_real_serials.py` are restated here, on the document's own terms.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from sungrow_modbus.dump import WALLBOX_MASKED
from sungrow_modbus.survey_document import STAND_IN_PREFIX

SURVEY = Path(__file__).resolve().parents[1] / "device-survey" / "scripts" / "python"
sys.path.insert(0, str(SURVEY))

import wallbox_direct  # noqa: E402

from .corpus import WALLBOX_DOCUMENTS as DOCUMENTS  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_there_are_wallbox_documents_to_check() -> None:
    """Otherwise every parametrised test below passes by having nothing to do."""
    assert DOCUMENTS


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_a_wallbox_document_derives_its_own_filename(path: Path) -> None:
    assert path.stem == wallbox_direct.label_for(_load(path))


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_a_wallbox_document_is_one_and_says_so(path: Path) -> None:
    """A wallbox document, not an inverter document that lost its device."""
    document = _load(path)

    assert document["document"] == "wallbox"
    assert "device" not in document
    assert document["wallbox"]["path"] in ("tls", "dongle")


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_a_wallbox_document_carries_a_stand_in(path: Path) -> None:
    stand_in = _load(path)["wallbox"]["serial_anonymized_hashed"]

    assert stand_in.startswith(STAND_IN_PREFIX)


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_every_masked_register_is_empty_in_the_dump(path: Path) -> None:
    """The serial and the short code at 21210 are published as null, never as words.

    Present as keys, so a reader can see they were masked rather than
    unread; empty, so nothing of them is published.
    """
    dump = _load(path)["wallbox"]["register_dump"]

    for space, start, count in WALLBOX_MASKED:
        for address in range(start, start + count):
            assert dump[space].get(str(address)) is None, (space, address)


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda p: p.stem)
def test_a_wallbox_document_holds_no_full_address(path: Path) -> None:
    """Only the tail its owner agreed to, or the placeholder."""
    document = _load(path)
    text = path.read_text(encoding="utf-8")

    assert "192.168." not in text
    tail = document["ip_address_last_two_octets"]
    assert tail == "xxx.xxx" or len(tail.split(".")) == 2
