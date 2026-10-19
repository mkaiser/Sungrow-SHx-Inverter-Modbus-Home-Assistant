"""What a capability survey reads, and how to publish it.

One definition of the document format, and two producers of it. The survey in
`device-fingerprints/` imports these tables to read a device from a
terminal; the integration imports them to write the same document from Home
Assistant's diagnostics download, because a user who has already set the
integration up has a working connection and otherwise no way to turn it into
evidence. Every document in `device-fingerprints/` is read by one
generator, whichever of the two wrote it.

Nothing here talks to a device. `PROBES` says which addresses answer the
question, `classify()` says what an answer means, and `stand_in()` is how a
serial leaves the building. The reading itself belongs to whoever has the
connection.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from enum import StrEnum
import hashlib
import ipaddress
import json
from typing import Any, NamedTuple, Protocol, cast

from .addresses import WALLBOX_SERIAL, field_address
from .battery import PACK_UNITS, PACK_VOLTAGE, model_for_capacity
from .const import model_for

#: The document format both producers write. Bumped when the *shape* changes,
#: not when a producer does.
#:
#: 17 allows a document collected through Home Assistant's diagnostics
#: download rather than by running the script. Everything else is identical;
#: what changes is that `command_line` may name a *tool* instead of an
#: invocation, because there is no command to repeat. The history of the
#: earlier numbers is in `device-fingerprints/scripts/python/probe.py`.
#:
#: 19 admits an optional **`control_test`** block, written by
#: `sungrow_modbus.control_test` through either of its two drivers: the result
#: of writing each control, reading it back and watching what the inverter did
#: with it. That is the one question a survey made entirely of reads cannot
#: answer, and the block is anonymous by construction -- register numbers, the
#: values a run chose, the words that came back -- so it publishes the way the
#: block read test already does.
#:
#: A bump rather than a silent addition, for the reason 18 was one: **its
#: absence is not evidence.** Almost every document will lack the block,
#: because producing it means writing to somebody's inverter, so a reader has
#: to be able to tell "this run did not do that" from "this document predates
#: the possibility".
#:
#: `connection.latency_ms` went **without** a bump: nothing read it, so its
#: absence tells a reader nothing.
#:
#: 20 admits an optional **`export_scale`** block: how this firmware writes
#: register 13074, as `sungrow_modbus.inverter.export_scale` asked it -- multiplied by
#: ten, or stored as handed -- with the one write that asked. A bump for the
#: same reason as 19: almost no document will carry it, and "not asked" has to
#: be told apart from "predates the question".
#:
#: 21 admits **`wallbox.serial_anonymized_hashed`**: the wallbox's serial
#: treated as the inverter's is, a `stand_in` hashed from it, so one wallbox
#: is recognisable across readings. Before 21 the serial was only masked, and
#: a reader has to tell "no stand-in could be read" from "predates it".
#:
#: 22 gives **`readings` one meaning whichever producer wrote it**, the
#: terminal survey's: an unavailable field is a None *inside* `values`, and
#: `fields_that_did_not_read` names only fields that failed a read of their
#: own. A document from Home Assistant at 21 or below used that key for the
#: None fields instead and left them out of `values`, so its readings are
#: read by the producer (`command_line` says which) and its number. The same
#: bump widens Home Assistant's `battery_pack` to the terminal survey's: the
#: module block and the unpacked cell and module positions, which an older
#: document from Home Assistant lacks because it never read them, not because
#: the pack withheld them. And `connection.winet_restricted_block_6100` says
#: `answered` for any answer, as the terminal survey always has: Home
#: Assistant wrote the probe's state, and read a sentinel answer as "not
#: reached" -- a cable-connected inverter reported behind a dongle. Its
#: `ip_address_last_two_octets` is zero-filled now too (`107.005`, not
#: `107.5`), as every terminal document's always was.
SCHEMA = 22

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
#: One entry, and it earns its own constant: a serial travels under names --
#: a field called `sungrow_inverter_serial`, a probe labelled "wallbox
#: serial" -- and as raw words a string check cannot see, so the name is what
#: is filtered.
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


#: The probe whose answer decides the transport: register 6100 is not
#: forwarded by a WiNet-S or a Logger, so it answers only on a direct path.
DIRECT_ONLY_LABEL = "PV power of today (6100, direct-only)"

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
    (DIRECT_ONLY_LABEL, "input", 6099, 2, "transport"),
    ("PV power limitation (13018, V1.1.10+)", "holding", 13017, 1, "firmware"),
)

#: The firmware strings, which decide more than the model does.
#:
#: Which registers a device answers moves between versions, so a fingerprint
#: without them cannot be compared with one taken a year later. Two of these
#: are worth knowing the character of: **arm** and **dsp** have been identical
#: on every document ever collected, because they identify *hardware* rather
#: than updatable firmware -- so matching readings are evidence of nothing.
#: `sungrow_version_1`, in the ordinary readings, is the field that actually
#: tracks an update.
#:
#: `communication_module` is **not** a connection signal. It names the module
#: that is *fitted*, not the one in the path, and through a dongle it can
#: answer empty -- wrong in both directions. It is reported beside register
#: 6100, which decides transport, as a separate fact.
#:
#: Each published name, by the inverter field that holds it: the one table,
#: so a survey reading raw words and one reading polled fields cannot drift.
FIRMWARE_FIELDS: dict[str, str] = {
    "arm": "sungrow_arm_software",
    "dsp": "sungrow_dsp_software",
    "inverter": "inverter_firmware_version",
    "communication_module": "communication_module_firmware_version",
    "battery": "battery_firmware_version",
}

#: The same, as raw reads for a producer that has no polled device:
#: (name, space, address, count), from the register map.
FIRMWARE_STRINGS: tuple[tuple[str, str, int, int], ...] = tuple(
    (name, where.space, where.address, where.length)
    for name, where in (
        (name, field_address(field)) for name, field in FIRMWARE_FIELDS.items()
    )
)

#: How many words a presence probe reads -- "does anything answer at this
#: unit" -- whatever the register's own width. Enough to tell an answer from
#: a refusal, and the count every published document was read with.
PRESENCE_WORDS = 2

#: Devices that live on unit ids of their own behind the inverter's endpoint,
#: as (published label, unit, input address). Any answer is `present`, any
#: failure `no answer`: the question is only whether something is there.
#:
#: A WiNet-S forwards the SBR at unit 2 instead of 200 -- measured on three
#: dongles -- and unit 2 is also where a slave inverter lives, so the device
#: type code is read there too: a slave answers it and a battery does not.
SIBLING_PROBES: tuple[tuple[str, int, int], ...] = (
    ("unit 200 SBR battery module block", 200, PACK_VOLTAGE.address),
    ("unit 2 SBR battery module block", 2, PACK_VOLTAGE.address),
    (
        "unit 2 inverter device type code",
        2,
        field_address("device_type_code").address,
    ),
    ("unit 3 wallbox serial", 3, WALLBOX_SERIAL.address),
    ("unit 248 wallbox serial (direct)", 248, WALLBOX_SERIAL.address),
)

#: The wallbox labels by unit, through a dongle and at its own address.
WALLBOX_PROBES: dict[int, str] = {
    3: "unit 3 wallbox serial",
    248: "unit 248 wallbox serial (direct)",
}


def slave_inverter_at(states: Mapping[str, object], unit: int) -> bool:
    """Whether an inverter, not a battery, answered at this sibling unit."""
    return states.get(f"unit {unit} inverter device type code") == State.PRESENT


def battery_pack_unit(states: Mapping[str, object]) -> int | None:
    """Return the unit a Sungrow pack answered on, from the sibling probes.

    `states` maps each probe label to its state. Unit 200 first, as the
    specification places it; unit 2 only where no inverter answered there,
    or a master/slave pair would report the slave as the master's pack.
    """
    for unit in PACK_UNITS:
        if states.get(f"unit {unit} SBR battery module block") != State.PRESENT:
            continue
        if unit != 200 and slave_inverter_at(states, unit):
            continue
        return unit
    return None


def wallbox_unit(states: Mapping[str, object]) -> int | None:
    """Return the unit a wallbox answered on, from the sibling probes."""
    for unit, label in WALLBOX_PROBES.items():
        if states.get(label) == State.PRESENT:
            return unit
    return None


#: What a stand-in serial always begins with, and cannot occur in a real one.
STAND_IN_PREFIX = "anon-"

#: The values `user_inputs.transport` may hold, which are part of the format.
#:
#: Keys only. The human wording lives with each producer -- a menu line in the
#: script, a translated string in the integration -- because that is
#: presentation, while the key is what `generate_compatibility.py` groups by.
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

#: The values `user_inputs.other_inverter` may hold, with the same
#: empty-means-unasked rule as the two above.
#:
#: The question is whether the installation holds a **non-Sungrow** inverter,
#: and it is worth a field of its own because of what it does to a reading
#: that otherwise looks like a fault. A Sungrow computes house load from its
#: own output plus grid import, so a second inverter feeding the same meter
#: makes `load_power` low by exactly that inverter's output -- silently, with
#: every register answering normally. A maintainer reading a document whose
#: load figures do not add up has no way to tell that from a decoding bug,
#: and no register can answer it: the inverter cannot see the thing that is
#: confusing it. `external.py` in the integration corrects for this from
#: entities another integration owns, which is the only value in the project
#: that comes from Home Assistant rather than from Modbus.
#:
#: Two answers rather than three. An owner knows what is on their own roof,
#: where "is a proxy in the path" is genuinely a thing somebody may not know.
OTHER_INVERTER_CLAIMS: tuple[str, ...] = ("yes", "no")

#: The one of those two that opens the follow-up question, named rather than
#: written out at the three places that compare against it. A literal "yes" in
#: a flow, a scanner and a document builder is three chances to disagree about
#: a string that decides whether anybody is asked what the other inverter is.
OTHER_INVERTER_YES = OTHER_INVERTER_CLAIMS[0]


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

    The `anon-` prefix is the point. A stand-in that kept a serial's shape
    would look exactly like a serial: somebody quoting it into an issue,
    searching for it, or comparing it against the label on a wall gets a
    plausible wrong answer, and the field being called
    `serial_anonymized_hashed` does not help once the value has been copied
    out of it.

    Both producers call this, so one device gets one stand-in whichever tool
    read it -- which is exactly what the hash exists to provide.
    """
    if not serial:
        return serial
    digest = hashlib.sha256(serial.encode("ascii", "replace")).hexdigest()
    digits = "".join(str(int(character, 16) % 10) for character in digest)
    # As many digits as the real serial had, so two setups stay as
    # distinguishable as they were, behind a prefix no Sungrow serial carries.
    return f"{STAND_IN_PREFIX}{digits[: len(serial)]}"


