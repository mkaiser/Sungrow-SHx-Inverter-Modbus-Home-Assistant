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
IDENTITY_REGISTER = 21215
IDENTITY_LENGTH = 5

#: Words that mean "nothing here", whatever they decode to.
#:
#: `0xFFFF` is the specification's unavailable marker, and `0` is what a
#: WiNet-S answers for a measuring point it does not forward -- which is not
#: the same thing and has invented capabilities before. A wallbox that is
#: absent behind a dongle is one of the two, and neither is a model name.
IMPLAUSIBLE = (0, 0xFFFF)


async def probe_units(unit_for, units: tuple[int, ...] = UNITS) -> int | None:
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
            words = await unit_for(unit).read_input_registers(
                IDENTITY_REGISTER, IDENTITY_LENGTH
            )
        except (ModbusError, TimeoutError, OSError):
            continue
        if not words or all(int(word) in IMPLAUSIBLE for word in words):
            continue
        if model_name(words):
            return unit
    return None


def model_name(words) -> str | None:
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
