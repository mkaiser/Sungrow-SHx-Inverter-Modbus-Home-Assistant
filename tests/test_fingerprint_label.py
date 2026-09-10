"""What one word of a fingerprint's filename is allowed to claim.

The filename is the only part of a fingerprint anybody reads before opening
it, and `doc/compatibility.md` turns it into a table row. So a word in it is a
published claim about somebody's hardware, and the rule is that it says only
what was measured.

The case that forced this file: a slave inverter in a master/slave cluster
answers **0** for every battery register, because the battery belongs to the
master. Zero decodes to a value, so it was published as `battery-thirdparty`
-- a third-party battery on a machine with no battery at all.
"""

from __future__ import annotations

import builtins
import contextlib
import json
from pathlib import Path
import re
import shlex
import sys

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent / "scripts" / "sungrow_scan")
)

from probe import (
    NEVER_PUBLISH,
    SCRIPT,
    _all_zero,
    _battery_token,
    _derive_label,
    _firmware_token,
    _last_two_octets,
    _slug,
    transport_verdict,
)

REPO = Path(__file__).resolve().parent.parent


@contextlib.contextmanager
def _answering(answers: list[str]):
    """Feed `input` a fixed list of answers for the duration of the block."""
    supply = iter(answers)
    original = builtins.input

    def fake(_prompt: str = "") -> str:
        return next(supply)

    builtins.input = fake
    try:
        yield
    finally:
        builtins.input = original


DIRECT = {"verdict": "direct to the inverter's LAN port"}
DONGLE = {"verdict": "behind a WiNet-S dongle"}


def _fingerprint(module_block: str, battery: str) -> dict:
    return {
        "registers": {
            "unit 200 SBR battery module block": module_block,
            "battery voltage": battery,
            "battery level": battery,
        }
    }


def test_a_cluster_slave_answering_zero_has_no_battery() -> None:
    # Measured on a real pair of SH10RT-V112 over VPN: unit 200 silent, the
    # connection direct, and every battery register zero. Silence at unit 200
    # on a direct path is evidence of a third-party pack -- but only if there
    # is a pack, and the zeros say there is not.
    fingerprint = _fingerprint("no answer", "present")
    raw = {"registers": {"battery voltage": [0], "battery level": [0]}}
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-none"


def test_a_third_party_pack_is_still_named() -> None:
    # The maintainer's own inverter: a Pylontech answers the battery
    # registers, and unit 200 stays silent because it is not a Sungrow pack.
    fingerprint = _fingerprint("no answer", "present")
    raw = {"registers": {"battery voltage": [1992], "battery level": [1000]}}
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-thirdparty"


def test_behind_a_dongle_the_same_silence_claims_nothing() -> None:
    fingerprint = _fingerprint("no answer", "present")
    raw = {"registers": {"battery voltage": [1992], "battery level": [1000]}}
    assert _battery_token(fingerprint, DONGLE, raw) == "battery-unknown"


def test_a_sungrow_pack_that_answers_unit_200_names_its_family() -> None:
    fingerprint = _fingerprint("present", "present")
    raw = {
        "registers": {
            "battery voltage": [1995],
            "battery level": [1000],
            "battery capacity (5639)": [960],
        }
    }
    # The model, not just the family: 9.6 kWh is SBR096 and nothing else,
    # and the pack's own module arrays showed three of eight slots filled.
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-sbr096"


def test_the_sentinel_remains_the_ordinary_way_to_say_no_battery() -> None:
    fingerprint = _fingerprint("no answer", "unavailable")
    raw = {"registers": {"battery voltage": [0xFFFF], "battery level": [0xFFFF]}}
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-none"


def test_one_zero_among_readings_is_a_measurement_not_an_absence() -> None:
    # An idle pack reports 0 current at a real voltage. Requiring every named
    # register to be zero is what keeps that a reading.
    raw = {"registers": {"battery voltage": [1992], "battery level": [0]}}
    assert not _all_zero(raw, ("battery voltage", "battery level"))


def test_a_register_that_never_answered_is_not_a_zero() -> None:
    # A missing key means the read failed, which is `battery-unreadable`
    # territory and must not be smoothed into a confident "no battery".
    assert not _all_zero({"registers": {}}, ("battery voltage",))


def test_a_capacity_matching_no_model_stays_at_the_family() -> None:
    # Certainly Sungrow -- unit 200 answered -- but 18.0 kWh is not an SBR or
    # an SBH size, so naming one would be inventing it.
    fingerprint = _fingerprint("present", "present")
    raw = {
        "registers": {
            "battery voltage": [1995],
            "battery level": [1000],
            "battery capacity (5639)": [1800],
        }
    }
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-sungrow"


def test_an_sbh_is_named_from_the_same_table() -> None:
    # No SBH has been measured; this pins the table lookup, not the hardware.
    fingerprint = _fingerprint("present", "present")
    raw = {
        "registers": {
            "battery voltage": [3200],
            "battery level": [500],
            "battery capacity (5639)": [2000],
        }
    }
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-sbh200"


def test_the_host_octets_are_zero_filled_strings_of_three_digits() -> None:
    # Strings because JSON cannot write a leading zero on a number, and three
    # digits because that is the widest an octet gets -- so every value is the
    # same width and sorts as text in the order an address sorts.
    assert _last_two_octets("192.168.176.34") == "176.034"
    assert _last_two_octets("192.168.176.28") == "176.028"
    assert _last_two_octets("10.0.0.4") == "000.004"
    assert _last_two_octets("10.0.0.128") == "000.128"


def test_something_that_is_not_an_ipv4_address_has_no_octets() -> None:
    # A hostname and an IPv6 address are both ordinary things to point the
    # script at, and neither has octets. None beats guessing at whatever
    # follows the final dots.
    assert _last_two_octets("winet-s.local") is None
    assert _last_two_octets("fe80::1") is None
    assert _last_two_octets("") is None


def test_the_octets_are_only_the_octets() -> None:
    # The document exists not to carry the host. Two octets of a subnet nobody
    # has named is not an address, and the front half must not come with it.
    assert "192.168" not in (_last_two_octets("192.168.176.34") or "")


