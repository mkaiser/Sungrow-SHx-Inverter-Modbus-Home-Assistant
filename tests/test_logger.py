"""A Sungrow Logger: found at unit 247, read raw, its text masked.

No Logger has been read anywhere and Sungrow's document is not read here, so
the fixture is the identity block two community maps agree on, typed by hand.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus import logger
from sungrow_modbus.dump import LOGGER_BANDS

SURVEY = Path(__file__).resolve().parents[1] / "device-survey" / "scripts" / "python"
sys.path.insert(0, str(SURVEY))

import ihomemanager_direct  # noqa: E402
import sungrow_survey  # noqa: E402

from .corpus import LOGGER_DOCUMENTS  # noqa: E402

#: The placeholder serial, as words, planted in an undocumented register.
SERIAL_WORDS = [0x4131, 0x3233, 0x3435, 0x3637, 0x3839]

SEED = Path(__file__).resolve().parents[1] / "scripts" / "dev" / "simulator_logger.json"


def _device() -> dict[str, dict[int, int]]:
    """Return a Logger1000's identity block, and text where a serial could be."""
    inputs = {7999: 0x0710, 8000: 0x4157, 8001: 0x3000, 8002: 0x0200, 8003: 0x0100}
    inputs.update({8004: 4, 8005: 1})
    inputs.update({8020 + i: word for i, word in enumerate(SERIAL_WORDS)})
    for space, start, count, _why in LOGGER_BANDS:
        if space == "input":
            for address in range(start, start + count):
                inputs.setdefault(address, 0)
    holding = dict.fromkeys(range(7999, 8199), 0)
    return {"input": inputs, "holding": holding}


def _dump(device):
    return {
        space: {str(a): w for a, w in words.items()} for space, words in device.items()
    }


def test_the_identity_names_the_model() -> None:
    section = logger.section(_dump(_device()), port=502)
    readings = section["readings"]

    assert readings["device_type_code"]["value"] == "0x0710"
    assert readings["device_type_code"]["model"] == "Logger1000"
    assert readings["protocol_number"]["value"] == "AW0"
    assert readings["protocol_version"]["value"] == "V1.0.2"
    assert readings["connected_devices"]["value"] == 4
    assert readings["devices_in_fault"]["value"] == 1
    assert {entry["held"] for entry in readings.values()} == {"named elsewhere"}


def test_text_outside_the_identity_is_masked() -> None:
    section = logger.section(_dump(_device()), port=502)

    words = section["register_dump"]["input"]
    assert [words[str(8020 + i)] for i in range(5)] == [None] * 5
    assert [record["register"] for record in section["masked_text"]] == [8021]
    assert "A123456789" not in json.dumps(section)


def _connection(device):
    class Unit:
        def __init__(self) -> None:
            self.mock = MockModbusConnection().for_unit(247)

        async def _read(self, table, address, count):
            if any(a not in table for a in range(address, address + count)):
                raise IllegalDataAddressError("illegal data address")
            return [table[a] for a in range(address, address + count)]

        async def read_input_registers(self, address, count):
            return await self._read(device["input"], address, count)

        async def read_holding_registers(self, address, count):
            return await self._read(device["holding"], address, count)

    class Connection:
        def __init__(self, params, timeout):
            self.unit = Unit()

        def for_unit(self, unit_id):
            assert unit_id == 247
            return self.unit

        async def close(self):
            pass

    return Connection


async def _no_sleep(_seconds):
    return None


async def test_a_logger_survey_writes_a_logger_document(tmp_path) -> None:
    found = ihomemanager_direct.Found("192.0.2.60", 502, "a Logger1000", "logger")
    answers = SimpleNamespace(timeout=1, reporter="tester", comment="")
    with (
        patch.object(ihomemanager_direct, "ModbusConnection", _connection(_device())),
        patch("sungrow_modbus.dump.asyncio.sleep", _no_sleep),
    ):
        reading = await ihomemanager_direct.async_survey(
            found, answers, tmp_path, lambda _text: None, address_tail="000.060"
        )

    assert reading.code == 0
    document = reading.document
    assert document["document"] == "logger"
    assert "ihomemanager" not in document
    assert reading.written.name == "logger1000-tester-port502.json"
    assert "A123456789" not in reading.written.read_text()


async def test_a_logger_behind_an_inverter_is_found_when_the_owner_says_so() -> None:
    """`identify` stops at the inverter; unit 247 is asked only on that answer."""
    sungrow_survey._MANAGERS.clear()
    found = sungrow_survey.Found("192.0.2.61", 502, 1, None)
    outcome = sungrow_survey.Outcome(
        found=found,
        unit=1,
        document={},
        written=[],
        transport=None,
        reported_transport="logger",
        block_outcome=None,
        code=0,
    )
    asked: list[tuple[str, int]] = []

    async def identify_247(host, port):
        asked.append((host, port))
        return SimpleNamespace(kind="logger", model="a Logger1000", unit=247)

    with (
        patch.object(sungrow_survey, "async_identify_unit_247", identify_247),
        patch.object(sungrow_survey.probe, "described", lambda who: who.model),
    ):
        await sungrow_survey._find_loggers_behind([outcome], lambda *_a: None)
        not_said = outcome._replace(reported_transport="winet_lan")
        await sungrow_survey._find_loggers_behind([not_said], lambda *_a: None)

    assert asked == [("192.0.2.61", 502)]
    assert [
        ihomemanager_direct.Found("192.0.2.61", 502, "a Logger1000", "logger")
    ] == sungrow_survey._MANAGERS
    sungrow_survey._MANAGERS.clear()


def test_the_simulator_seed_decodes_as_a_logger() -> None:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    dump: dict[str, dict[str, int]] = {"input": {}, "holding": {}}
    for space in ("input", "holding"):
        for start, words in seed[space].items():
            for offset, word in enumerate(words):
                dump[space][str(int(start) + offset)] = word
    section = logger.section(dump, port=5022)

    assert section["readings"]["device_type_code"]["model"] == "Logger1000"
    assert [record["register"] for record in section["masked_text"]] == [8021]


@pytest.mark.parametrize("path", LOGGER_DOCUMENTS, ids=lambda p: p.stem)
def test_a_committed_logger_document_hides_its_text(path) -> None:
    """Held to every committed reading, once there is one."""
    document = json.loads(path.read_text(encoding="utf-8"))
    label = logger.label_for(document)
    assert path.stem == label or path.stem.startswith(f"{label}-")
    published = document["logger"]["register_dump"]
    assert (
        logger.section(published, port=document["logger"]["port"])["masked_text"] == []
    )
