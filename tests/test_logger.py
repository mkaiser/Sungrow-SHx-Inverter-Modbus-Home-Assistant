"""A Sungrow Logger: found at unit 247, decoded from Sungrow's document.

No Logger has been measured here, so the fixture is typed by hand from the
*Logger Communication Protocol* 1.0.2.9 (`.wiki/raw/logger-communication-protocol.md`).
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
    inputs.update({8039 + i: word for i, word in enumerate(SERIAL_WORDS)})
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
    identity = logger.COMPONENTS["identity"].declared_fields
    held = {readings[name.removesuffix("_raw")]["held"] for name in identity}
    assert held == {"spec 1.0.2.5-1.0.2.9"}
    assert readings["wifi_hotspot"]["held"] == "spec 1.0.2.9"


def test_text_outside_the_identity_is_masked() -> None:
    section = logger.section(_dump(_device()), port=502)

    words = section["register_dump"]["input"]
    assert [words[str(8039 + i)] for i in range(5)] == [None] * 5
    assert [record["register"] for record in section["masked_text"]] == [8040]
    assert "A123456789" not in json.dumps(section)


def _decode(input_words=None, holding_words=None):
    """Decode words given by register number, nothing else answered."""
    dump = {
        "input": {str(r - 1): w for r, w in (input_words or {}).items()},
        "holding": {str(r - 1): w for r, w in (holding_words or {}).items()},
    }
    return logger.readings(dump)


def test_a_32_bit_value_sends_its_low_word_first() -> None:
    """The document's own example: 0x0000015E is sent 01 5E 00 00."""
    readings = _decode(holding_words={8005: 0x015E, 8006: 0x0000})

    assert readings["active_power_ratio_setting"]["value"] == pytest.approx(35.0)
    assert readings["active_power_ratio_setting"]["unit"] == "%"


def test_a_64_bit_value_sends_its_high_word_first() -> None:
    readings = _decode(
        {
            8070: 0, 8071: 0, 8072: 0x0001, 8073: 0x86A0,
            8080: 0, 8081: 0, 8082: 0, 8083: 12345,
            8076: 0xFFFF, 8077: 0xFFFF, 8078: 0xFFFF, 8079: 0xFF38,
        }
    )  # fmt: skip

    assert readings["total_active_power"]["value"] == 100000
    assert readings["total_yield"]["value"] == pytest.approx(1234.5)
    assert readings["total_reactive_power"]["value"] == -200


def test_an_unsupported_register_is_absent_not_a_number() -> None:
    """All ones unsigned, the largest positive signed: the document's blanks."""
    readings = _decode(
        {
            8027: 0x7FFF,
            8058: 0xFFFF,
            8074: 0xFFFF, 8075: 0xFFFF,
            8070: 0xFFFF, 8071: 0xFFFF, 8072: 0xFFFF, 8073: 0xFFFF,
            8076: 0x7FFF, 8077: 0xFFFF, 8078: 0xFFFF, 8079: 0xFFFF,
        }
    )  # fmt: skip

    assert readings == {}


@pytest.mark.parametrize(
    ("space", "register", "word", "field", "means"),
    [
        ("input", 8068, 1, "array_switch", "on"),
        ("input", 8069, 0, "unlatch_state", "latched"),
        ("holding", 8017, 0xAA, "power_gradient_control", "enabled"),
        ("holding", 8020, 0x55, "wifi_hotspot", "disabled"),
        ("holding", 8013, 1, "digital_output_1", "common to NO closed"),
    ],
)
def test_the_codes_become_words(space, register, word, field, means) -> None:
    readings = (
        _decode({register: word})
        if space == "input"
        else _decode(holding_words={register: word})
    )

    assert readings[field]["value"] == word
    assert readings[field]["means"] == means


def test_the_scaled_inputs_carry_the_documents_scale() -> None:
    readings = _decode({8027: 0xFF9C, 8029: 1000, 8030: 2000})

    assert readings["pt100_1_temperature"]["value"] == pytest.approx(-10.0)
    assert readings["ai1_voltage"]["value"] == pytest.approx(10.0)
    assert readings["ai1_current"]["value"] == pytest.approx(20.0)


def test_every_documented_field_is_inside_a_band() -> None:
    read: dict[str, set[int]] = {"input": set(), "holding": set()}
    for space, start, count, _why in LOGGER_BANDS:
        read[space].update(range(start, start + count))
    for component in logger.COMPONENTS.values():
        for name, field in component.declared_fields.items():
            needed = set(range(field.address, field.address + field.count))
            assert needed <= read[component.register_space], name


def test_the_documented_bands_come_before_the_gaps() -> None:
    """A survey that runs out of time still has every documented register."""
    kinds = [why.startswith("undocumented") for *_rest, why in LOGGER_BANDS]
    assert kinds == sorted(kinds)


def test_every_field_has_a_source() -> None:
    for component in logger.COMPONENTS.values():
        for name in component.declared_fields:
            assert name.removesuffix("_raw") in logger.CONFIDENCE


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

    readings = section["readings"]
    assert readings["device_type_code"]["model"] == "Logger1000"
    assert readings["total_active_power"]["value"] == 86500
    assert readings["array_switch"]["means"] == "on"
    assert [record["register"] for record in section["masked_text"]] == [8040]


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