def test_the_address_tail_is_withheld_unless_its_owner_allowed_it() -> None:
    """Consent that was never asked for is not consent.

    The third octet is what separates one contributor's network from
    another's -- three installations on record sit on 192.168.178 and two on
    192.168.176 -- so it is the more revealing half and the owner's to give.
    `xxx.xxx` is a truthful answer where a real value would be a guess about
    what somebody is willing to publish.
    """
    from probe import _address_tail

    assert _address_tail({"host": "192.168.178.105"}) == "xxx.xxx"
    assert _address_tail({"host": "192.168.178.105", "address_detail": "hidden"}) == (
        "xxx.xxx"
    )
    allowed = {"host": "192.168.178.105", "address_detail": "two_octets"}
    assert _address_tail(allowed) == "178.105"
    # Permission cannot conjure octets a hostname does not have.
    assert _address_tail({"host": "winet.local", "address_detail": "two_octets"}) == (
        "xxx.xxx"
    )


def _sbr_fingerprint() -> tuple[dict, dict]:
    fingerprint = {
        "device_type_code": "0x0E0F",
        "output_type": "three phase 3P4L",
        "registers": {
            "unit 200 SBR battery module block": "present",
            "battery voltage": "present",
            "battery level": "present",
            "meter phase A voltage (5741)": "present",
        },
    }
    raw = {
        "registers": {
            "battery voltage": [1995],
            "battery level": [1000],
            "battery capacity (5639)": [960],
        }
    }
    return fingerprint, raw


def test_the_hash_sits_between_the_device_and_what_is_attached_to_it() -> None:
    fingerprint, raw = _sbr_fingerprint()
    label = _derive_label(fingerprint, DIRECT, STAND_IN, raw, "fwitten")
    assert label == f"sh10rt-v112-3p-fwitten-{STAND_IN}-battery-sbr096-meter"


def test_the_contributor_groups_their_own_files_together() -> None:
    # One contributor usually sends several. Their name goes before the hash
    # so their documents sort together instead of being scattered by model
    # among everybody else's.
    fingerprint, raw = _sbr_fingerprint()
    assert _derive_label(fingerprint, DIRECT, "A123456789", raw, "gerd").startswith(
        "sh10rt-v112-3p-gerd-"
    )


def test_a_contributor_name_is_made_safe_for_a_filename() -> None:
    # It arrives as free text and lands in a public repository's filename.
    fingerprint, raw = _sbr_fingerprint()
    label = _derive_label(fingerprint, DIRECT, STAND_IN, raw, "Mr O'Brien / #2")
    assert f"sh10rt-v112-3p-mr-o-brien-2-{STAND_IN}-" in label
    for character in label:
        assert character.isalnum() or character == "-", character


def test_no_contributor_is_anonymous_rather_than_a_gap() -> None:
    # A missing name must not collapse two words into one, which would make
    # the label unparseable and could collide with a real contributor's.
    fingerprint, raw = _sbr_fingerprint()
    assert "-anonymous-" in _derive_label(fingerprint, DIRECT, "A123456789", raw, "")
    assert "-anonymous-" in _derive_label(fingerprint, DIRECT, "A123456789", raw)


def test_one_machine_read_two_ways_shares_a_prefix() -> None:
    # The reason the hash moved. An inverter read directly and through its
    # dongle differ in every word after the hash, so with the hash last the
    # two documents for one machine sorted to opposite ends of the directory.
    fingerprint, raw = _sbr_fingerprint()
    direct = _derive_label(fingerprint, DIRECT, STAND_IN, raw, "fwitten")

    # Through a dongle the meter block is refused and unit 200 goes silent,
    # which is what makes the words differ.
    fingerprint["registers"]["unit 200 SBR battery module block"] = "no answer"
    fingerprint["registers"]["meter phase A voltage (5741)"] = "refused"
    through = _derive_label(
        fingerprint,
        {"verdict": "through a communication module (WiNet-S, WiNet-S2 or Logger)"},
        STAND_IN,
        raw,
        "fwitten",
    )

    assert through == f"sh10rt-v112-3p-fwitten-{STAND_IN}-battery-unknown-winet"
    prefix = f"sh10rt-v112-3p-fwitten-{STAND_IN}-"
    assert direct.startswith(prefix)
    assert through.startswith(prefix)


def test_the_label_still_carries_neither_the_serial_nor_the_host() -> None:
    """Case-insensitively, and for a caller who passes the wrong thing.

    This compared `"A123456789" not in label` while `_slug` lowercases, so
    a real serial in the identity word would have passed it -- which stopped
    being hypothetical when the word became the caller's string rather than a
    hash of it. `_derive_label` now takes only a value prefixed `anon-`, and
    this is the test that says why.
    """
    fingerprint, raw = _sbr_fingerprint()
    label = _derive_label(fingerprint, DIRECT, "A123456789", raw)
    assert "a8649311754" not in label.lower()
    assert "176" not in label
    # Given a proper stand-in it appears; given a serial, nothing does.
    assert STAND_IN in _derive_label(fingerprint, DIRECT, STAND_IN, raw)


def _forwarded_pack(ident_at_unit_2: str) -> tuple[dict, dict]:
    """Return a Sungrow pack answering at unit 2 instead of unit 200."""
    fingerprint = {
        "device_type_code": "0x0E13",
        "output_type": "three phase 3P4L",
        "registers": {
            "unit 200 SBR battery module block": "no answer",
            "unit 2 SBR battery module block": "present",
            "unit 2 inverter device type code": ident_at_unit_2,
            "battery voltage": "present",
            "battery level": "present",
        },
    }
    raw = {
        "registers": {
            "battery voltage": [2002],
            "battery level": [1000],
            "battery capacity (5639)": [960],
        }
    }
    return fingerprint, raw


def test_a_pack_forwarded_to_unit_2_is_still_named() -> None:
    # Measured on bar12's SH10RT-20: unit 200 silent, the SBR at unit 2, and
    # the pack is a perfectly ordinary SBR096. Before unit 2 was probed this
    # came back `battery-unknown`.
    fingerprint, raw = _forwarded_pack("no answer")
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-sbr096"


def test_a_slave_inverter_at_unit_2_is_not_a_battery() -> None:
    # Unit 2 is also where a slave inverter lives. It answers the device type
    # code and a battery does not, which is what separates them -- without
    # that, a master/slave pair would report the slave as the master's pack.
    fingerprint, raw = _forwarded_pack("present")
    assert _battery_token(fingerprint, DIRECT, raw) == "battery-thirdparty"


def test_a_reported_transport_outranks_the_measurement() -> None:
    # The one place testimony beats a reading, because both signals the
    # measurement rests on have been caught lying on hardware.
    fingerprint, raw = _forwarded_pack("no answer")
    undetermined = {
        "verdict": "not determinable over Modbus -- a module is attached, "
        "which does not say the reading came through it",
        "reported_by_hand": "winet",
    }
    assert _derive_label(fingerprint, undetermined, "A123456789", raw).endswith(
        "battery-sbr096-winet"
    )

    undetermined["reported_by_hand"] = "direct_lan"
    assert not _derive_label(fingerprint, undetermined, "A123456789", raw).endswith(
        "winet"
    )


