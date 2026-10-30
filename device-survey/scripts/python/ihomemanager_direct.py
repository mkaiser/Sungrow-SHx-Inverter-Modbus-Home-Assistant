"""A Sungrow iHomeManager or Logger at unit 247: read it, write its document.

Both answer at unit 247 in the same protocol family, so one reader serves
both, handed the device's package (`sungrow_modbus.ihomemanager` by default,
or `sungrow_modbus.logger`): its bands, its section and its document.

Found by `probe.identify`, which falls back to input 8000 on unit 247 where
no inverter unit answers. Nothing has ever been measured on one, so this
reads every register Sungrow's V1.0.2 document defines and then the gaps
between them, bounded by `dump.BUDGET`, and publishes the words raw beside
the decoded readings: the first reading is the map.

Two things the document imposes:

- **Each port takes one TCP connection.** This holds one for the whole read
  and closes it, so whatever else uses that port is shut out meanwhile.
- **It has no documented serial**, so any text in a gap is masked and
  recorded only as a stand-in (`ihomemanager.masked_text`).

Read-only, like everything in this folder: function codes 3 and 4.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, NamedTuple

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from probe import ADDRESS_HIDDEN

from sungrow_modbus import dump as register_dump, ihomemanager, logger
from sungrow_modbus.survey import word_reader


class Found(NamedTuple):
    """A device at unit 247 that answered, where, and what it called itself."""

    host: str
    port: int
    model: str
    kind: str = "ihomemanager"


#: The library package for each kind `Found` can carry.
PACKAGES: dict[str, Any] = {"ihomemanager": ihomemanager, "logger": logger}


class Reading(NamedTuple):
    """What one survey of an iHomeManager produced."""

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
    """Read the device whole, and write its document into `directory`.

    `answers` carries the reporter, the comment and the timeout;
    `address_tail` is the published address, already decided by consent.
    """
    package = PACKAGES[found.kind]
    read_at = datetime.now(UTC).isoformat(timespec="seconds")
    connection = ModbusConnection(
        ModbusTcpParams(host=found.host, port=found.port), timeout=answers.timeout
    )
    bands = package.BANDS
    total = register_dump.block_count(bands)
    try:

        def on_block(done: int, _total: int, why: str) -> None:
            echo(f"  {done:>2} of {total}  {why}")

        raw = await register_dump.async_dump(
            word_reader(connection.for_unit(package.UNIT)),
            on_progress=on_block,
            bands=bands,
        )
    finally:
        await connection.close()

    section = package.section(raw, port=found.port)
    del raw
    document = package.document(
        command_line=getattr(answers, "command_line", None)
        or "sungrow_survey.py <host>",
        read_at=read_at,
        user_inputs={
            "reporter": getattr(answers, "reporter", ""),
            "comment": getattr(answers, "comment", ""),
        },
        address_tail=address_tail,
        connection={"protocol": "Modbus TCP", "port": found.port},
        **{package.DOCUMENT: section},
    )
    if not register_dump.answered(section["register_dump"]):
        # Nothing read: the link, not the device. Not written, and exit 1.
        return Reading(document, None, 1)
    directory.mkdir(parents=True, exist_ok=True)
    path = _destination(directory, package.label_for(document), address_tail)
    path.write_text(json.dumps(document, indent=2) + "\n")
    return Reading(document, path, 0)


def _destination(directory: Path, label: str, tail: str) -> Path:
    """Overwrite a reading from this address; never one from another.

    The rule the inverter survey follows, smaller: there is no stand-in
    serial to tell two iHomeManagers apart, so the address tail does it, and
    where it was withheld a numbered name is used rather than overwrite.
    """
    first = directory / f"{label}.json"
    known = bool(tail) and tail != ADDRESS_HIDDEN
    candidates = [first]
    if known:
        candidates.append(directory / f"{label}-{tail.replace('.', '-')}.json")
    candidates += [directory / f"{label}-{number}.json" for number in range(2, 20)]
    for path in candidates:
        if not path.exists():
            return path
        try:
            theirs = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if known and theirs.get("ip_address_last_two_octets") == tail:
            return path
    return candidates[-1]
