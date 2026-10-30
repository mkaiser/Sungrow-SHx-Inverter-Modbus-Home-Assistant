"""What an iHomeManager puts into a published document.

**It has no documented serial**, so there is no fixed mask as the inverter
and the wallbox have. What it may still have is an undocumented one: the
survey reads the gaps between documented registers, because that is where
anything Sungrow left out would be. So any **text** in a gap is treated as a
serial until somebody shows otherwise: masked out of the dump, and recorded
only as where it was, how long, and a stand-in. A stand-in for text that
turns out to be a part number costs nothing; publishing a serial costs the
owner, and it cannot be taken back.
"""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from modbus_connection.model import Component

from .registers import CODES, COMPONENTS, CONFIDENCE, UNIT, protocol_version

#: The `document` key of an iHomeManager document. Inverter documents carry
#: no `document` key and a wallbox's says `wallbox`.
IHOMEMANAGER_DOCUMENT = "ihomemanager"

#: The shortest text worth masking, in words: three words is six
#: characters, shorter than any Sungrow serial.
MIN_TEXT_WORDS = 3

#: And the fewest letters and digits in it, so a run of spaces and
#: punctuation is not called text.
MIN_ALNUM = 4


#: A device's components, by name: what `masked_text` leaves alone and
#: `readings` decodes. The iHomeManager's by default; a Logger passes its own.
Components = Mapping[str, type[Component]]


def _declared(components: Components) -> dict[str, set[int]]:
    """Every address a documented field reads, by space."""
    out: dict[str, set[int]] = {}
    for component in components.values():
        space = out.setdefault(component.register_space, set())
        for field in component.declared_fields.values():
            space.update(range(field.address, field.address + field.count))
    return out


def _texty(word: int) -> bool:
    """Whether a word could be two characters of text, or text's padding."""
    return all(byte == 0 or 0x20 <= byte < 0x7F for byte in word.to_bytes(2, "big"))


def _text(words: list[int]) -> str:
    return b"".join(w.to_bytes(2, "big") for w in words).decode("ascii").strip("\x00")


def _runs(values: Mapping[str, Any], skip: set[int]) -> list[tuple[int, list[int]]]:
    """Consecutive answered, text-shaped words outside `skip`, as (start, words)."""
    runs: list[tuple[int, list[int]]] = []
    start: int | None = None
    words: list[int] = []
    for address in sorted(int(key) for key in values if key.isdigit()):
        word = values[str(address)]
        joins = start is not None and address == start + len(words)
        if address in skip or word is None or not _texty(int(word)) or int(word) == 0:
            if start is not None:
                runs.append((start, words))
            start, words = None, []
            continue
        if not joins:
            if start is not None:
                runs.append((start, words))
            start, words = address, []
        words.append(int(word))
    if start is not None:
        runs.append((start, words))
    return runs


def masked_text(
    dump: Mapping[str, Any],
    components: Components = COMPONENTS,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return the dump with gap text blanked, and a record of each blank.

    Only addresses no documented field reads are looked at, so a reading is
    never lost to this; the documented strings (protocol number, software
    version) are fields and published as they are. A run is masked when it
    is at least `MIN_TEXT_WORDS` words of printable ASCII, NUL-padded, with
    `MIN_ALNUM` letters or digits in it. Each record carries the register
    number, the count and `stand_in` of the text -- never the words.
    """
    # Imported here: `survey_document` reads the battery package, whose
    # addresses load every device's registers.
    from ..survey_document import stand_in

    declared = _declared(components)
    out: dict[str, Any] = {
        space: dict(values) if isinstance(values, Mapping) else values
        for space, values in dump.items()
    }
    records: list[dict[str, Any]] = []
    for space, values in out.items():
        if not isinstance(values, dict):
            continue
        for start, words in _runs(values, declared.get(space, set())):
            text = _text(words)
            alnum = len(re.findall(r"[A-Za-z0-9]", text))
            if len(words) < MIN_TEXT_WORDS or alnum < MIN_ALNUM:
                continue
            for address in range(start, start + len(words)):
                values[str(address)] = None
            records.append(
                {
                    "space": space,
                    "register": start + 1,
                    "count": len(words),
                    "stand_in": stand_in(text),
                }
            )
    return out, records


def readings(
    dump: Mapping[str, Any],
    components: Components = COMPONENTS,
    confidence: Mapping[str, str] = CONFIDENCE,
    codes: Mapping[str, Mapping[int, str]] = CODES,
) -> dict[str, dict[str, Any]]:
    """Decode an iHomeManager's words into named readings.

    The same shape as a wallbox's: each reading keeps its register number
    and its `held` source, a code what it `means`. A field with any word
    missing, or answering the document's "unavailable", is absent, not zero.
    Run it on the **masked** dump.
    """
    out: dict[str, dict[str, Any]] = {}
    for component in components.values():
        values = dump.get(component.register_space)
        if not isinstance(values, Mapping):
            continue
        for name, field in component.declared_fields.items():
            found = [values.get(str(field.address + i)) for i in range(field.count)]
            words = [int(word) for word in found if word is not None]
            if len(words) < field.count:
                continue
            value = field.decode(words)
            if value is None:
                continue
            published = name.removesuffix("_raw")
            entry: dict[str, Any] = {
                "register": field.address + 1,
                "held": confidence[published],
            }
            if isinstance(value, str):
                if not value.strip():
                    continue
                entry["value"] = value.strip()
            elif published == "device_type_code":
                entry["value"] = f"0x{int(value):04X}"
            elif published == "protocol_version":
                entry["value"] = protocol_version(int(value))
                entry["raw"] = f"0x{int(value):08X}"
            elif published in codes:
                entry["value"] = int(value)
                entry["means"] = codes[published].get(int(value), "unknown code")
            else:
                entry["value"] = value
            if unit := getattr(field, "unit", None):
                entry["unit"] = unit
            out[published] = entry
    return out


def section(raw_dump: Mapping[str, Any], *, port: int) -> dict[str, Any]:
    """Return the `ihomemanager` section from an **unmasked** dump."""
    masked, records = masked_text(raw_dump)
    return {
        "unit": UNIT,
        "port": port,
        "readings": readings(masked),
        "masked_text": records,
        "register_dump": masked,
    }


def document(
    *,
    command_line: str,
    read_at: str,
    user_inputs: Mapping[str, object],
    address_tail: str,
    connection: Mapping[str, object],
    ihomemanager: Mapping[str, object],
) -> dict[str, object]:
    """Build the document for an iHomeManager, from an already masked section."""
    from ..survey_document import SCHEMA

    return {
        "schema": SCHEMA,
        "document": IHOMEMANAGER_DOCUMENT,
        "command_line": command_line,
        "read_at": read_at,
        "user_inputs": {key: value for key, value in user_inputs.items() if value},
        "ip_address_last_two_octets": address_tail,
        "connection": dict(connection),
        "ihomemanager": dict(ihomemanager),
    }


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def label_for(document: Mapping[str, Any]) -> str:
    """Name a document: what it is, its software, who read it, which port.

    In the order an inverter's and a wallbox's label use. There is no
    stand-in serial to carry, because the device documents none.
    """
    section_ = document.get("ihomemanager") or {}
    readings_ = section_.get("readings") or {}
    software = str(
        (readings_.get("application_software_version") or {}).get("value") or ""
    )
    reporter = str((document.get("user_inputs") or {}).get("reporter") or "")
    parts = ["ihomemanager", _slug(software), _slug(reporter)]
    if port := section_.get("port"):
        parts.append(f"port{port}")
    return "-".join(part for part in parts if part)