def test_one_installation_read_both_ways_gets_two_filenames() -> None:
    # The collision that started this: identical readings on both addresses,
    # so only the stated transport separates the two documents. Without it
    # the second silently overwrote the first.
    fingerprint, raw = _forwarded_pack("no answer")
    lan = _derive_label(
        fingerprint,
        {"verdict": "x", "reported_by_hand": "direct_lan"},
        "A123456789",
        raw,
    )
    dongle = _derive_label(
        fingerprint, {"verdict": "x", "reported_by_hand": "winet"}, "A123456789", raw
    )
    assert lan != dongle
    assert dongle == f"{lan}-winet"


def test_a_refused_6100_no_longer_claims_a_dongle() -> None:
    # An SH10RT-20 on its own LAN port refuses 6100, having no such block, so
    # the measurement must not read that as a communication module.
    fingerprint, raw = _forwarded_pack("no answer")
    undetermined = {
        "verdict": "not determinable over Modbus -- 6100 refused, and no "
        "module named itself"
    }
    assert not _derive_label(fingerprint, undetermined, "A123456789", raw).endswith(
        "winet"
    )


def test_not_being_sure_does_not_outrank_a_measurement() -> None:
    # "Not sure" is a first-class answer, and it must not overwrite a reading
    # that does know: 6100 answering still proves a direct path.
    fingerprint, raw = _forwarded_pack("no answer")
    connection = {
        "verdict": "direct to the inverter's LAN port",
        "reported_by_hand": "unsure",
    }
    assert not _derive_label(fingerprint, connection, "A123456789", raw).endswith(
        "winet"
    )


def test_wired_and_wireless_winet_get_different_filenames() -> None:
    # Modbus cannot tell the medium apart, which is why a person is asked --
    # and why the filename has to carry it. One dongle read wired and over
    # WiFi is two legitimate readings that are otherwise indistinguishable,
    # so without this the second silently overwrote the first.
    fingerprint, raw = _forwarded_pack("no answer")
    labels = {
        key: _derive_label(
            fingerprint, {"verdict": "x", "reported_by_hand": key}, "A123456789", raw
        )
        for key in ("winet_lan", "winet_wlan", "winet")
    }
    assert len(set(labels.values())) == 3
    assert labels["winet_lan"].endswith("winet-lan")
    assert labels["winet_wlan"].endswith("winet-wlan")
    assert labels["winet"].endswith("winet")


def test_a_refused_6100_means_a_module_even_when_it_does_not_name_itself() -> None:
    # Measured on fwitten's two dongles: 6100 refused, and register 13265
    # came back an empty string -- exactly what an inverter with no module
    # returns. So an empty module string must not stop the refusal counting.
    fingerprint, raw = _forwarded_pack("no answer")
    unnamed = {
        "verdict": "through a communication module (WiNet-S, WiNet-S2 or Logger), "
        "which did not name itself"
    }
    assert _derive_label(fingerprint, unnamed, "A123456789", raw).endswith("winet")


def test_every_menu_option_is_a_valid_flag_value() -> None:
    # The interactive menu and --transport must not drift apart: the menu
    # offers exactly what the flag accepts, and each has a sentence to show.
    from probe import REPORTED_TRANSPORTS

    for key, (menu_label, verdict, table_label, word) in REPORTED_TRANSPORTS.items():
        assert menu_label, key
        if key == "unsure":
            assert verdict == "" and table_label == "" and word == ""
        elif key == "direct_lan":
            # The inverter's own port is the unmarked case, so no word.
            assert verdict and table_label and word == ""
        else:
            assert verdict and table_label and word, key


# -- the transport verdict, one row per house that produced it ---------------


def test_answering_6100_means_nothing_is_in_the_way() -> None:
    """Read on an inverter's own LAN port with no module named: fwitten."""
    verdict = transport_verdict(answered_6100=True, module_named=False)

    assert verdict == "direct to the inverter's LAN port"


def test_a_refused_6100_with_a_named_module_names_it() -> None:
    """Through a WiNet-S that reports its firmware: bar12's SH10RT-20."""
    verdict = transport_verdict(answered_6100=False, module_named=True)

    assert "through a communication module" in verdict
    assert "did not name itself" not in verdict


def test_a_refused_6100_with_no_module_named_still_concludes() -> None:
    """Silence from register 13265 proves nothing, so 6100 carries it alone.

    Measured on fwitten's dongle, which returns 13265 empty -- exactly as an
    inverter with no dongle at all does.

    So its silence proves nothing and 6100 has to carry the verdict alone --
    which it does, or a real WiNet reading would be labelled direct.
    """
    verdict = transport_verdict(answered_6100=False, module_named=False)

    assert "through a communication module" in verdict
    assert "did not name itself" in verdict


def test_a_module_named_on_a_direct_reading_is_reported_as_fitted() -> None:
    """Named module on a direct reading: gerd's SH8.0RT has a WiNet-S fitted.

    The row that settles what register 13265 means. It reports what is
    **attached**, not the route taken -- so a named module cannot be allowed
    to overrule 6100, and the useful thing to say is that this house has both
    routes. The one it is not using forwards fewer measuring points and
    answers zero where the inverter answers "unavailable", which fabricates
    capabilities, so being on the direct path is worth knowing.
    """
    verdict = transport_verdict(answered_6100=True, module_named=True)

    assert verdict.startswith("direct to the inverter's LAN port")
    assert "fitted as well but not in the path" in verdict


def test_the_document_does_not_claim_latency_can_tell_wifi_from_ethernet() -> None:
    """It cannot, and the claim was published in every fingerprint for a week.

    Direct-LAN medians measured 2.0 to 61.5 ms and WiNet medians 24.3 to 48.3
    across four installations -- overlapping, with one house's direct link
    slower than its own dongle. The text has to say so, because a reader who
    believes the old sentence will mislabel their own setup.
    """
    from probe import _async_connection

    text = _async_connection.__doc__
    assert "not determinable" in text
    assert "about 2 ms" not in text, "the disproved claim is back in the docstring"


# -- what a person typed stays where a reader can see that it was typed -----

FINGERPRINTS = sorted((REPO / "doc" / "device-fingerprints").glob("*.json"))

