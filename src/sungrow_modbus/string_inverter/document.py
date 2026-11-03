"""What an SG string inverter puts into a published document.

A document of its own kind (`"document": "string_inverter"`), as a wallbox's
and an iHomeManager's are: the inverter documents in `device-survey/results/`
are read as hybrids by everything that reads them, and an SG answers none of
the hybrid map past 5035.

The serial is handled as on a hybrid: its ten words are masked out of the dump
(`dump.DUMP_MASKED`), and the document carries only `serial_anonymized_hashed`.
The map is unmeasured, so the dump is the evidence and the readings are the
map's reading of it; a field answering the protocol's "unavailable" is absent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..dump import DUMP_MASKED, masked
from ..model import words_text
from .registers import COMPONENTS, MODELS, SWITCH, WORK_STATES

#: The `document` key of an SG document.
STRING_INVERTER_DOCUMENT = "string_inverter"

#: Where every address in `registers` comes from, said once per document.
SOURCE = (
    "ha-modbus-manager sungrow_sg_dynamic.yaml (MIT, commit 4a1e662), from "
    "Sungrow's Communication Protocol of Residential and Commercial PV "
    "Grid-Connected Inverters V1.1.53; unmeasured"
)

#: The codes a reading publishes with their meaning beside the number.
CODES: dict[str, Mapping[int, str]] = {
    "work_state": WORK_STATES,
    "power_limitation": SWITCH,
}

#: What input 5002 says.
OUTPUT_TYPES: dict[int, str] = {
    0: "single phase",
    1: "three phase 3P4L",
    2: "three phase 3P3L",
}

#: The serial's words, protocol addresses.
SERIAL_START = 4989
SERIAL_COUNT = 10

#: The ARM and DSP software versions, input 4954 and 4969, 15 words each.
FIRMWARE: dict[str, int] = {"arm": 4953, "dsp": 4968}
FIRMWARE_COUNT = 15


def readings(dump: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Decode an SG's words into named readings, from the **masked** dump.

    The shape a wallbox's and an iHomeManager's readings take: each keeps its
    register number, a code its meaning. A field with any word missing, or
    answering the protocol's "unavailable", is absent rather than zero.
    """
    out: dict[str, dict[str, Any]] = {}
    for component in COMPONENTS.values():
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
            entry: dict[str, Any] = {"register": field.address + 1}
            if published == "device_type_code":
                entry["value"] = f"0x{int(value):04X}"
            elif published in CODES:
                entry["value"] = int(value)
                entry["means"] = CODES[published].get(int(value), "unknown code")
            else:
                entry["value"] = value
            if unit := getattr(field, "unit", None):
                entry["unit"] = unit
            out[published] = entry
    return out


def serial_words(dump: Mapping[str, Any]) -> list[int] | None:
    """Return the serial's words from an **unmasked** dump, or None."""
    values = dump.get("input")
    if not isinstance(values, Mapping):
        return None
    words = [values.get(str(SERIAL_START + i)) for i in range(SERIAL_COUNT)]
    if any(word is None for word in words):
        return None
    return [int(word) for word in words if word is not None]


def serial(dump: Mapping[str, Any]) -> str | None:
    """Return the serial as text from an **unmasked** dump, or None."""
    words = serial_words(dump)
    return (words_text(words).strip() or None) if words else None


def firmware(dump: Mapping[str, Any]) -> dict[str, str | None]:
    """Return the ARM and DSP versions the dump read; None where one did not.

    From the dump, not from reads of their own: the first band covers both.
    """
    values = dump.get("input")
    out: dict[str, str | None] = {}
    for name, start in FIRMWARE.items():
        found = (
            [values.get(str(start + i)) for i in range(FIRMWARE_COUNT)]
            if isinstance(values, Mapping)
            else []
        )
        words = [int(word) for word in found if word is not None]
        text = words_text(words).strip() if len(words) == FIRMWARE_COUNT else ""
        out[name] = text or None
    return out


def mask(dump: Mapping[str, Any]) -> dict[str, Any]:
    """Return the dump with the serial's words blanked, as on a hybrid."""
    return masked(dict(dump), DUMP_MASKED)


def device_block(dump: Mapping[str, Any], serial: str | None) -> dict[str, Any]:
    """Return what the inverter is: code, model, phases, stand-in serial."""
    from ..survey_document import stand_in

    values = dump.get("input") if isinstance(dump.get("input"), Mapping) else {}
    code = values.get("4999") if isinstance(values, Mapping) else None
    phases = values.get("5001") if isinstance(values, Mapping) else None
    return {
        "device_type_code": None if code is None else f"0x{int(code):04X}",
        "device_type": None if code is None else MODELS.get(int(code)),
        "output_type": None if phases is None else OUTPUT_TYPES.get(int(phases)),
        "serial_anonymized_hashed": stand_in(serial) if serial else None,
    }


def section(masked_dump: Mapping[str, Any], *, unit: int) -> dict[str, Any]:
    """Return the `string_inverter` section from an already masked dump."""
    return {
        "unit": unit,
        "map": SOURCE,
        "readings": readings(masked_dump),
        "register_dump": dict(masked_dump),
    }


def document(
    *,
    command_line: str,
    read_at: str,
    user_inputs: Mapping[str, object],
    address_tail: str,
    device: Mapping[str, object],
    firmware: Mapping[str, object],
    connection: Mapping[str, object],
    string_inverter: Mapping[str, object],
) -> dict[str, object]:
    """Build the document for an SG, from an already masked section."""
    from ..survey_document import SCHEMA

    return {
        "schema": SCHEMA,
        "document": STRING_INVERTER_DOCUMENT,
        "command_line": command_line,
        "read_at": read_at,
        "user_inputs": {key: value for key, value in user_inputs.items() if value},
        "ip_address_last_two_octets": address_tail,
        "device": dict(device),
        "firmware": dict(firmware),
        "connection": dict(connection),
        "string_inverter": dict(string_inverter),
    }


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def label_for(document: Mapping[str, Any]) -> str:
    """Name a document: model, phases, who read it, the stand-in serial.

    In the order an inverter's label uses, so one machine's documents share a
    prefix. No firmware word: an SG's firmware block is not known to answer.
    """
    device = document.get("device") or {}
    model = str(device.get("device_type") or device.get("device_type_code") or "sg")
    phases = "1p" if device.get("output_type") == "single phase" else "3p"
    if device.get("output_type") is None:
        phases = ""
    reporter = str((document.get("user_inputs") or {}).get("reporter") or "anonymous")
    stand_in = str(device.get("serial_anonymized_hashed") or "")
    parts = [_slug(model), phases, _slug(reporter), stand_in]
    return "-".join(part for part in parts if part)
