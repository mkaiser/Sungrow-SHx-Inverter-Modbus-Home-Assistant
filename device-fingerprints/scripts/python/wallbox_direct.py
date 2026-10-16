"""A Sungrow wallbox at its own address: find it, read it, write its document.

Measured on an AC22E-01: a wallbox with a network connection of its own
serves Modbus TCP **inside TLS on port 516**, answers only as **unit 248**,
and has no port 502 at all -- so a sweep for 502 never sees it, and before
this module the survey reported its 516 as "found, not readable". Through a
WiNet-S the same wallbox answers as unit 3, and that path stays what
`probe.py` reads behind an inverter's dongle.

Two rules the direct path imposes, both measured:

- **A read must start on a data point's first register**, or it times out.
  So the raw bands are `dump.WALLBOX_TLS_BANDS`, cut at measured starts,
  never the dongle's `WALLBOX_BANDS`.
- **The certificate is Sungrow's own**, signed by `OT.SUNGROW` and
  byte-identical on a WiNet-S and a wallbox at one house, so it is not
  verified: there is nothing to verify it against.

Read-only, like everything in this folder: function codes 3 and 4.

The document is a **wallbox document**, not an inverter's: it has no
`device` section, and its own filename. It is published in
`device-fingerprints/` beside the inverter documents; the corpus checks
tell the two apart by `"document": "wallbox"`, not by folder.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, NamedTuple

from modbus_connection import ModbusError, ModbusTlsParams
from modbus_connection.tmodbus import ModbusConnection

from sungrow_modbus import dump as register_dump, wallbox as wallbox_reader
from sungrow_modbus.addresses import read
from sungrow_modbus.fingerprint import (
    wallbox_document,
    wallbox_label_for as label_for,
    wallbox_section,
)
from sungrow_modbus.survey import word_reader

#: Where a wallbox answers at its own address. Constants, because they are
#: the only values measured.
PORT = 516
UNIT = 248


class Found(NamedTuple):
    """A wallbox that answered at its own address, and its model."""

    host: str
    model: str


class Reading(NamedTuple):
    """What one survey of a wallbox produced."""

    document: dict[str, Any]
    written: Path | None
    code: int


def params(host: str) -> ModbusTlsParams:
    """Return the link to a wallbox's own address: Modbus inside TLS, unverified."""
    return ModbusTlsParams(host=host, port=PORT, verify=False, check_hostname=False)


async def async_identify(host: str, timeout: float = 6.0) -> Found | None:
    """Return the wallbox answering at this address over TLS, or None.

    The model *name*, never the serial two registers below it -- the same
    probe the integration and `probe.py` use. A host whose 516 is a WiNet-S
    answers nothing at unit 248, and comes back None.
    """
    connection = ModbusConnection(params(host), timeout=timeout)
    try:
        unit = connection.for_unit(UNIT)
        if await wallbox_reader.probe_units(lambda _unit_id: unit, (UNIT,)) is None:
            return None
        words = await read(unit, wallbox_reader.MODEL_NAME)
        model = wallbox_reader.model_name(words)
    except (ModbusError, TimeoutError, OSError):
        return None
    finally:
        await connection.close()
    return Found(host, model) if model else None


async def async_survey(
    found: Found,
    answers: Any,
    directory: Path,
    echo,
    *,
    address_tail: str,
    local_time,
) -> Reading:
    """Read the wallbox whole, and write its document beside the script.

    `answers` carries what was asked -- reporter, comment, and the timeout;
    `address_tail` is the published address, already decided by consent;
    `local_time` renders the UTC stamp the way inverter documents do.
    """
    read_at = datetime.now(UTC).isoformat(timespec="seconds")
    connection = ModbusConnection(params(found.host), timeout=answers.timeout)
    try:
        read_words = word_reader(connection.for_unit(UNIT))
        stand_in = await wallbox_reader.async_serial_stand_in(read_words)
        total = register_dump.block_count(register_dump.WALLBOX_TLS_BANDS)

        def on_block(done: int, _total: int, why: str) -> None:
            echo(f"  {done:>2} of {total}  {why}")

        raw = await register_dump.async_dump(
            read_words,
            on_progress=on_block,
            bands=register_dump.WALLBOX_TLS_BANDS,
        )
    finally:
        await connection.close()

    masked = register_dump.masked(raw, register_dump.WALLBOX_MASKED)
    section = wallbox_section(
        UNIT,
        readings=wallbox_reader.readings(masked),
        serial_stand_in=stand_in,
        path="tls",
        register_dump=masked,
    )
    document = wallbox_document(
        command_line=getattr(answers, "command_line", None)
        or "sungrow_survey.py <host>",
        read_at=read_at,
        user_inputs={
            "reporter": getattr(answers, "reporter", ""),
            "comment": getattr(answers, "comment", ""),
        },
        address_tail=address_tail,
        connection={"protocol": "Modbus TCP inside TLS", "port": PORT},
        wallbox=section,
    )
    answered = register_dump.answered(masked)
    if not answered:
        # Nothing read: the link, not the wallbox. Not written, and exit 1.
        return Reading(document, None, 1)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{label_for(document)}.json"
    path.write_text(json.dumps(document, indent=2) + "\n")
    return Reading(document, path, 0)