#: The stand-in serial these labels are built from, exactly as
#: `_fake_serial("A123456789")` writes it. Spelled out rather than computed,
#: so a change to that derivation fails a test instead of silently agreeing
#: with itself.
STAND_IN = "anon-5155200572"

#: A key anywhere outside `user_inputs` that reads as somebody's claim. The
#: point of the section is that these names are no longer needed; a new one
#: appearing means a claim was filed with the measurements.
CLAIM_MARKERS = ("reported_by_hand", "reported_disagrees", "by_hand")


def _claim_keys(value: object, path: str = "") -> list[str]:
    """Return the paths of any keys that read as a hand-supplied value."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{path}.{key}" if path else key
            if any(marker in key for marker in CLAIM_MARKERS):
                found.append(here)
            found += _claim_keys(child, here)
    return found


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_every_published_fingerprint_separates_claims_from_readings(path) -> None:
    """`user_inputs` exists, comes first, and holds every contributed value."""
    document = json.loads(path.read_text(encoding="utf-8"))

    assert document["schema"] >= 5, "predates the user_inputs section"
    assert "user_inputs" in document
    # First of the substantive keys, after the three that say what this file is.
    keys = list(document)
    assert keys[:5] == [
        "schema",
        "command_line",
        "read_on",
        "read_at_local",
        "user_inputs",
    ]

    measured = {k: v for k, v in document.items() if k != "user_inputs"}
    assert not _claim_keys(measured), (
        f"a hand-supplied value is filed with the measurements: {_claim_keys(measured)}"
    )


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_a_published_fingerprint_still_carries_no_serial_or_address(path) -> None:
    """The rule the section must not have loosened.

    Moving fields around is exactly the change that quietly reintroduces a
    serial or a host, so it is asserted per file rather than trusted.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    text = json.dumps(document)

    assert "host" not in document
    assert "read_at" not in document, "the exact time says when somebody was in"
    # An octet on its own is one of 254 on a subnet nobody has named; a dotted
    # quad is somebody's network.
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), "an IP address"


def test_a_supplied_value_lands_only_in_user_inputs() -> None:
    """Checked against the writer, not only against the committed files."""
    from probe import _document

    raw = {
        "read_at": "2026-09-08T20:00:33+00:00",
        "host": "192.168.178.35",
        "serial": "A987654321",
        "reporter": "somebody",
        "comment": "the master, with the battery",
        "battery": "Sungrow SBR096, 9.6 kWh",
        "proxy": "no",
        "connection": {
            "verdict": "direct to the inverter's LAN port",
            "reported_by_hand": "direct_lan",
        },
        "firmware": {"arm": "ARM_X"},
        "readings": {"values": {}, "components_that_did_not_answer": []},
        "registers": {},
    }

    document = _document(raw, {"registers": {}})

    assert document["user_inputs"] == {
        "reporter": "somebody",
        "comment": "the master, with the battery",
        "battery": "Sungrow SBR096, 9.6 kWh",
        "transport": "direct_lan",
        "modbus_proxy": "no",
    }
    # The measured connection keeps the verdict and loses the claim.
    assert document["connection"] == {"verdict": "direct to the inverter's LAN port"}
    # And `raw` is untouched, because the filename is derived from it.
    assert raw["connection"]["reported_by_hand"] == "direct_lan"
    # Observed, not claimed.
    # Withheld, because this raw carries no permission.
    assert document["ip_address_last_two_octets"] == "xxx.xxx"
    assert "ip_address_last_two_octets" not in document["user_inputs"]


def test_a_comparison_of_two_stored_values_is_not_stored() -> None:
    """Schema 5 kept `transport_disagrees_with_measurement`; schema 6 does not.

    It was neither what a person typed nor what a wire said, so the
    `user_inputs` split had nowhere to put it. Worse, it would go stale the
    moment the verdict logic changed, while sitting next to both of its own
    inputs. The check still happens -- it is printed while the script runs,
    which is when somebody can act on it.
    """
    from probe import _document

    document = _document(
        {
            "read_at": "2026-09-08T20:00:33+00:00",
            "connection": {"verdict": "direct", "reported_by_hand": "winet_lan"},
        },
        {"registers": {}},
    )

    assert "transport" in document["user_inputs"]
    assert not [k for k in json.dumps(document).split('"') if "disagree" in k]


def test_the_local_time_carries_its_offset_across_the_dst_boundary() -> None:
    """Summer and winter differ by an hour, and the value has to say which.

    A bare wall-clock time would be ambiguous twice a year, and these are
    read minutes apart on purpose -- one machine on its LAN port and then
    through its dongle.
    """
    from probe import _local_time

    assert _local_time("2026-09-07T22:00:33+00:00") == "2026-09-08T00:00:33+02:00"
    assert _local_time("2026-01-15T08:30:00+00:00") == "2026-01-15T09:30:00+01:00"


def test_an_unreadable_timestamp_is_passed_through_rather_than_invented() -> None:
    """A wrong local time would be worse than an honest UTC one."""
    from probe import _local_time

    assert _local_time("nonsense") == "nonsense"
    assert _local_time("") == ""


def test_the_menus_are_numbered_and_accept_the_value_itself() -> None:
    """Numbered, not lettered.

    `a-h` with six options leaves half the alphabet invalid, `l` and `1` are
    hard to tell apart in some terminal fonts, and a contributor checking
    their own answer has to count letters. A number is the position.
    """
    from probe import PROXY_ANSWERS, REPORTED_TRANSPORTS, _ask_menu

    keys = list(REPORTED_TRANSPORTS)
    labels = {k: v[0] for k, v in REPORTED_TRANSPORTS.items()}

    with _answering(["1"]):
        assert _ask_menu(keys, labels, "winet") == "direct_lan"
    with _answering(["3"]):
        assert _ask_menu(keys, labels, "winet") == "winet_wlan"
    # Enter takes the default.
    with _answering([""]):
        assert _ask_menu(keys, labels, "winet") == "winet"
    # The value itself still works, so a pasted command runs.
    with _answering(["winet_wlan"]):
        assert _ask_menu(keys, labels, "winet") == "winet_wlan"
    # Out of range and letters are rejected, then it asks again.
    with _answering(["9", "b", "2"]):
        assert _ask_menu(keys, labels, "winet") == "winet_lan"

    proxy = list(PROXY_ANSWERS)
    for choice, expected in (("1", "yes"), ("2", "no"), ("3", "unknown")):
        with _answering([choice]):
            assert _ask_menu(proxy, PROXY_ANSWERS, "unknown") == expected


