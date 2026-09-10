"""What a capability survey reads, and how to publish it.

The survey in `scripts/sungrow_scan/` has always owned this knowledge, and it
had to: that directory ships as a zip a stranger runs on bare Python, so it
cannot import this library. But the *integration* can, and a user who has
already set the integration up has by definition a working connection to
their inverter and no way to turn it into evidence. Every document in
`doc/device-fingerprints/` comes from one of four houses, all of them known
to the maintainer, which is the single biggest filter on what this project
knows.

So the tables live here, where both a Home Assistant integration and a test
can reach them, and `scripts/sungrow_scan/probe.py` keeps its own literal
copy. **That duplication is deliberate and asserted**, the same trade already
made for `IDENTIFY_UNITS`: a survey that cannot run standalone is a worse
problem than two tables a test keeps identical.

Nothing here talks to a device. `PROBES` says which addresses answer the
question, `classify()` says what an answer means, and `stand_in()` is how a
serial leaves the building. The reading itself belongs to whoever has the
connection.
"""

from __future__ import annotations

from enum import StrEnum
import hashlib

#: The document format both producers write. Bumped when the *shape* changes,
#: not when a producer does.
#:
#: 17 allows a document collected through Home Assistant's diagnostics
#: download rather than by running the script. Everything else is identical;
#: what changes is that `command_line` may name a *tool* instead of an
#: invocation, because there is no command to repeat. The full history of the
#: earlier numbers is in `scripts/sungrow_scan/probe.py`, which is where the
#: format grew up.
#:
#: `test_the_two_producers_agree_on_the_schema` keeps this equal to
#: `probe.SCHEMA`.
SCHEMA = 17

#: How a document says it was collected, when no command line could repeat it.
#:
#: `command_line` exists to reproduce a reading. A diagnostics download cannot
#: be reproduced by running anything, so it says what produced it and stops
#: there rather than printing an invocation nobody could type. The guard in
#: `tests/test_fingerprint_label.py` accepts this exact prefix and no other
#: non-invocation.
COLLECTED_BY_INTEGRATION = "home assistant"

#: Words that may never appear in a published key or label. Values *or* names.
#:
#: One entry, and it earned its own constant: `sungrow_inverter_serial` once
#: reached a published document's `fields_read_individually`, and two capability
#: probes named "wallbox serial" published their raw words -- `[16690, 13633]`,
#: which decodes to `A25A`.
NEVER_PUBLISH = ("serial",)

#: Values the specification uses for "this measuring point is not here".
#: U16, U32, S16, S32.
UNAVAILABLE = frozenset({0xFFFF, 0x7FFF})

#: What register 5002 reports, in words.
OUTPUT_TYPES = {0: "single phase", 1: "three phase 3P4L", 2: "three phase 3P3L"}


class State(StrEnum):
    """What one probe's read established, in the survey's own vocabulary.

    Four states, and the distinction between the last two is the one that
    matters most. A device answering an exception 0x02 has **told** you the
    register is not there; a read that timed out has told you nothing at all,
    and from this end a silent inverter and a tunnel that lost the answer look
    identical. Collapsing them would put a guess into `layout.py`.
    """

    PRESENT = "present"
    """It answered with something other than the unavailable sentinel."""

    UNAVAILABLE = "unavailable"
    """It answered, with the specification's "not here" value."""

    REFUSED = "refused"
    """The device rejected the read. Evidence about the register."""

    NO_ANSWER = "no answer"
    """Nothing came back. Evidence about the link, not the register."""


#: What to read to establish each capability axis.
#:
#: Addresses are **protocol addresses**, one below the register number in
#: Sungrow's document -- so `("device type code (5000)", …, 4999, …)` reads
#: what the document calls register 5000. The label is what a published
#: document and `doc/compatibility.md` are keyed on, so it is part of the
#: format: renaming one silently unrelates a new reading from every old one.
#:
#: (label, space, address, count, axis)
PROBES: tuple[tuple[str, str, int, int, str], ...] = (
    ("device type code (5000)", "input", 4999, 1, "model"),
    ("nominal output power (5001)", "input", 5000, 1, "model"),
    ("output type (5002)", "input", 5001, 1, "phase"),
    ("MPPT1 voltage", "input", 5010, 1, "mppt"),
    ("MPPT2 voltage", "input", 5012, 1, "mppt"),
    ("MPPT3 voltage", "input", 5014, 1, "mppt"),
    ("MPPT4 voltage", "input", 5114, 1, "mppt"),
    ("phase A voltage", "input", 5018, 1, "phase"),
    ("phase B voltage", "input", 5019, 1, "phase"),
    ("phase C voltage", "input", 5020, 1, "phase"),
    ("meter phase A voltage (5741)", "input", 5740, 1, "meter"),
    ("meter phase A current (5744)", "input", 5743, 1, "meter"),
    ("battery voltage", "input", 13019, 1, "battery"),
    ("battery level", "input", 13022, 1, "battery"),
    ("battery temperature", "input", 13024, 1, "battery"),
    ("battery capacity (5639)", "input", 5638, 1, "battery"),
    ("firmware block (13250, spec V1.1.7+)", "input", 13249, 1, "firmware"),
    ("PV power of today (6100, direct-only)", "input", 6099, 2, "transport"),
    ("PV power limitation (13018, V1.1.10+)", "holding", 13017, 1, "firmware"),
)

