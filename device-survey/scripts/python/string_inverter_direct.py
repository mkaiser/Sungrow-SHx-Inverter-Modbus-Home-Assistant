"""A Sungrow SG string inverter: read it, write its document.

Found by `probe.identify`, which names an SG by its type code at input 5000
(`string_inverter.MODELS`). An SG answers the identity block and the PV
registers a hybrid does, and none of the hybrid map past 5035, so it is read
by its own map: `dump.SG_BANDS` raw, beside the readings
`string_inverter.readings` decodes from them. No SG has been surveyed, so the
words are the evidence and the readings only the map's reading of them.

Two things the document imposes:

- **The serial never leaves the transcript.** Its ten words are read, the
  stand-in is hashed from them, and the dump is masked before anything else
  sees it (`string_inverter.mask`).
- **Nothing writes.** No control test, no hybrid block test: both write or
  read the hybrid map, and an SG's holding registers mean other things.

Read-only, like everything in this folder: function codes 3 and 4.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, NamedTuple

from ihomemanager_direct import _destination
from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from sungrow_modbus import dump as register_dump, string_inverter
from sungrow_modbus.survey import word_reader


class Found(NamedTuple):
    """An SG that answered, where, on which unit, and its model."""

    host: str
    port: int
    unit: int
    model: str


class Reading(NamedTuple):
    """What one survey of an SG produced."""

    document: dict[str, Any]
    written: Path | None
    code: int


async def async_survey(
    found: Found,
    answers: Any,
    directory: Path,
    echo,
    *,
    address_tail: str,
) -> Reading:
    """Read the SG whole, and write its document into `directory`.

    `answers` carries the reporter, the comment and the timeout;
    `address_tail` is the published address, already decided by consent.
    """
    read_at = datetime.now(UTC).isoformat(timespec="seconds")
    connection = ModbusConnection(
        ModbusTcpParams(host=found.host, port=found.port), timeout=answers.timeout
    )
    bands = string_inverter.BANDS
    total = register_dump.block_count(bands)
    try:

        def on_block(done: int, _total: int, why: str) -> None:
            echo(f"  {done:>2} of {total}  {why}")

        raw = await register_dump.async_dump(
            word_reader(connection.for_unit(found.unit)),
            on_progress=on_block,
            bands=bands,
        )
    finally:
        await connection.close()

    serial = string_inverter.serial(raw)
    firmware = string_inverter.firmware(raw)
    dump = string_inverter.mask(raw)
    del raw
    section = string_inverter.section(dump, unit=found.unit)
    document = string_inverter.document(
        command_line=getattr(answers, "command_line", None)
        or "sungrow_survey.py <host>",
        read_at=read_at,
        user_inputs={
            "reporter": getattr(answers, "reporter", ""),
            "comment": getattr(answers, "comment", ""),
        },
        address_tail=address_tail,
        device=string_inverter.device_block(dump, serial),
        firmware=firmware,
        connection={"protocol": "Modbus TCP", "port": found.port, "unit": found.unit},
        string_inverter=section,
    )
    if not register_dump.answered(section["register_dump"]):
        # Nothing read: the link, not the device. Not written, and exit 1.
        return Reading(document, None, 1)
    directory.mkdir(parents=True, exist_ok=True)
    path = _destination(directory, string_inverter.label_for(document), address_tail)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return Reading(document, path, 0)