def test_a_proxy_is_an_answer_of_three_states_and_a_fourth_absence() -> None:
    """`unknown` is asked-and-did-not-know; empty is never-asked.

    Both are honest and they are not the same, so neither may be written as
    the other -- the eight documents collected before the question existed
    carry the empty one.
    """
    from probe import PROXY_ANSWERS, _document

    assert list(PROXY_ANSWERS) == ["yes", "no", "unknown"]

    asked = _document({"read_at": "2026-09-08T20:00:33+00:00", "proxy": "unknown"}, {})
    never = _document({"read_at": "2026-09-08T20:00:33+00:00"}, {})

    assert asked["user_inputs"]["modbus_proxy"] == "unknown"
    assert never["user_inputs"]["modbus_proxy"] == ""


def test_pressing_enter_on_the_transport_question_records_nothing() -> None:
    """The default is `unsure`, and that is the point of it.

    A WiNet-S is the commonest fitting, which made it tempting -- and this is
    the one field no measurement can correct, so pre-filling the likeliest
    answer would turn a guess into a record. `_effective_verdict` already
    treats `unsure` as claiming nothing, so Enter costs the document nothing
    rather than costing it the truth.
    """
    from probe import _ask_transport, _effective_verdict

    with _answering([""]):
        assert _ask_transport() == "unsure"

    measured = {"verdict": "direct to the inverter's LAN port"}
    assert (
        _effective_verdict({**measured, "reported_by_hand": "unsure"})
        == (measured["verdict"])
    )


def test_the_command_line_reproduces_the_reading_without_the_address() -> None:
    """The one line that could undo the whole point of the document.

    A fingerprint drops the host deliberately -- `ip_address_last_octet` is
    the single, considered exception. Quoting the real command would put the
    address back in the first line of the file, so the host is a placeholder
    and `--save` is left out as a local path.
    """
    import argparse

    from probe import _invocation

    line = _invocation(
        argparse.Namespace(
            host="192.168.178.35",
            port=502,
            unit=1,
            timeout=10.0,
            passes=8,
            dump=True,
            transport="direct_lan",
            proxy="no",
            reporter="mkaiser",
            battery="Pylontech Force H1, 14.4 kWh",
            comment="the master's reading",
            save="/home/somebody/reports",
            label=None,
        )
    )

    assert "192.168.178.35" not in line
    assert "<host>" in line
    assert "/home/somebody" not in line, "a local path leaked"

    # Every collection flag is there, and the values survive quoting -- a
    # comment with an apostrophe in it has to paste back intact.
    words = shlex.split(line)
    assert words[:3] == [SCRIPT, "capabilities", "<host>"]
    assert "Pylontech Force H1, 14.4 kWh" in words
    assert "the master's reading" in words
    for flag in (
        "--port",
        "--unit",
        "--timeout",
        "--passes",
        "--dump",
        "--transport",
        "--proxy",
        "--reporter",
    ):
        assert flag in words, flag