#: The firmware strings, which decide more than the model does.
#:
#: Which registers a device answers moves between versions, so a fingerprint
#: without them cannot be compared with one taken a year later. Two of these
#: are worth knowing the character of: **arm** and **dsp** have been identical
#: on every document ever collected, because they identify *hardware* rather
#: than updatable firmware -- so nine matching readings are evidence of
#: nothing. `sungrow_version_1`, in the ordinary readings, is the field that
#: actually tracks an update.
#:
#: `communication_module` is also a connection signal: a direct-LAN inverter
#: has no module and answers the specification's UTF-8 unavailable, which
#: decodes to an empty string, while anything behind a WiNet-S names itself.
#:
#: (name, space, address, count)
FIRMWARE_STRINGS: tuple[tuple[str, str, int, int], ...] = (
    ("arm", "input", 4953, 15),
    ("dsp", "input", 4968, 15),
    ("inverter", "input", 13249, 15),
    ("communication_module", "input", 13264, 15),
    ("battery", "input", 13279, 15),
)

#: The register that says which way in we came, and what it means.
#:
#: Sungrow states the 6100-6195 block is not forwarded by a WiNet-S over
#: TCP/IP. Measured 9 of 9 across four houses, which makes it the only
#: reliable transport signal there is -- latency is not one, and WiFi versus
#: Ethernet is not determinable at all.
DIRECT_ONLY_ADDRESS = 6099

#: What a stand-in serial always begins with, and cannot occur in a real one.
STAND_IN_PREFIX = "anon-"

#: The values `user_inputs.transport` may hold, which are part of the format.
#:
#: Keys only. The human wording lives with each producer -- a menu line in the
#: script, a translated string in the integration -- because that is
#: presentation, while the key is what `generate_compatibility.py` groups by.
#: Kept equal to `probe.REPORTED_TRANSPORTS`' keys.
#:
#: `unsure` is not a gap in the list. A WiNet-S answers identically wired and
#: over WiFi, so an owner who does not know which their dongle is using is
#: reporting the truth, and a document that recorded a guess instead would be
#: worse than one that records the uncertainty.
TRANSPORT_CLAIMS: tuple[str, ...] = (
    "direct_lan",
    "winet_lan",
    "winet_wlan",
    "winet",
    "logger",
    "unsure",
)

#: The values `user_inputs.modbus_proxy` may hold.
#:
#: An empty string is none of these and means the question was never put,
#: which is a different statement from `unknown` -- where it was put and the
#: answer was that they did not know. Documents written before the question
#: existed are the empty case, and collapsing the two would turn silence into
#: testimony.
PROXY_CLAIMS: tuple[str, ...] = ("yes", "no", "unknown")


def classify(words: list[int] | tuple[int, ...] | None) -> State:
    """Say what a successful read means, by the specification's convention.

    `None` or an empty read is `NO_ANSWER`; a caller that caught a refusal
    should record `REFUSED` itself, because only it can tell the two apart.
    """
    if not words:
        return State.NO_ANSWER
    if all(int(word) in UNAVAILABLE for word in words):
        return State.UNAVAILABLE
    return State.PRESENT


