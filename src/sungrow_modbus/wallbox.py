"""Finding a wallbox, and reading it as a device.

**A wallbox cannot be found by looking for it.** Measured at a site whose
owner confirms a LAN cable running into the wallbox: a full sweep of the /24
found Modbus TCP on exactly two addresses, the inverter and its dongle.
Nothing answered on 503 either. The wallbox was reachable **only** as unit 3
behind the dongle's endpoint, and never at 248.

So discovery has to ask the endpoints it already has, rather than sweep for
another one -- which is the same shape the SBR takes, and the reason one
config entry is one endpoint plus whatever answers behind it.

Two unit ids, and neither has a safe default: **3** through a WiNet-S, and
**248** where an RS485-to-TCP adapter puts the wallbox on the network
directly. The direct case is documented by the community projects rather than
measured here, so 248 is tried and nothing is assumed about it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from .addresses import field_address, read
from .wallbox_registers import CODES, COMPONENTS, CONFIDENCE, LOCAL_CLOCK, MODELS

#: Unit ids a wallbox may answer on, in the order to try them.
#:
#: 3 first, because that is the one measured: a WiNet-S forwards the wallbox
#: at unit 3, and it was the only path that worked at the one site with a
#: wallbox. 248 second, from the community projects, for an RS485-to-TCP
#: adapter wired straight to the wallbox.
UNITS: tuple[int, ...] = (3, 248)

#: The register read to decide whether a wallbox is there, and its length.
#:
#: The model *name*, as ASCII across five registers, rather than the device
#: type code next to it. Two reasons, both from measurement. A name is
#: self-validating -- `AC22E-01` is a wallbox and no amount of coincidence
#: makes an inverter answer that -- where a bare code has to be looked up
#: against a table with three entries in it, and a device answering a code
#: outside the table would be dismissed. And the serial sits immediately
#: before this at 21200, so probing the name rather than the serial keeps a
#: serial out of a capability probe entirely, which is a rule this project
#: has already broken once.
MODEL_NAME = field_address("model_name", "wallbox")

#: Words that mean "nothing here", whatever they decode to.
#:
#: `0xFFFF` is the specification's unavailable marker, and `0` is what a
#: WiNet-S answers for a measuring point it does not forward -- which is not
#: the same thing and has invented capabilities before. A wallbox that is
#: absent behind a dongle is one of the two, and neither is a model name.
IMPLAUSIBLE = (0, 0xFFFF)


async def probe_units(
    unit_for: Callable[[int], Any], units: tuple[int, ...] = UNITS
) -> int | None:
    """Return the unit id a wallbox answers on, or None.

    `unit_for` is called with a unit id and returns something with
    `read_input_registers`, which is how this stays testable without a device
    and without Home Assistant -- the same seam `battery.probe_units` uses.

    An answer is not enough; it has to be a **name**. The first version of
    the battery's equivalent took any successful read as evidence and a
    device answering zeros satisfied that, which is precisely what sits
    between us and the hardware in most installations. Here the test is
    stricter still: the words have to decode to printable text, because that
    is what a model name is.
    """
    from modbus_connection import ModbusError

    for unit in units:
        try:
            words = await read(unit_for(unit), MODEL_NAME)
        except (ModbusError, TimeoutError, OSError):
            continue
        if not words or all(int(word) in IMPLAUSIBLE for word in words):
            continue
        if model_name(words):
            return unit
    return None


def model_name(words: list[int]) -> str | None:
    """Decode a model name from the identity registers, or None.

    Sungrow fills a text field it cannot answer with 0x00, which decodes to
    an empty string and would otherwise sail through as a value -- the same
    trap `model.present` exists for one layer up. Anything that is not
    printable ASCII is treated as nothing rather than as a name, because a
    wallbox that is not there does not have a name and a garbled one is
    evidence of reading the wrong device.
    """
    if not words:
        return None
    try:
        raw = b"".join(int(word).to_bytes(2, "big") for word in words)
    except (OverflowError, ValueError):
        return None
    text = raw.decode("ascii", "replace").strip("\x00").strip()
    if not text or "�" in text:
        return None
    # A model name is short, printable and has no control characters in it.
    if not all(32 <= ord(character) < 127 for character in text):
        return None
    return text


def readings(dump: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Decode a wallbox's words into named readings, as a document publishes them.

    `dump` is `{"input": {"21299": 17805, ...}, "holding": {...}}`, protocol
    addresses as strings, the shape `dump.async_dump` returns. Run it on the
    **masked** dump, so no reading can come from a register the document
    refuses to publish. Each field is decoded by its own descriptor, so this
    cannot disagree with the integration's entities about a scale.

    Each reading keeps the register it came from and its `CONFIDENCE`; a code
    carries what it `means`, the type code the `model` it names, and the two
    session times the `local_time` they are. A field with any word missing is
    **absent**, not zero -- a failed read publishing 0 would be a claim about
    somebody's configuration made up out of nothing -- and so is an empty
    string. A reading nobody can name is published under its register number,
    because the next person to see one may recognise it.
    """
    out: dict[str, dict[str, Any]] = {}
    for component in COMPONENTS.values():
        values = dump.get(component.register_space)
        if not isinstance(values, Mapping):
            continue
        for name, field in component.declared_fields.items():
            words = [values.get(str(field.address + i)) for i in range(field.count)]
            present = [int(word) for word in words if word is not None]
            if len(present) < field.count:
                continue
            published = name.removesuffix("_raw")
            value = field.decode(present)
            entry: dict[str, Any] = {
                "register": field.address + 1,
                "held": CONFIDENCE[published],
            }
            if isinstance(value, str):
                if not value.strip():
                    continue
                entry["value"] = value.strip()
            elif published == "device_type_code":
                entry["value"] = f"0x{value:04X}"
                if (model := MODELS.get(value)) is not None:
                    entry["model"] = model
            elif published in LOCAL_CLOCK:
                entry["value"] = value
                entry["local_time"] = _local_time(value)
                entry["note"] = "epoch, but the value is the wallbox's local clock"
            elif published in CODES:
                entry["value"] = value
                entry["means"] = CODES[published].get(value, "unknown code")
            else:
                entry["value"] = value
            if unit := getattr(field, "unit", None):
                entry["unit"] = unit
            out[published] = entry
    return out


def _local_time(value: int) -> str | None:
    """Render a wallbox timestamp: local time wearing an epoch's shape.

    Decoded as UTC it reads two hours off in Berlin and matched the wall clock
    exactly, so the number is the device's own local time -- the same quirk
    the inverter's clock registers have. Rendered without a zone suffix,
    because attaching one would be a claim this cannot support.
    """
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return None


async def async_mapped_words(
    read: Callable[[str, int, int], Any],
) -> dict[str, dict[str, int]]:
    """Read each component's span once, in the shape `readings` decodes.

    For a document without the dump: four reads, the same ranges the poll
    covers, and never the serial, which no component spans. A span that
    fails is left out, so its fields are absent rather than zero.
    """
    from modbus_connection import ModbusError

    words: dict[str, dict[str, int]] = {}
    for component in COMPONENTS.values():
        fields = component.declared_fields.values()
        start = min(field.address for field in fields)
        end = max(field.address + field.count for field in fields)
        try:
            got = await read(component.register_space, start, end - start)
        except (ModbusError, TimeoutError, OSError):
            continue
        space = words.setdefault(component.register_space, {})
        for offset, word in enumerate(got):
            space[str(start + offset)] = int(word)
    return words