def test_an_unset_option_is_absent_rather_than_guessed() -> None:
    """A flag nobody can show was used must not appear.

    The documents collected before schema 8 recorded only the tool name, so
    their lines are rebuilt from what each file itself preserves -- and
    `--port`, `--unit`, `--timeout` and `--passes` are genuinely unknown for
    them. A reconstructed line that names them at their defaults would read
    as a record of a run nobody made.
    """
    import argparse

    from probe import _invocation

    line = _invocation(
        argparse.Namespace(port=502, unit=1, timeout=5.0, passes=8, dump=False)
    )

    assert "--dump" not in line
    assert "--transport" not in line
    assert "--comment" not in line
    # The one place the path is written out rather than derived, so that
    # SCRIPT cannot quietly drift from where the file actually is.
    assert _invocation(None) == "scripts/sungrow_scan/probe.py capabilities <host>"


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_every_published_command_line_is_runnable_and_hostless(path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    words = shlex.split(document["command_line"])

    assert words[:3] == [SCRIPT, "capabilities", "<host>"]
    # The stronger check lives in the no-serial-or-address test, but the
    # command line is the field most likely to reintroduce one.
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", document["command_line"])


def test_the_stand_in_serial_cannot_be_mistaken_for_a_serial() -> None:
    """It used to keep the real serial's leading letters, and that was wrong.

    `A123456789` became `A5155200572` -- not a serial, and indistinguishable
    from one. Somebody quoting it into an issue, searching for it, or holding
    it against a label on a wall gets a plausible wrong answer, and the field
    being named `serial_anonymized_hashed` stops helping the moment the value
    is copied out of it. So the value says what it is.
    """
    from probe import _fake_serial

    stand_in = _fake_serial("A123456789")

    assert stand_in.startswith("anon-")
    assert not stand_in.startswith("A")
    # Still stable, and still distinguishes two machines.
    assert stand_in == _fake_serial("A123456789")
    assert stand_in != _fake_serial("A987654321")
    # And nothing of the real serial survives in it.
    assert "2311227462" not in stand_in
    assert _fake_serial("") == ""


def test_the_filename_now_follows_the_stand_in_deliberately() -> None:
    """The property this file used to assert, traded away on purpose.

    The old rule hashed the **real** serial, so a filename could not move
    when the stand-in's format changed -- which mattered, because adding the
    `anon-` prefix had once renamed nine contributors' files for a reason
    with nothing to do with their hardware.

    The maintainer chose the other side of that trade, and the reason is
    better: a document and its name carried two different derivations of one
    serial, only one of which a reader holding the published file could
    recompute. On the first machine to have both they shared four characters
    by chance -- `anon-00267885816` against `aa2678` -- and were read as one
    value gone wrong.

    So the exposure is back and is stated rather than forgotten: **change
    how the stand-in is written and every filename moves.** Schema 10 settled
    that format; this test is what will fail if it is unsettled.
    """
    fingerprint, raw = _sbr_fingerprint()
    raw = {**raw, "serial": "A123456789"}

    label = _derive_label(fingerprint, DIRECT, "anon-00267885816", raw, "gerd")
    assert "-anon-00267885816-" in label

    # Written differently, the name moves. That is the cost, asserted so that
    # nobody discovers it by renaming a directory.
    moved = _derive_label(fingerprint, DIRECT, "anon-99999999999", raw, "gerd")
    assert moved != label

    # And with no stand-in at all -- which a document always has, but a
    # caller might not pass -- it still produces a label rather than crashing.
    without = _derive_label(fingerprint, DIRECT, "", raw, "gerd")
    assert "-gerd-" in without


def test_the_recorded_command_names_the_path_that_works_where_it_ran(
    monkeypatch, tmp_path
) -> None:
    """Inside the checkout, the repository path; unpacked from a zip, the file.

    `command_line` is an instruction to repeat a reading. A contributor who
    unpacked the directory into a folder of its own has no `scripts/` above
    it, so the repository path would be an instruction that fails -- and this
    field is the one line of the document somebody actually retypes.
    """
    import probe

    assert probe._script_name() == probe.SCRIPT

    unpacked = tmp_path / "sungrow_scan" / "probe.py"
    unpacked.parent.mkdir()
    unpacked.write_text("")
    monkeypatch.setattr(probe, "__file__", str(unpacked))
    assert probe._script_name() == "probe.py"


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_a_published_filename_can_be_checked_against_its_own_document(path) -> None:
    """The file must account for the name it is filed under.

    This test exists because a reader could not do it. The name used to carry
    `sha256(real serial)[:6]`, which a published document cannot derive -- it
    has no real serial, by design -- so the only way to tell whether a
    document and its filename belonged together was to trust them. Worse, the
    stand-in serial in the file and the hash in the name were two derivations
    of one serial, and on the first machine to have both they shared four
    characters by pure chance: `anon-00267885816` and `aa2678`. That reads as
    one value corrupted rather than two values unrelated.

    So the name carries the stand-in itself, and the firmware it claims must
    be the firmware the document recorded.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    device = document["device"]

    stand_in = device["serial_anonymized_hashed"]
    assert stand_in, "no stand-in serial to check the filename against"
    assert _slug(stand_in) in path.stem, (
        f"{path.name} does not carry its own stand-in serial {stand_in}"
    )
    firmware = _firmware_token({"firmware": document["firmware"]})
    if firmware:
        assert firmware in path.stem, (
            f"{path.name} does not carry its firmware word {firmware}"
        )


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_no_published_probe_carries_the_values_of_a_serial(path) -> None:
    """The leak this rule was written for, and the device it forgot.

    `NEVER_PUBLISH` kept serials out of the readings block and out of the
    register dump. It did not cover the curated probes -- two of which are
    named "wallbox serial" -- so gerd's document published `[16690, 13633]`,
    which decodes to `A25A`: the first four characters of the wallbox's real
    serial. The inverter's own identity was masked in three places and the
    device attached to it in none.

    What a capability needs is that the register answered. The value never
    was the point.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    for label, entry in document.get("capability_probes", {}).items():
        if any(word in label for word in NEVER_PUBLISH):
            assert "values" not in entry, f"{label} publishes {entry.get('values')}"
        # And whatever a probe does publish must not decode to printable text
        # that looks like a serial: a Sungrow serial is a letter and ten
        # alphanumerics, so any long ASCII run is worth failing on.
        words = entry.get("values") or []
        if all(isinstance(word, int) and 0 <= word <= 0xFFFF for word in words):
            text = b"".join(int(w).to_bytes(2, "big") for w in words)
            printable = "".join(chr(b) if 32 <= b < 127 else " " for b in text)
            assert not any(
                len(run) >= 6 and any(c.isdigit() for c in run)
                for run in printable.split()
            ), f"{label} publishes something that reads as text: {printable!r}"


@pytest.mark.parametrize(
    ("recorded", "expected"),
    [
        ("SAPPHIRE-H_B001.V000.P022", "b001v000p022"),
        # No underscore: taken whole rather than dropped.
        ("PLAINVERSION1.2", "plainversion12"),
        # Absent: omitted, not filled in with a word that sorts as a version.
        ("", ""),
    ],
)
def test_the_firmware_word_is_the_version_without_its_family(
    recorded, expected
) -> None:
    """`sh80rt` already says the family; the word says only what varies."""
    assert _firmware_token({"firmware": {"inverter": recorded}}) == expected


def test_a_reading_with_no_firmware_still_gets_a_filename() -> None:
    """A component that did not read must not cost the document its name."""
    fingerprint, raw = _sbr_fingerprint()
    raw.pop("firmware", None)
    label = _derive_label(fingerprint, DIRECT, "anon-00267885816", raw)
    assert label
    assert "none" not in label and "unknown-firmware" not in label


def test_the_filename_carries_the_stand_in_and_not_the_real_serial() -> None:
    """Both halves of the rule, on one call.

    The stand-in is what a reader can check; the real serial is what must
    never appear. They are derived from each other, so a test that only
    looked for one of them would pass on a filename carrying the other.
    """
    fingerprint, raw = _sbr_fingerprint()
    raw["serial"] = "A123456789"
    label = _derive_label(fingerprint, DIRECT, "anon-00267885816", raw)
    assert "anon-00267885816" in label
    assert "A123456789" not in label and "2311227462" not in label


def test_a_wallbox_dump_is_masked_at_the_wallbox_serial() -> None:
    """The second serial in the house, masked by its own mask.

    The inverter's serial lives at input 4990 and the wallbox's at input
    21201, so masking a wallbox dump with the inverter's mask would look
    careful and publish a serial. `A25A123456` was already published once,
    as the words of a capability probe.
    """
    from probe import WALLBOX_DUMP_MASKED, _masked_dump

    # The words this wallbox actually answered at 21201-21206, and one
    # measurement that must survive.
    dump = {
        "input": {
            "21200": 16690,
            "21201": 13633,
            "21202": 13105,
            "21203": 12597,
            "21204": 14390,
            "21205": 12544,
            "21307": 3324,
        }
    }
    masked = _masked_dump(dump, WALLBOX_DUMP_MASKED)

    serial_words = [masked["input"][str(a)] for a in range(21200, 21206)]
    assert serial_words == [None] * 6
    assert masked["input"]["21307"] == 3324, "the measurements must survive"
    # And the inverter's mask would not have covered it, which is the point.
    from probe import DUMP_MASKED

    wrong = _masked_dump(dump, DUMP_MASKED)
    text = b"".join(
        int(wrong["input"][str(a)]).to_bytes(2, "big") for a in range(21200, 21206)
    )
    assert text.decode("ascii").startswith("A25A"), (
        "this is what using the inverter's mask published"
    )


def test_a_second_device_never_overwrites_the_first(tmp_path) -> None:
    """Two readings, one derived name, and both must survive.

    A machine read through two paths derives the same filename unless the
    person said which path each was -- same serial, same battery, same
    capabilities, and the transport word is empty when the honest answer is
    "not sure". A first-time contributor answering that twice would have had
    their second reading land on the first one's file.

    This is not hypothetical twice over: it cost a file earlier in this
    project, and the run that prompted the fix answered "not sure" for both
    paths of one inverter.
    """
    from probe import _save

    def reading(host: str) -> tuple[dict, dict]:
        fingerprint, raw = _sbr_fingerprint()
        raw = {
            **raw,
            "serial": "A123456789",
            "host": host,
            "address_detail": "two_octets",
            "read_at": "2026-09-08T18:00:00+00:00",
            "firmware": {"inverter": "SAPPHIRE-H_B001.V000.P022"},
        }
        return raw, fingerprint

    first = _save(tmp_path, "one-machine", *reading("192.168.178.41"))
    second = _save(tmp_path, "one-machine", *reading("192.168.178.23"))

    assert first[0].name == "one-machine.json"
    assert second[0].name != first[0].name, "the second reading overwrote the first"
    assert first[0].exists() and second[0].exists()
    # And the name says which address it came from, since that is the only
    # thing distinguishing them.
    assert "178-023" in second[0].name

    import json

    assert json.loads(first[0].read_text())["ip_address_last_two_octets"] == "178.041"
    assert json.loads(second[0].read_text())["ip_address_last_two_octets"] == "178.023"


def test_re_reading_the_same_device_does_overwrite(tmp_path) -> None:
    """One machine, one path, read twice: the newer reading replaces it.

    The guard is about *different* devices colliding. A re-read of the same
    address is a correction, and accumulating `-178-041` copies of it would
    turn a directory into a pile.
    """
    from probe import _save

    def reading() -> tuple[dict, dict]:
        fingerprint, raw = _sbr_fingerprint()
        raw = {
            **raw,
            "serial": "A123456789",
            "host": "192.168.178.41",
            "address_detail": "two_octets",
            "read_at": "2026-09-08T18:00:00+00:00",
            "firmware": {"inverter": "SAPPHIRE-H_B001.V000.P022"},
        }
        return raw, fingerprint

    first = _save(tmp_path, "one-machine", *reading())
    again = _save(tmp_path, "one-machine", *reading())
    assert again[0] == first[0]
    assert len(list(tmp_path.glob("*.json"))) == 1


def _table_rows() -> dict[str, dict[str, str]]:
    """Return the committed compatibility table, row by row, keyed by stem."""
    lines = (REPO / "doc" / "compatibility.md").read_text(encoding="utf-8").splitlines()
    header = next(line for line in lines if line.startswith("| Setup"))
    columns = [cell.strip() for cell in header.strip().strip("|").split("|")]
    rows = {}
    for line in lines:
        if not line.startswith("| `sh"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0].strip("`")] = dict(zip(columns, cells, strict=False))
    return rows


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_the_table_and_the_filename_agree_about_the_battery(path: Path) -> None:
    """Two artefacts, one reading: they must not contradict each other.

    Both `doc/compatibility.md` and the filename are generated from the same
    document, so a disagreement means one of them is wrong -- and a reader has
    no way to tell which. Measured case, 2026-09-09: a cluster slave whose
    filename said `battery-none` had `Battery: yes` in the table, because the
    column marked the *state* of the `battery level` probe and a slave answers
    that probe with 0. `_battery_token` had tested for all-zero since it was
    written; the table had not.

    Asserted against the committed table rather than by re-deriving it, so
    this also fails when somebody regenerates one artefact and not the other.
    """
    row = _table_rows().get(path.stem)
    assert row is not None, (
        f"{path.stem} is in device-fingerprints/ but not in compatibility.md -- "
        "run scripts/generate_compatibility.py"
    )

    # The filename's own word, which is what a reader sees first.
    claims_none = "-battery-none" in path.stem or path.stem.endswith("battery-none")
    if claims_none:
        assert row["Battery"] != "yes", (
            f"{path.stem} says battery-none in its filename and "
            f"Battery={row['Battery']!r} in the table"
        )

    # And the other direction: a named pack must not be marked absent.
    document = json.loads(path.read_text(encoding="utf-8"))
    named_a_model = "-battery-sbr" in path.stem or "-battery-sbh" in path.stem
    if named_a_model:
        assert row["Battery"] == "yes", (
            f"{path.stem} names a Sungrow pack and the table says "
            f"Battery={row['Battery']!r}"
        )
        assert document["capability_probes"]["battery capacity (5639)"]["values"], (
            "a filename naming a pack model needs the capacity it was matched on"
        )


