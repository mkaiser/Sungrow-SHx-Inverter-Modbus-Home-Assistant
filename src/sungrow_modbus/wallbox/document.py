"""What a wallbox puts into a published document.

Its readings, decoded from a dump with each register's confidence mark, and
its serial -- only ever as a stand-in, from the words `WALLBOX_MASKED`
removes from the published dump.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from ..dump import WALLBOX_MASKED
from .discovery import _printable
from .registers import CODES, COMPONENTS, CONFIDENCE, LOCAL_CLOCK, MODELS

#: Where the serial is: the one band `WALLBOX_MASKED` names.
SERIAL_SPACE, SERIAL_START, SERIAL_COUNT = WALLBOX_MASKED[0]


def serial_stand_in(dump: Mapping[str, Any]) -> str | None:
    """Return the wallbox's stand-in serial from an **unmasked** dump, or None.

    The same treatment as the inverter's serial: the words are masked out of
    the published dump, and the document carries `stand_in(serial)` in their
    place, so one wallbox is recognisable across readings without its serial
    leaving the house. None where any word is missing or the words are not
    text -- a stand-in hashed from garbage would claim an identity nobody has.
    """
    values = dump.get(SERIAL_SPACE) or {}
    found = [values.get(str(SERIAL_START + i)) for i in range(SERIAL_COUNT)]
    words = [int(word) for word in found if word is not None]
    if len(words) != SERIAL_COUNT:
        return None
    serial = _printable(words)
    # Imported here: `fingerprint` reads the battery package, whose
    # addresses load every device's registers, this package's among them.
    from ..fingerprint import stand_in

    return stand_in(serial) if serial else None


async def async_serial_stand_in(
    read_words: Callable[[str, int, int], Any],
) -> str | None:
    """Read the serial and return only its stand-in, or None.

    For a caller that has no dump: `read_words(space, address, count)` is the
    seam a device offers. The real serial lives only inside this function.
    """
    from modbus_connection import ModbusError

    try:
        words = await read_words(SERIAL_SPACE, SERIAL_START, SERIAL_COUNT)
    except (ModbusError, TimeoutError, OSError):
        return None
    if not words:
        return None
    dump = {SERIAL_SPACE: {str(SERIAL_START + i): w for i, w in enumerate(words)}}
    return serial_stand_in(dump)


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
