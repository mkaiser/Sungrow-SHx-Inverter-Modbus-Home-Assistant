"""Finding a wallbox, on whichever unit it answers.

**A sweep for port 502 does not find a wallbox.** It answers in two places,
both measured on one AC22E-01: as unit **3** behind a WiNet-S, and as unit
**248** at its own LAN address, inside TLS on port 516 with no port 502 at
all. Never through the inverter's own LAN port.

So discovery asks the endpoints it already has, rather than sweeping for
another one -- the same shape the SBR takes, and the reason one config entry
is one endpoint plus whatever answers behind it. The wallbox's own address is
an option on that entry (`wallbox_host`), probed at unit 248 over TLS alone.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..addresses import field_address, read

#: Unit ids a wallbox may answer on, in the order to try them.
#:
#: Behind a plain Modbus TCP endpoint. 3 first: a WiNet-S forwards the
#: wallbox there. 248 second, for an RS485-to-TCP adapter wired straight to
#: the wallbox -- reported by others, not measured here. The wallbox's own
#: address over TLS is probed at 248 alone, by its caller.
UNITS: tuple[int, ...] = (3, 248)

#: The register read to decide whether a wallbox is there, and its length.
#:
#: The model *name*, as ASCII across five registers, rather than the device
#: type code next to it. Two reasons, both from measurement. A name is
#: self-validating -- `AC22E-01` is a wallbox and no amount of coincidence
#: makes an inverter answer that -- where a bare code has to be looked up
#: against a table with three entries in it, and a device answering a code
#: outside the table would be dismissed. And the serial sits just below
#: it, at protocol address 21200, so probing the name rather than the serial keeps a
#: serial out of a capability probe entirely.
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

    An answer is not enough; it has to be a **name**. Any successful read is
    satisfied by a device answering zeros, which is precisely what a dongle
    in the path does for a unit it does not forward. So the words have to
    decode to printable text, because that is what a model name is.
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
    return _printable(words)


def _printable(words: list[int]) -> str | None:
    """Decode words as printable ASCII, or None where they are not text."""
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