class _FakeUnit:
    """One unit id of a fake device, answering only what it was given."""

    def __init__(self, answers: dict[int, list[int]]):
        self._answers = answers

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Answer, or raise the way a device refusing an address does."""
        if address not in self._answers:
            raise _FakeRefusal("Modbus Exception 0x02 for function code 0x04")
        return self._answers[address]


class _FakeRefusal(Exception):
    """Stands in for the library's ModbusError."""


class _FakeConnection:
    """A device whose unit ids answer different things, or nothing."""

    def __init__(self, units: dict[int, dict[int, list[int]]]):
        self._units = units
        self.asked: list[int] = []

    def for_unit(self, unit_id: int) -> _FakeUnit:
        self.asked.append(unit_id)
        return _FakeUnit(self._units.get(unit_id, {}))

    async def close(self) -> None:
        """Nothing to close."""


def _serial_words(serial: str) -> list[int]:
    """Encode a serial the way the inverter reports it at input 4989."""
    raw = serial.encode("ascii").ljust(20, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, 20, 2)]


@pytest.fixture
def _fake_stack(monkeypatch: pytest.MonkeyPatch):
    """Let a test hand `identify` a device instead of a network."""
    import probe as probe_module

    def install(units: dict[int, dict[int, list[int]]]) -> _FakeConnection:
        connection = _FakeConnection(units)
        monkeypatch.setattr(
            probe_module,
            "_require_library",
            lambda: (_FakeRefusal, lambda **_kw: None, lambda *_a, **_kw: connection),
        )
        return connection

    return install


