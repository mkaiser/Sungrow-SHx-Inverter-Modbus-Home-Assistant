"""Decoding a wallbox's registers, which no manufacturer document describes.

Everything asserted here was measured on one AC22E-01 through a WiNet-S while
a car was charging and then finished charging, and cross-checked against the
two projects `doc/wallbox_registers.md` names. The words in `DUMP` below are
that reading, minus the six registers holding the serial -- which is the
point of the masking these tests also check.

The reason this file exists rather than trusting the table: a wallbox is the
rarest device this project sees, so the decode is exercised about once per
contributor. A scale that is wrong by a factor of ten would sit in a
fingerprint unnoticed and be read as evidence about somebody's hardware.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "sungrow_scan"))

from probe import (  # noqa: E402
    WALLBOX_DUMP_MASKED,
    WALLBOX_ENUMS,
    WALLBOX_FIELDS,
    _masked_dump,
    _wallbox_readings,
)

#: The measured session, at the moment it was charging at 3.4 kW. Register
#: numbers are one above these addresses.
DUMP = {
    "input": {
        # The serial's six registers, already masked as the document masks them.
        "21200": None,
        "21201": None,
        "21202": None,
        "21203": None,
        "21204": None,
        "21205": None,
        "21215": 16707,  # "AC"
        "21223": 16256,  # 0x3F80, the AC22E-01
        "21224": 1,
        "21261": 230,
        "21262": 320,
        "21269": 1,
        "21271": 1380,
        "21272": 22080,
        "21299": 17805,  # low word
        "21300": 4,  # high word: 4 * 65536 + 17805 = 279,949 Wh
        "21301": 2279,
        "21302": 150,
        "21303": 0,
        "21304": 0,
        "21305": 0,
        "21306": 0,
        "21307": 3407,
        "21308": 0,
        "21309": 613,
        "21310": 0,
        "21311": 597,
        "21312": 261,
        "21313": 1,
        "21316": 3,
        "21317": 16668,
        "21318": 27296,
        "21321": 160,
    },
    "holding": {
        "21202": 160,
        "21203": 1,
        "21210": 1,
        "21211": 0,
        "21231": 50,
    },
}


@pytest.fixture
def readings() -> dict:
    """Return the decoded session."""
    return _wallbox_readings(DUMP)


def test_the_session_reads_back_as_it_was_measured(readings) -> None:
    """The whole picture, in the units a person would say it in."""
    assert readings["charging_status"]["means"] == "charging"
    assert readings["charging_power"]["value"] == 3407
    assert readings["phase_a_voltage"]["value"] == 227.9
    assert readings["phase_a_current"]["value"] == 15.0
    assert readings["session_energy"]["value"] == 613
    assert readings["phase_mode"]["means"] == "single phase"


def test_the_lifetime_counter_is_thirty_two_bit_low_word_first(readings) -> None:
    """The disagreement this measurement settled.

    One project reads this as a word-swapped `uint32`, the other as 16-bit
    with the next register unrelated. Here the high word held 4 while the low
    word read 17805, and `4 * 65536 + 17805` is 279,949 Wh -- a plausible
    lifetime for the unit, moving in step with the power reading. Read the
    words the other way round and the same registers say 1.17 GWh.
    """
    assert readings["lifetime_energy"]["value"] == 279949
    assert readings["lifetime_energy"]["unit"] == "Wh"


def test_the_control_pilot_voltage_is_a_charging_state(readings) -> None:
    """5.97 V is IEC 61851 state C, and 9.03 V is state B.

    A hypothesis here until an independent measurement on an AC011E named the
    same address, which is why this reads `two sources` and not `measured
    here`.
    """
    assert readings["control_pilot_voltage"]["value"] == 5.97
    assert readings["control_pilot_voltage"]["unit"] == "V"

    idle = {"input": {**DUMP["input"], "21311": 903}}
    assert _wallbox_readings(idle)["control_pilot_voltage"]["value"] == 9.03


def test_a_timestamp_is_local_time_wearing_an_epoch_shape(readings) -> None:
    """Decoded as UTC it matched the wall clock, not UTC.

    So the rendered string carries no zone, because attaching one would be a
    claim the measurement cannot support -- and the note says as much in the
    document itself.
    """
    started = readings["charging_started"]
    assert started["local_time"] == "2026-09-08T17:08:44"
    assert "local clock" in started["note"]
    assert "+" not in started["local_time"], "no zone: none was established"


def test_the_model_comes_from_the_type_code(readings) -> None:
    """`0x3F80` is an AC22E-01, and the 22 kW maximum agrees with it."""
    assert readings["device_type_code"]["value"] == "0x3F80"
    assert readings["device_type_code"]["model"] == "AC22E-01"
    assert readings["maximum_charging_power"]["value"] == 22080


def test_a_register_nobody_can_name_is_published_anyway(readings) -> None:
    """Three measurements of this family and none of them knows what it is.

    Published under its register number, and marked `open`, because the next
    person to see one may recognise it -- and because an entity must not be
    invented for it.
    """
    entry = readings["unnamed_register_21313"]
    assert entry["value"] == 261
    assert entry["register"] == 21313
    assert entry["held"] == "open"


def test_no_reading_can_come_from_a_masked_register() -> None:
    """The serial cannot reach a reading, because the mask runs first.

    `_document` decodes the *masked* dump rather than the raw one, so this
    is a property of the order rather than of the field table -- and the
    field table not listing the serial is then a second line of defence
    instead of the only one.
    """
    unmasked = {
        "input": {
            **DUMP["input"],
            "21200": 16690,
            "21201": 13633,
            "21202": 13105,
            "21203": 12597,
            "21204": 14390,
            "21205": 12544,
        }
    }
    masked = _masked_dump(unmasked, WALLBOX_DUMP_MASKED)
    text = "".join(str(entry) for entry in _wallbox_readings(masked).values())
    assert "A25A" not in text
    # And even from the unmasked words, no field reads that range.
    assert "A25A" not in "".join(
        str(entry) for entry in _wallbox_readings(unmasked).values()
    )


def test_a_field_that_did_not_answer_is_absent_rather_than_zero() -> None:
    """An absent register is not a reading of nothing.

    Holding 21263 did not answer on this unit though a project names it. A
    fingerprint that published it as 0 would say the wallbox is in "network"
    working mode, which is a claim about somebody's configuration.
    """
    thin = {"input": {"21316": 3}}
    readings = _wallbox_readings(thin)
    assert set(readings) == {"charging_status"}


@pytest.mark.parametrize("field", WALLBOX_FIELDS, ids=lambda f: f[0])
def test_every_field_is_declared_completely(field) -> None:
    """Eight parts per row, and the enum kinds must exist.

    A typo in a `kind` would silently fall through to the plain integer
    branch, which is the one way this table can be wrong without failing.
    """
    name, space, address, count, kind, scale, _unit, held = field
    assert space in {"input", "holding"}
    assert 21200 <= address <= 21340, name
    assert count >= 1 and scale > 0
    assert held in {
        "three sources",
        "two sources",
        "measured here",
        "named elsewhere",
        "open",
    }, name
    if kind not in {"u16", "u32", "ascii", "hex", "local_epoch"}:
        assert kind in WALLBOX_ENUMS, f"{name} names a kind that does not exist"


def test_the_field_table_never_reads_the_serial() -> None:
    """The addresses the mask covers must not appear in the table at all.

    **Per space**, which the first version of this test forgot: holding 21202
    is the output current setting and input 21202 is part of the serial, and
    comparing the numbers alone failed on a table that was correct. Two
    address spaces sharing a numbering is exactly the sort of thing a
    space-blind check gets wrong in the safe direction and then, one day, in
    the other.
    """
    masked = {
        (space, address)
        for space, start, count in WALLBOX_DUMP_MASKED
        for address in range(start, start + count)
    }
    for name, space, address, count, *_ in WALLBOX_FIELDS:
        overlap = masked & {(space, a) for a in range(address, address + count)}
        assert not overlap, f"{name} reads masked addresses {sorted(overlap)}"
