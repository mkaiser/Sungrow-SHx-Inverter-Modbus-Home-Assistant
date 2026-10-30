"""What a Logger puts into a published document.

Its identity decoded, and every other word raw. Most of a Logger is
undocumented here, so the text guard of `ihomemanager.masked_text` runs over
all of it: any text outside the protocol number is masked and published as a
stand-in, because a Logger's serial, if it has one in these bands, would
otherwise be published as words.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..ihomemanager.document import masked_text, readings as decoded
from .registers import COMPONENTS, CONFIDENCE, MODELS, UNIT

#: The `document` key of a Logger document.
LOGGER_DOCUMENT = "logger"


def readings(dump: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Decode the identity block, naming the model from the type code."""
    out = decoded(dump, COMPONENTS, CONFIDENCE, {})
    if (code := out.get("device_type_code")) is not None:
        model = MODELS.get(int(str(code["value"]), 16))
        if model is not None:
            code["model"] = model
    return out


def section(raw_dump: Mapping[str, Any], *, port: int) -> dict[str, Any]:
    """Return the `logger` section from an **unmasked** dump."""
    masked, records = masked_text(raw_dump, COMPONENTS)
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
    logger: Mapping[str, object],
) -> dict[str, object]:
    """Build the document for a Logger, from an already masked section."""
    from ..survey_document import SCHEMA

    return {
        "schema": SCHEMA,
        "document": LOGGER_DOCUMENT,
        "command_line": command_line,
        "read_at": read_at,
        "user_inputs": {key: value for key, value in user_inputs.items() if value},
        "ip_address_last_two_octets": address_tail,
        "connection": dict(connection),
        "logger": dict(logger),
    }


def label_for(document: Mapping[str, Any]) -> str:
    """Name a document: model, who read it, which port."""
    section_ = document.get("logger") or {}
    code = (section_.get("readings") or {}).get("device_type_code") or {}
    model = str(code.get("model") or "logger").lower()
    reporter = str((document.get("user_inputs") or {}).get("reporter") or "")
    slug = "".join(c if c.isalnum() else "-" for c in reporter.lower()).strip("-")
    parts = [model, slug]
    if port := section_.get("port"):
        parts.append(f"port{port}")
    return "-".join(part for part in parts if part)