def device_block(
    device_type_code: int | str | None,
    output_type: object,
    serial: str,
) -> dict[str, object]:
    """Build the privacy-safe device section shared by survey producers."""
    if isinstance(device_type_code, str):
        try:
            numeric_code = int(device_type_code, 16)
        except ValueError:
            numeric_code = None
    else:
        numeric_code = device_type_code
    mapped_output: object = (
        OUTPUT_TYPES.get(output_type, output_type)
        if isinstance(output_type, int)
        else output_type
    )
    return {
        "device_type_code": (
            f"0x{numeric_code:04X}" if numeric_code is not None else None
        ),
        "device_type": model_for(numeric_code) if numeric_code is not None else None,
        "output_type": mapped_output,
        "serial_anonymized_hashed": stand_in(serial),
    }


def publishable(name: str) -> bool:
    """Whether a key or label may appear in a published document at all."""
    return not any(word in name.lower() for word in NEVER_PUBLISH)


def capability_registers(
    fingerprint_registers: Mapping[str, object],
    raw_registers: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Build the privacy-safe capability register section."""
    registers: dict[str, dict[str, object]] = {}
    for label, state in fingerprint_registers.items():
        entry: dict[str, object] = {"state": state}
        values = raw_registers.get(label)
        if values is not None and publishable(label):
            entry["values"] = values
        registers[label] = entry
    return registers


class FieldSource(Protocol):
    """A library device that can enumerate and return its decoded fields."""

    @property
    def field_names(self) -> frozenset[str]:
        """Every field name `field()` accepts."""
        ...

    def field(self, name: str) -> object:
        """Return one decoded value, or None when it did not read."""
        ...


def _published_fields(device: FieldSource) -> dict[str, object]:
    """Return every publishable field of a device, None where it did not read."""
    values: dict[str, object] = {}
    for name in sorted(device.field_names):
        if not publishable(name):
            continue
        try:
            values[name] = device.field(name)
        except (AttributeError, KeyError):
            continue
    return values


def readings_section(
    device: FieldSource,
    failed_components: Iterable[str] = (),
    *,
    salvaged: Mapping[str, object] | None = None,
    unreadable: Iterable[str] = (),
) -> dict[str, object]:
    """Every decoded value of a device, and what did not read.

    `values` holds every publishable field, **None included**: None is the
    specification's unavailable sentinel, or a field whose component failed,
    and `components_that_did_not_answer` says which. Two lists appear only
    when a producer read fields one at a time after a component failed:
    `fields_read_individually` for what that recovered -- from a different
    moment than its neighbours, which is why it is named -- and
    `fields_that_did_not_read` for what did not answer even alone. Not
    "refused": that is a claim about the device, and this is only what did
    not read after several separated attempts.

    `NEVER_PUBLISH` applies to the lists as well as the values: a field
    *name* is not a serial, but the rule is kept absolute.
    """
    values = _published_fields(device)
    recovered = dict(salvaged or {})
    # The recovered values live in throwaway components, not the device's
    # stores; overlay them only where the component read left nothing.
    for name, value in recovered.items():
        if publishable(name) and values.get(name) is None:
            values[name] = value
    report: dict[str, object] = {
        "values": values,
        # Sorted, so two readings of one machine differ only where it did.
        "components_that_did_not_answer": sorted(failed_components),
    }
    named = sorted(name for name in recovered if publishable(name))
    if named:
        report["fields_read_individually"] = named
    silent = sorted(name for name in unreadable if publishable(name))
    if silent:
        report["fields_that_did_not_read"] = silent
    return report


def firmware_section(device: FieldSource) -> dict[str, str | None]:
    """Return the five published firmware strings, from a polled device."""
    values: dict[str, str | None] = {}
    for name, field in FIRMWARE_FIELDS.items():
        try:
            value = device.field(field)
        except (AttributeError, KeyError):
            value = None
        values[name] = None if value is None else str(value)
    return values


def battery_readings(
    device: FieldSource,
    failed_components: Iterable[str] = (),
    *,
    unanswered_fields: Iterable[str] = (),
) -> dict[str, object]:
    """Return a pack's readings: every field that answered, and what failed.

    The pack's components are read and reported separately because they fail
    separately -- through a dongle the cell block refuses while the pack
    block answers -- so one failing must not make the pack look unreadable.
    `unanswered_fields` are the failed components' fields, left out rather
    than published as None: None is the pack saying a point is unavailable,
    which a block that never answered did not say.
    """
    omitted = set(unanswered_fields)
    return {
        "values": {
            name: value
            for name, value in _published_fields(device).items()
            if name not in omitted
        },
        "components_that_did_not_answer": list(failed_components),
    }


def battery_pack_section(
    device: FieldSource,
    unit: int,
    failed_components: Iterable[str] = (),
    *,
    unanswered_fields: Iterable[str] = (),
) -> dict[str, object] | None:
    """Return a battery pack's section, or None when nothing decoded.

    `battery_pack` and never `battery`: that key holds what the owner *typed*
    about their battery, and a measurement must not overwrite testimony.
    None rather than a section of Nones, which
    would say the pack was read and reported nothing.
    """
    readings = battery_readings(
        device, failed_components, unanswered_fields=unanswered_fields
    )
    values = cast(dict[str, object], readings["values"])
    if all(value is None for value in values.values()):
        return None
    return {"unit": unit, "readings": readings}


def wallbox_section(
    unit: int,
    *,
    readings: Mapping[str, object],
    serial_stand_in: str | None = None,
    path: str | None = None,
    register_dump: Mapping[str, object] | None = None,
    connection: object = None,
) -> dict[str, object]:
    """Return a wallbox's section, from readings the caller has decoded.

    The readings must come from **masked** words, so none can come from a
    register the document refuses to publish: the serial sits two registers
    below the model name, and raw words carry it past any string check.
    `wallbox_from_dump` does that for a raw dump.
    """
    section: dict[str, object] = {"unit": unit}
    if path is not None:
        # Which way it was reached, because the two do not read alike: a
        # dongle answers 0 for several registers the wallbox's own address
        # answers with values.
        section["path"] = path
    if connection is not None:
        section["connection"] = connection
    if serial_stand_in:
        section["serial_anonymized_hashed"] = serial_stand_in
    section["readings"] = dict(readings)
    if register_dump is not None:
        section["register_dump"] = dict(register_dump)
    return section


def wallbox_from_dump(
    unit: int,
    raw_dump: Mapping[str, Any],
    *,
    path: str | None = None,
    connection: object = None,
) -> dict[str, object]:
    """Return a wallbox's section from its unmasked register dump.

    Masked with the wallbox's own mask rather than the inverter's -- the two
    serials live at different addresses, and using the wrong one publishes a
    serial while looking careful. The stand-in is hashed from the raw words
    before the mask; the readings and the dump come from after it.
    """
    from . import dump as register_dump, wallbox

    masked = register_dump.masked(dict(raw_dump), register_dump.WALLBOX_MASKED)
    return wallbox_section(
        unit,
        readings=wallbox.readings(masked),
        serial_stand_in=wallbox.serial_stand_in(raw_dump),
        path=path,
        register_dump=masked,
        connection=connection,
    )


#: The `document` key of a wallbox read at its own address, which is a
#: document of its own: no `device` section, and its own filename. Inverter
#: documents carry no `document` key, so the corpus tells the two apart by
#: this value rather than by folder.
WALLBOX_DOCUMENT = "wallbox"


def wallbox_document(
    *,
    command_line: str,
    read_at: str,
    user_inputs: Mapping[str, object],
    address_tail: str,
    connection: Mapping[str, object],
    wallbox: Mapping[str, object],
) -> dict[str, object]:
    """Build the document for a wallbox read at its own address.

    `wallbox` is a `wallbox_section`, already masked. `user_inputs` keeps only
    what was answered: a wallbox survey asks two questions, not the inverter's
    seven, and an empty key would claim a question was put.
    """
    return {
        "schema": SCHEMA,
        "document": WALLBOX_DOCUMENT,
        "command_line": command_line,
        "read_at": read_at,
        "user_inputs": {key: value for key, value in user_inputs.items() if value},
        "ip_address_last_two_octets": address_tail,
        "connection": dict(connection),
        "wallbox": dict(wallbox),
    }


def wallbox_label_for(document: Mapping[str, Any]) -> str:
    """Name a wallbox document: model, reporter, stand-in, and the path.

    The same order as an inverter's label, so the files sort the same way:
    what it is, who read it, which unit it was.
    """
    section = document.get("wallbox") or {}
    readings = section.get("readings") or {}
    model = str((readings.get("model_name") or {}).get("value") or "wallbox")
    parts = [model.lower().replace("-", "").replace(".", "")]
    reporter = str((document.get("user_inputs") or {}).get("reporter") or "")
    if reporter:
        parts.append(
            "".join(c if c.isalnum() else "-" for c in reporter.lower()).strip("-")
        )
    serial = str(section.get("serial_anonymized_hashed") or "")
    if serial.startswith(STAND_IN_PREFIX):
        parts.append(serial)
    parts += ["wallbox", str(section.get("path") or "tls")]
    return "-".join(part for part in parts if part)


def assemble_document(
    *,
    command_line: str,
    read_at: str,
    user_inputs: Mapping[str, object],
    host: str,
    publish_address: bool,
    device_type_code: int | str | None,
    output_type: object,
    serial: str,
    firmware: object,
    connection: object,
    readings: object,
    capability_probes: Mapping[str, object],
    contention: Mapping[str, object] | None = None,
    register_dump: Mapping[str, Any] | None = None,
    wallbox: Mapping[str, object] | None = None,
    block_read_test: object = None,
    battery_pack: Mapping[str, Any] | None = None,
    control_test: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the publishable document from sections already collected.

    The one builder: the terminal survey reaches it through
    `publish_document`, Home Assistant directly. Each caller owns how a
    section was collected; this owns which sections exist, their order, and
    what is removed before anything is published.

    `user_inputs` is everything a person typed, in one section and first: the
    only values in the file not read off a wire, kept apart so a claim is
    never quoted back as a measurement. Each exists because Modbus cannot
    answer it -- no register names a battery's make, a master reads exactly
    like a lone inverter, and a WiNet-S answers the same wired as over WiFi.
    An empty answer means the question was not put, which is a different
    statement from `unknown`. For the same reason `connection` loses any
    testimony a caller left in it.

    `capability_probes` follows the measured sections because it is four
    lines per register, and somebody opening a document wants to know *which
    setup it is* first. `contention` is what the producer itself was doing to
    the link, which only Home Assistant can measure.

    `register_dump` is the raw bands and is masked here, never by a caller:
    the serial's ten registers sit inside the identity band and would
    otherwise be published as words. `wallbox` is a finished section, from
    `wallbox_section` or `wallbox_from_dump`, which own its mask. A
    `battery_pack` with no value read is left out: a pack that answered its
    presence probe already says so under `capability_probes`.
    """
    from . import dump as dump_module

    document: dict[str, object] = {
        "schema": SCHEMA,
        "command_line": command_line,
        "read_at": read_at,
        "user_inputs": dict(user_inputs),
        "ip_address_last_two_octets": address_tail(host, publish_address),
        "device": device_block(device_type_code, output_type, serial),
        "firmware": firmware,
        "connection": (
            measured_connection(connection)
            if isinstance(connection, Mapping)
            else connection
        ),
        "readings": readings,
        "capability_probes": capability_probes,
    }
    if contention is not None:
        document["contention"] = dict(contention)
    if register_dump:
        document["register_dump"] = dump_module.masked(dict(register_dump))
    if wallbox:
        document["wallbox"] = dict(wallbox)
    # What the block read test measured, when one ran. A maintainer reading a
    # submitted document needs it to see which blocks the integration would
    # fail on; the transcript, which also has it, is the file a contributor
    # keeps because it holds their real address.
    if block_read_test:
        document["block_read_test"] = block_read_test
    if battery_pack and (battery_pack.get("readings") or {}).get("values"):
        document["battery_pack"] = dict(battery_pack)
    if control_test:
        attach_control_test(document, control_test, serial=serial)
    return document


def attach_control_test(
    document: dict[str, Any] | dict[str, object],
    block: Mapping[str, object],
    *,
    serial: str,
) -> None:
    """Put part B's result into a document, having checked it may be published.

    Its own function because part B runs *after* part A -- part A is what
    establishes that this device answers and what it is -- so a caller may
    attach the block to a document that already exists. Attaching it
    afterwards must not mean attaching it unchecked, and one guarded door is
    the only way to be sure it does not.

    The block is anonymous by construction -- register numbers, chosen values,
    words that came back -- so the check should never fire. It is here
    because "should never" is what a serial in raw words slips past. A
    refusal costs somebody a run they can repeat; publishing costs somebody
    else their serial number in a public repository, permanently.
    """
    if serial and serial in json.dumps(block, default=str):
        raise ValueError(
            "refusing to publish the control test block: it carries the serial"
        )
    document["control_test"] = dict(block)


def publish_document(
    raw: Mapping[str, object],
    fingerprint: Mapping[str, object],
    *,
    command_line: str,
    host: str,
    publish_address: bool,
    user_inputs: Mapping[str, object],
    serial: str,
) -> dict[str, object]:
    """Build the document from the terminal survey's collected dicts.

    ``raw`` holds the measurements -- read words, decoded sections and the
    optional dumps, block test, battery and control test -- and
    ``fingerprint`` the identity and the probe states, as `probe.py`
    collects them. This only unpacks them for `assemble_document`; the
    wallbox arrives as a raw dump and is shaped by `wallbox_from_dump`.
    """
    raw_data = cast(dict[str, Any], raw)
    fingerprint_data = cast(dict[str, Any], fingerprint)
    wallbox_raw = raw_data.get("wallbox") or {}
    return assemble_document(
        command_line=command_line,
        read_at=str(raw_data["read_at"]),
        user_inputs=user_inputs,
        host=host,
        publish_address=publish_address,
        device_type_code=fingerprint_data.get("device_type_code"),
        output_type=fingerprint_data.get("output_type"),
        serial=serial,
        firmware=raw_data.get("firmware", {}),
        connection=raw_data.get("connection", {}),
        readings=raw_data.get("readings", {}),
        capability_probes=capability_registers(
            fingerprint_data.get("registers", {}),
            raw_data.get("registers", {}),
        ),
        register_dump=raw_data.get("register_dump"),
        wallbox=(
            wallbox_from_dump(
                wallbox_raw["unit"],
                wallbox_raw["register_dump"],
                # Found behind the inverter's endpoint, so not at its own
                # address over TLS: "dongle", as the integration writes it.
                path=wallbox_raw.get("path") or "dongle",
                connection=wallbox_raw.get("connection"),
            )
            if wallbox_raw.get("register_dump")
            else None
        ),
        block_read_test=raw_data.get("block_read_test"),
        battery_pack=raw_data.get("battery_pack"),
        control_test=raw_data.get("control_test"),
    )


def collected_nothing(document: Mapping[str, Any]) -> bool:
    """Whether a document holds no value read from the device at all.

    No decoded reading and no answered address in the raw bands. Either one
    is a reading worth keeping, however thin; neither is a document of
    nothing, which is the link failing and not worth sending.
    """
    from . import dump as register_dump

    values = (document.get("readings") or {}).get("values") or {}
    if any(value is not None for value in values.values()):
        return False
    return not register_dump.answered(document.get("register_dump") or {})


def measured_connection(
    connection: Mapping[str, object],
    claimed_key: str = "reported_by_hand",
) -> dict[str, object]:
    """Remove owner testimony from the measured connection section."""
    return {key: value for key, value in connection.items() if key != claimed_key}


def last_two_octets(host: str) -> str | None:
    """Return the last two octets of an IPv4 address, each zero-filled.

    Strings rather than numbers, because JSON cannot write a leading zero.
    Three digits is the widest an octet gets, so every value is the same
    width: "178.029" beside "178.114" lines up in a table and sorts as text
    in the order an address sorts, where 4, 28 and 128 as numbers-in-text
    would not.

    Two octets rather than one because the third is what separates one
    contributor's network from another's -- three of the installations on
    record sit on 192.168.178 and two on 192.168.176, which one octet cannot
    show. It is also the more revealing half, which is why it is asked for
    rather than taken.

    A hostname has no octets, and neither does an IPv6 address; both are
    perfectly ordinary things to point this script at, so both give None
    rather than a guess at the last things after a dot.
    """
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return None
    if address.version != 4:
        return None
    third, fourth = str(address).split(".")[2:]
    return f"{int(third):03d}.{int(fourth):03d}"


def address_tail(host: str, permitted: bool) -> str:
    """Return the published address tail, or a refusal to say.

    Only ever with permission: the tail is asked for rather than taken, and
    without it this reads `xxx.xxx` -- a document with that in it is complete
    rather than damaged. A hostname or an IPv6 address has no octets and
    reads the same.
    """
    if not permitted:
        return "xxx.xxx"
    return last_two_octets(host) or "xxx.xxx"


def local_time(read_at: str, zone: str = "Europe/Berlin") -> str:
    """Render an ISO timestamp in the survey's local zone when available."""
    try:
        from zoneinfo import ZoneInfo

        moment = datetime.fromisoformat(read_at).astimezone(ZoneInfo(zone))
    except (ValueError, KeyError, ModuleNotFoundError):
        return read_at
    return moment.isoformat(timespec="seconds")


#: What a document says about WiFi versus Ethernet, which is that it cannot say.
#:
#: Settled against the controlled case rather than argued: bar12's SH10RT-20,
#: one dongle, read wired and then over WiFi. The structural diff is **nil** --
#: identical probe states, identical failed components, identical firmware
#: strings. Nothing in the register space moves, so a person has to say it.
#:
#: One sentence for every document, because a reader comparing two must never
#: have to wonder whether a difference here means something.
WIFI_OR_ETHERNET = (
    "not determinable over Modbus. Nothing in the protocol reports it, and "
    "a WiNet-S answers identically wired and over WiFi. Use "
    "user_inputs.transport, which is what the contributor said."
)


def transport_verdict(*, answered_6100: bool, module_named: bool) -> str:
    """Read the two transport signals into one sentence.

    Two signals, both from the specification rather than inferred. Registers
    **6100-6195** are documented "WiNet-S/S2 and Logger is not supported", so
    if they answer we are not behind one. Register **13265** names the
    communication module if there is one, and a direct-LAN inverter has no
    module and answers the specification's UTF-8 unavailable.

    The first decides. The second is not its equal: a module can be *fitted*
    while not being in the path -- a real installation, and the top row
    below -- and through a dongle it can answer empty.

    Both producers call this, because `doc/compatibility.md` groups readings
    by this string and two spellings of one route would split a comparison.
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


#: What `winet_restricted_block_6100` says when the block answered at all.
ANSWERED_6100 = "answered"

#: The verdict when register 6100 got no answer at all: neither route is
#: shown, so none is claimed, and no transport goes into a filename.
TRANSPORT_NOT_DETERMINED = (
    "not determined: register 6100 got no answer, so the route could not be told"
)


def connection_block(restricted_state: str, module: str | None) -> dict[str, object]:
    """Build the measured connection section shared by survey producers.

    `restricted_state` may be a probe's `State` or the word `answered`. Any
    answer -- the sentinel included -- is published as `answered`, because
    the question is whether the path forwards the block, not what it holds:
    a dongle refuses 6100, it does not answer 0xFFFF for it.
    """
    if restricted_state in {str(State.PRESENT), str(State.UNAVAILABLE)}:
        restricted_state = ANSWERED_6100
    if restricted_state == str(State.NO_ANSWER):
        verdict = TRANSPORT_NOT_DETERMINED
    else:
        verdict = transport_verdict(
            answered_6100=restricted_state == ANSWERED_6100,
            module_named=bool(module),
        )
    return {
        "communication_module_firmware": module or "",
        "verdict": verdict,
        "wifi_or_ethernet": WIFI_OR_ETHERNET,
        "winet_restricted_block_6100": restricted_state,
    }


class ReportedTransport(NamedTuple):
    """What a reported transport means in a document, beside its key."""

    verdict: str
    """The sentence it becomes, phrased like a measured verdict so everything
    reading a verdict keeps working. Empty for `unsure`, which outranks
    nothing."""
    table: str
    """How `doc/compatibility.md` names it."""
    word: str
    """Its word in a filename."""


#: What each `TRANSPORT_CLAIMS` key means once it is in a document.
#:
#: `winet_lan` and `winet_wlan` are worth separating even though Modbus cannot
#: tell them apart -- that is exactly why. The protocol reports nothing about
#: the medium, so a person has to be the one to say it.
#:
#: The filename word names every route, the inverter's own LAN port included.
#: A reading through a dongle changes which registers answer, so a reader
#: comparing two documents needs the route in front of them, and one dongle
#: read wired and over WiFi produces two documents that would otherwise
#: derive the same name. Only "not sure" adds nothing.
REPORTED_TRANSPORTS: dict[str, ReportedTransport] = {
    "direct_lan": ReportedTransport(
        "direct to the inverter's LAN port (reported by the contributor)",
        "direct LAN port",
        "direct-lan",
    ),
    "winet_lan": ReportedTransport(
        "through a WiNet-S, wired (reported by the contributor)",
        "WiNet-S, wired",
        "winet-lan",
    ),
    "winet_wlan": ReportedTransport(
        "through a WiNet-S, over WiFi (reported by the contributor)",
        "WiNet-S, WiFi",
        "winet-wlan",
    ),
    "winet": ReportedTransport(
        "through a WiNet-S (reported by the contributor)",
        "WiNet-S",
        "winet",
    ),
    "logger": ReportedTransport(
        "through a Logger (reported by the contributor)",
        "Logger",
        "logger",
    ),
    "unsure": ReportedTransport("", "", ""),
}

#: The filename word for each reported transport.
TRANSPORT_WORDS: dict[str, str] = {
    key: reported.word for key, reported in REPORTED_TRANSPORTS.items()
}


def claim_of(verdict: str) -> str | None:
    """Return what a verdict actually claims: `direct`, `module`, or None.

    Verdicts are sentences so that a reader gets the reasoning, which makes
    them the wrong thing to compare. None for the "not determined" cases, so
    a measurement that concluded nothing can contradict nobody.
    """
    if verdict.startswith("direct"):
        return "direct"
    if verdict.startswith(
        ("through a communication module", "through a WiNet-S", "through a Logger")
    ):
        return "module"
    return None


def effective_verdict(connection: Mapping[str, object]) -> str:
    """Return the transport to act on: what somebody said, else what was read.

    Testimony outranks the measurement here, the opposite of the rule
    everywhere else, because the measurement cannot reach the question in
    one case that matters: a WiNet-S answers the same wired as over WiFi --
    one dongle read on both of its addresses produced identical documents.
    `unsure` maps to an empty verdict, so not knowing outranks nothing.
    """
    reported = str(connection.get("reported_by_hand") or "")
    said = REPORTED_TRANSPORTS.get(reported)
    return (said.verdict if said else "") or str(connection.get("verdict", ""))


def transport_contradiction(verdict: str, reported: str) -> tuple[str, str] | None:
    """Return (measured, said) claims when the owner's answer contradicts the wire.

    None when they agree, or when either side claims nothing -- a verdict that
    concluded nothing, or an owner who said they are not sure. Said at the
    moment it can be acted on, never stored: a comparison of two values in
    one file goes stale when the verdict logic changes.
    """
    said = REPORTED_TRANSPORTS.get(reported)
    measured = claim_of(verdict)
    claimed = claim_of(said.verdict) if said else None
    if measured is None or claimed is None or measured == claimed:
        return None
    return measured, claimed


def _slug(text: str) -> str:
    """Return text safe to put in a filename, or "anonymous" if nothing is left.

    Contributor names arrive as free text and land in a filename that goes
    into a public repository, so anything outside a-z, 0-9 and a dash becomes
    a dash.
    """
    kept = "".join(c if c.isalnum() else "-" for c in text.strip().lower())
    return "-".join(part for part in kept.split("-") if part) or "anonymous"


def _probe(document: dict[str, Any], name: str) -> dict[str, Any]:
    """Return one capability probe's published entry, or an empty one."""
    probes = document.get("capability_probes") or {}
    entry = probes.get(name)
    return entry if isinstance(entry, dict) else {}


def _answered(document: dict[str, Any], *names: str) -> bool:
    """Whether any of these probes came back with a value."""
    return any(_probe(document, name).get("state") == State.PRESENT for name in names)


def _reached_directly(document: dict[str, Any]) -> bool:
    """Whether this reading came through the inverter's own port.

    Testimony outranks the measurement, which is the opposite of the rule
    everywhere else here and has to be: a WiNet-S answers identically wired
    and over WiFi, so the medium is knowable only to the person who plugged
    the cable in. `unsure` is not testimony and overrides nothing.
    """
    said = str((document.get("user_inputs") or {}).get("transport") or "")
    if said and said != "unsure":
        return said == "direct_lan"
    verdict = str((document.get("connection") or {}).get("verdict") or "")
    return verdict.startswith("direct")


def _battery_word(document: dict[str, Any]) -> str:
    """Return what can honestly be said about the battery, in one word.

    Every state is prefixed `battery-` so the words sort together and read as
    one field. The distinction that earns its keep is the last pair: battery
    registers answering while unit 200 stays silent means a third-party pack
    **on a direct path**, where the specification puts the Sungrow module
    block at unit 200 -- and means nothing at all behind a dongle, which
    forwards the pack at an address of its own choosing. The two look
    identical over the wire and are not the same fact.
    """
    probe_states = {
        label: entry.get("state")
        for label, entry in (document.get("capability_probes") or {}).items()
        if isinstance(entry, dict)
    }
    if battery_pack_unit(probe_states) is not None:
        values = _probe(document, "battery capacity (5639)").get("values")
        if values:
            model = model_for_capacity(values[0] * 0.01)
            if model is not None:
                return f"battery-{model.name.lower()}"
        return "battery-sungrow"

    pair = ("battery voltage", "battery level")
    read = [_probe(document, name) for name in pair]
    if read and all(entry.get("values") and not any(entry["values"]) for entry in read):
        # Zeros rather than the sentinel, which is how a cluster slave says it
        # has no battery of its own. Checked before "present", because a zero
        # decodes as a value and would otherwise read as a third-party pack.
        return "battery-none"
    states = [entry.get("state") for entry in read]
    if any(state == State.PRESENT for state in states):
        return (
            "battery-thirdparty" if _reached_directly(document) else "battery-unknown"
        )
    if any(state == State.UNAVAILABLE for state in states):
        return "battery-none"
    return "battery-unreadable"


def firmware_word(firmware: Mapping[str, object]) -> str:
    """Return the inverter firmware as a filename word, or "" if it did not read.

    `SAPPHIRE-H_B001.V000.P022` becomes `b001v000p022`. The family prefix goes
    because the model word already says `sh80rt`, and the punctuation goes
    because a filename reads better without it -- the document keeps the
    string exactly as the device gave it. Everything after the first
    underscore is the version; a string with no underscore is taken whole.
    """
    value = str(firmware.get("inverter") or "")
    if not value:
        return ""
    return _slug(value.split("_", 1)[-1]).replace("-", "")


def label_for(document: dict[str, Any]) -> str:
    """Return the filename this document should carry, without its extension.

    **Derived from the published document alone**, which is the whole point:
    the standalone survey builds the same name from the structures it holds
    before publishing, and this reaches the identical answer from the file
    itself. `tests/test_document_filenames.py` asserts that over every
    fingerprint this repository has committed, which is a stronger check than
    any pair of unit tests -- the corpus is the specification.

    Order is `model-firmware-phases-contributor-standin`, then the battery,
    meter, wallbox and transport words. The stand-in comes before everything
    attached so that every document from one machine shares a prefix and they
    group when a directory is sorted: one inverter read directly and through
    its dongle differs only in the words *after* it.

    Nothing here can leak: the model, the firmware and the phases are
    properties of a product line, the stand-in is the document's own and is
    required to say so, and the contributor's name is one they typed.
    """
    device = document.get("device") or {}
    said = document.get("user_inputs") or {}

    code = str(device.get("device_type_code") or "")
    model = "unknown"
    if code.startswith("0x"):
        try:
            model = (model_for(int(code, 16)) or "unknown").lower().replace(".", "")
        except ValueError:
            model = "unknown"
    parts = [model]

    # Directly after the model, because it qualifies the model and nothing
    # else: which registers a device answers moves between versions, so
    # `sh80rt` alone does not say what to expect and `sh80rt-b001v000p022`
    # does. Omitted rather than filled in when it did not read -- a name
    # silent about firmware is honest, where `fw-unknown` would sort as
    # though it were a version.
    firmware = firmware_word(document.get("firmware") or {})
    if firmware:
        parts.append(firmware)

    parts += _phase_word(device)

    parts.append(_slug(str(said.get("reporter") or "")))

    # Only ever a value that says it is a stand-in. Putting the string in
    # unchecked is how a real serial would reach a filename, and `anon-`
    # cannot occur in a Sungrow serial -- which makes the mistake
    # unrepresentable rather than merely unlikely.
    stand_in = str(device.get("serial_anonymized_hashed") or "")
    if stand_in.startswith(STAND_IN_PREFIX):
        parts.append(_slug(stand_in))

    parts.append(_battery_word(document))
    if _answered(document, "meter phase A voltage (5741)"):
        parts.append("meter")
    if _answered(document, *WALLBOX_PROBES.values()):
        parts.append("wallbox")

    parts += _transport_word(document, said)

    return "-".join(parts)


def _phase_word(device: dict[str, Any]) -> list[str]:
    """Name the supply: the phase count always, the wiring only where unusual.

    3P4L is an ordinary domestic three-phase supply and is just `3p`. **3P3L
    has to be named** (`3p3w`): it has no neutral, and the same registers then
    report line voltages rather than phase voltages -- about 1.73x higher --
    so a reader comparing two documents needs the warning before they compare
    the numbers.

    A list rather than a string so the caller stays a sequence of parts, and so
    "say nothing" is the empty list rather than a falsy value to test for.
    """
    phases = str(device.get("output_type") or "")
    if "3P3L" in phases:
        return ["3p3w"]
    if "3P4L" in phases:
        return ["3p"]
    if "single" in phases:
        return ["1p"]
    return []


def _transport_word(document: dict[str, Any], said: dict[str, Any]) -> list[str]:
    """Name how the survey reached the inverter: what was said, else what showed.

    Testimony first, because the owner knows what is plugged in and no register
    reports it. Where they did not say, the connection verdict is the
    measurement -- input 6100 answers on a cable and is refused through a
    WiNet-S, at every site measured -- and that is worth a word in the filename
    because a dongle forwards less than a cable does, so two documents from one
    machine can legitimately disagree about which registers exist.
    """
    word = TRANSPORT_WORDS.get(str(said.get("transport") or ""), "")
    if not word:
        verdict = str((document.get("connection") or {}).get("verdict") or "")
        if verdict.startswith("direct"):
            word = "direct-lan"
        elif verdict.startswith(
            ("through a communication module", "through a WiNet-S")
        ):
            word = "winet"
        elif verdict.startswith("through a Logger"):
            word = "logger"
    return [word] if word else []