async def test_a_cluster_slave_is_found_on_unit_2_without_being_told(
    _fake_stack,
) -> None:
    """The regression this exists for, measured at a real house.

    fwitten's second inverter answers on unit **2** at its own LAN port and
    times out on 1, because a cluster slave's own device address is 2.
    `identify` asked unit 1 and gave up, so the survey printed "no serial at
    unit 1" and then offered a unit prompt defaulting to 1 -- and the only
    reason that scan produced a document is that the operator already knew
    the answer. A contributor would have been told their inverter is absent,
    while `CANDIDATE_UNITS` had listed unit 2 as "inverter slave" all along.
    """
    import probe as probe_module

    connection = _fake_stack({2: {4989: _serial_words("A987654321"), 4999: [0x0E0F]}})

    who = await probe_module.identify("192.0.2.29", 502)

    assert who.serial == "A987654321"
    assert who.unit == 2, "the unit that answered has to come back"
    assert who.error is None
    assert who.device_type_code == 0x0E0F
    assert connection.asked[:2] == [1, 2], "unit 1 is still tried first"
    # And it says so, because a reader seeing unit 2 needs to know it is not
    # the usual one rather than wondering if the tool is confused.
    assert "unit 2" in probe_module.described(who)


async def test_an_inverter_on_unit_1_costs_no_extra_reads(_fake_stack) -> None:
    """The common case must not pay for the rare one.

    Four extra probes against every address would be four timeouts each on a
    slow link, for a house where nothing is wrong.
    """
    import probe as probe_module

    connection = _fake_stack({1: {4989: _serial_words("A987654321"), 4999: [0x0E03]}})

    who = await probe_module.identify("192.0.2.35", 502)

    assert who.unit == 1
    assert connection.asked == [1], "no unit beyond the first was touched"
    # Unit 1 is the default everywhere, so saying so would be noise.
    assert "unit" not in probe_module.described(who)


async def test_a_modbus_device_that_is_not_a_sungrow_is_not_claimed_as_one(
    _fake_stack,
) -> None:
    """Measured: an open port 502 at a surveyed house that was not an inverter.

    A /24 sweep of fwitten's network found five endpoints on 502, one more
    than the two inverters and their two dongles. The fifth refuses input
    4989 on every unit id with exception 0x02, ignores the unit id
    altogether, and answers only registers 0-19 with small integers -- some
    other vendor's Modbus device on a home network.

    So an open 502 is not an inverter, which is why discovery identifies by
    what answers. What `identify` must not do is guess: no serial means no
    device, and the error names the exception so that a refusal is
    distinguishable from silence.
    """
    import probe as probe_module

    connection = _fake_stack({unit: {0: [3, 8964]} for unit in (1, 2, 3, 4, 5)})

    who = await probe_module.identify("192.0.2.99", 502)

    assert who.serial is None
    assert who.unit is None, "nothing answered, so no unit did"
    assert who.error is not None
    assert "no serial at unit 1, 2, 3, 4, 5" in who.error
    # The exception type is in the message, because "refused" and "timed out"
    # lead to different next steps -- see scripts/layout.py.
    assert "_FakeRefusal" in who.error
    assert connection.asked == [1, 2, 3, 4, 5], "every candidate is tried"


async def test_a_device_that_answers_but_names_nothing_stops_the_sweep(
    _fake_stack,
) -> None:
    """Something is there and talking; a later unit is a different device.

    Continuing would let unit 2's answer be reported as the identity of an
    address whose unit 1 is occupied by something else.
    """
    import probe as probe_module

    connection = _fake_stack(
        {
            1: {4989: [0] * 10},
            2: {4989: _serial_words("A987654321"), 4999: [0x0E03]},
        }
    )

    who = await probe_module.identify("192.0.2.40", 502)

    assert who.serial is None
    assert who.unit == 1
    assert who.error == "answered, but reported no serial"
    assert connection.asked == [1], "the sweep stopped where something answered"


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_a_document_carries_what_the_schema_it_claims_added(path: Path) -> None:
    """A schema number is a claim about content, not a version stamp.

    Written after getting this wrong. Schema 15 added `battery_pack`, the
    pack's own seventeen registers, and nine committed documents were bumped
    to 15 with a one-line edit -- documents collected by the *previous* code,
    which had never read those registers. Six of the nine had a pack
    answering their probe, so the section's absence then read as "no pack
    found" on a machine that has one. A reader has no way to tell that from
    the truth.

    The rule is the one this repo applies to everything else: a document says
    what was measured. If the code that produced it could not have read
    something, its schema must not claim the version that reads it.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["schema"] < 15:
        return

    probes = document.get("capability_probes") or {}

    def answered(name: str) -> bool:
        return (probes.get(name) or {}).get("state") == "present"

    # Unit 2 is also where a slave inverter lives on a direct connection, and
    # it answers the pack's probe address with 0xFFFF -- so the device type
    # code is what separates them, exactly as `_battery_token` does it.
    pack_answered = answered("unit 200 SBR battery module block") or (
        answered("unit 2 SBR battery module block")
        and not answered("unit 2 inverter device type code")
    )
    if not pack_answered:
        return

    assert "battery_pack" in document, (
        f"{path.stem} claims schema {document['schema']} and a pack answered "
        "its probe, so it must carry the battery_pack section that schema "
        "added. If this document predates the code that reads those "
        "registers, its schema is wrong rather than its contents."
    )
    assert document["battery_pack"].get("readings", {}).get("values"), (
        "an empty battery_pack section is worse than none: it says the pack "
        "was read and reported nothing"
    )


@pytest.mark.parametrize("path", FINGERPRINTS, ids=lambda p: p.stem)
def test_a_collect_run_at_schema_16_carries_its_block_read_test(path: Path) -> None:
    """Schema 16 added `block_read_test`, and only one tool produces it.

    Keyed on `command_line` rather than on the schema alone, because the
    absence is legitimate for one of the two tools: `collect.py` always runs
    the block read test, and the bare `capabilities` subcommand never does.
    Requiring it of every schema-16 document would fail an honest one.

    The sibling of `test_a_document_carries_what_the_schema_it_claims_added`,
    which caught this file's author bumping nine documents to a schema whose
    contents they did not have -- twice in one day, the second time within
    minutes of writing the test.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    if document["schema"] < 16:
        return
    if "collect.py" not in str(document.get("command_line", "")):
        return

    assert "block_read_test" in document, (
        f"{path.stem} was collected by collect.py at schema "
        f"{document['schema']}, which always runs the block read test, so the "
        "section it added must be here"
    )
    measured = document["block_read_test"]
    # The three lists have to exist even when empty: "no block ever failed"
    # is a finding, and an absent list would read as "not looked at".
    for name in ("answered", "never_answered", "intermittent"):
        assert name in measured, name
    assert measured.get("rounds"), "how it was measured decides what it means"
    assert measured.get("client"), (
        "which Modbus client read it decides what a refusal means -- the "
        "library one fails wherever the integration does"
    )