def stand_in(serial: str) -> str:
    """Return a stable stand-in for a serial, that cannot be read as one.

    Derived from a hash rather than at random, so one machine always maps to
    one stand-in: published files stay diffable across reads and two setups
    stay distinguishable, without the real serials leaving the building.

    The `anon-` prefix is the point. This used to keep the real serial's
    leading letters on the reasoning that a same-shaped value keeps the
    string decoder under test, and that was a bad trade -- `A123456789`
    became `A5155200572`, which is not a serial and looks exactly like one.
    Somebody quoting it into an issue, searching for it, or comparing it
    against the label on a wall gets a plausible wrong answer, and the field
    being called `serial_anonymized_hashed` does not help once the value has
    been copied out of it.

    Must stay identical to `probe._fake_serial`, or one device would get two
    stand-ins depending on which tool read it -- which is exactly the thing
    the hash exists to prevent. `test_the_two_producers_agree_on_the_stand_in`
    holds them together.
    """
    if not serial:
        return serial
    digest = hashlib.sha256(serial.encode("ascii", "replace")).hexdigest()
    digits = "".join(str(int(character, 16) % 10) for character in digest)
    # As many digits as the real serial had, so two setups stay as
    # distinguishable as they were, behind a prefix no Sungrow serial carries.
    return f"{STAND_IN_PREFIX}{digits[: len(serial)]}"


def publishable(name: str) -> bool:
    """Whether a key or label may appear in a published document at all."""
    return not any(word in name.lower() for word in NEVER_PUBLISH)


def address_tail(host: str, permitted: bool) -> str:
    """Return the last two octets of an address, or a refusal to say.

    Two octets rather than one because the third is what separates one
    contributor's network from another's -- three measured installations sit
    on 192.168.178 and two on 192.168.176. That is also the more revealing
    half, which is why it is asked for rather than taken: without permission
    this reads `xxx.xxx`, and a document with `xxx.xxx` in it is complete
    rather than damaged.
    """
    if not permitted:
        return "xxx.xxx"
    parts = str(host).split(".")
    if len(parts) != 4:
        return "xxx.xxx"
    return ".".join(parts[2:])


#: What a document says about WiFi versus Ethernet, which is that it cannot say.
#:
#: Settled against the controlled case rather than argued: bar12's SH10RT-20,
#: one dongle, read wired and then over WiFi. The structural diff is **nil** --
#: identical probe states, identical failed components, identical firmware
#: strings. Latency was the standing hypothesis and does not survive either,
#: which is what the sentence itself explains to whoever opens the document.
#:
#: Copied from `probe.WIFI_OR_ETHERNET` and kept identical by
#: `test_the_two_producers_agree_on_the_wifi_sentence`, because a reader
#: comparing two documents must never have to wonder whether a difference
#: here means something.
WIFI_OR_ETHERNET = (
    "not determinable over Modbus. Nothing in the protocol reports it, "
    "and latency cannot stand in: measured across four installations, "
    "direct-LAN medians run from 2.0 to 61.5 ms and WiNet medians from "
    "24.3 to 48.3, so the ranges overlap -- one house's direct link is "
    "slower than its own dongle. Jitter does not separate them either: a "
    "WiNet-S measured 1.6 ms of spread wired and 4.9 over WiFi on the "
    "same dongle, while another house's wired WiNet spread 8.6. Latency "
    "describes the network between the client and the device, not how the "
    "device is attached. Use the reported_by_hand field."
)


def transport_verdict(*, answered_6100: bool, module_named: bool) -> str:
    """Read the two transport signals into one sentence.

    Two signals, both from the specification rather than inferred. Registers
    **6100-6195** are documented "WiNet-S/S2 and Logger is not supported", so
    if they answer we are not behind one. Register **13265** names the
    communication module if there is one, and a direct-LAN inverter has no
    module and answers the specification's UTF-8 unavailable.

    The first decides, and the second is why: it was written as its equal on
    the reasoning that anything behind a WiNet-S names itself, and a module
    can be *fitted* while not being in the path -- which is a real
    installation rather than a hypothetical, and the top row below.

    Kept identical to `probe.transport_verdict`; the four-row truth table is
    asserted against it, because `doc/compatibility.md` groups readings by
    this string and two spellings of one route would split a comparison.
    """
    if answered_6100 and module_named:
        # This installation has both routes and is on the better one. Worth
        # saying out loud: the path it is not using forwards fewer measuring
        # points and answers zero where the inverter answers "unavailable",
        # which fabricates capabilities.
        return (
            "direct to the inverter's LAN port, with a communication module "
            "fitted as well but not in the path"
        )
    if answered_6100:
        return "direct to the inverter's LAN port"
    if module_named:
        return "through a communication module (WiNet-S, WiNet-S2 or Logger)"
    return (
        "through a communication module (WiNet-S, WiNet-S2 or Logger), "
        "which did not name itself"
    )
