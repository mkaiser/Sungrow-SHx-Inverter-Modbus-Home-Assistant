"""The iHomeManager: its map, the text it must not publish, and its survey.

No iHomeManager has been read anywhere, so the fixtures are Sungrow's own
document -- the type code, the protocol number and the version example of
*Communication Protocol of iHomeManager* V1.0.2 -- typed here by hand, not
taken from the map under test.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus import ihomemanager
from sungrow_modbus.dump import IHOMEMANAGER_BANDS, block_count
from sungrow_modbus.ihomemanager.registers import TEXT_FIELDS

SURVEY = Path(__file__).resolve().parents[1] / "device-survey" / "scripts" / "python"
sys.path.insert(0, str(SURVEY))

import ihomemanager_direct  # noqa: E402
import probe  # noqa: E402
import sungrow_survey  # noqa: E402

from .corpus import IHOMEMANAGER_DOCUMENTS  # noqa: E402

#: The placeholder serial, as two-character words, planted in a gap.
SERIAL_WORDS = [0x4131, 0x3233, 0x3435, 0x3637, 0x3839]


def _words(text: str) -> list[int]:
    raw = text.encode("ascii")
    raw += b"\x00" * (len(raw) % 2)
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2)]


def _device() -> dict[str, dict[int, int]]:
    """Return an iHomeManager as V1.0.2 describes one, by protocol address."""
    inputs = {
        7999: 0x072A,  # 8000, the type code
        8000: _words("AW0")[0],
        8001: _words("AW0")[1],
        8002: 0x0200,  # 8003-8004: V1.0.2, sent as 0x02000100
        8003: 0x0100,
        8004: 2,  # 8005, two devices connected
        8005: 0,
        8162: 953,  # 8163, battery level 95.3 %
        8160: 0xFFFF,  # 8161-8162, battery power -0.01 kW, low word first
        8161: 0xFFFF,
        8151: 0xFFFF,  # 8152: unavailable
        8553: 1,  # 8554, three phase four wire
    }
    for offset, word in enumerate(_words("IHM_V1.2.3")):
        inputs[8317 + offset] = word
    for offset, word in enumerate(SERIAL_WORDS):
        inputs[8400 + offset] = word
    holding = {8023: 4, 8024: 0xCC}  # 8024 VPP, 8025 stop
    return {"input": inputs, "holding": holding}


def _dump(device: dict[str, dict[int, int]]) -> dict[str, dict[str, int]]:
    """Return what the bands would read: every address, 0 where nothing is set."""
    out: dict[str, dict[str, int]] = {"input": {}, "holding": {}}
    for space, start, count, _why in IHOMEMANAGER_BANDS:
        for address in range(start, start + count):
            out[space][str(address)] = device[space].get(address, 0)
    return out


def test_the_identity_decodes_as_the_document_says() -> None:
    masked, _records = ihomemanager.masked_text(_dump(_device()))
    readings = ihomemanager.readings(masked)

    assert readings["device_type_code"]["value"] == "0x072A"
    assert readings["protocol_number"]["value"] == "AW0"
    assert readings["protocol_version"]["value"] == "V1.0.2"
    assert readings["connected_devices"]["value"] == 2
    assert readings["battery_level"]["value"] == pytest.approx(95.3)
    assert readings["battery_power"]["value"] == pytest.approx(-0.01)
    assert readings["output_type"]["means"] == "three phase, four wire"
    assert readings["ems_mode"]["means"] == "VPP"
    assert readings["charge_command"]["means"] == "stop"
    assert readings["application_software_version"]["value"] == "IHM_V1.2.3"
    assert readings["protocol_version"]["held"] == "spec V1.0.2"
    assert readings["charger_power"]["held"] == "field"


def test_an_unavailable_or_missing_field_is_absent_not_zero() -> None:
    dump = _dump(_device())
    dump["input"]["8175"] = None  # 8176, grid import, half missing
    readings = ihomemanager.readings(ihomemanager.masked_text(dump)[0])

    assert "min_battery_charge_power" not in readings
    assert "grid_import_energy" not in readings


def test_text_in_a_gap_is_masked_and_only_its_stand_in_published() -> None:
    masked, records = ihomemanager.masked_text(_dump(_device()))

    assert [masked["input"][str(8400 + i)] for i in range(5)] == [None] * 5
    assert records == [
        {
            "space": "input",
            "register": 8401,
            "count": 5,
            "stand_in": records[0]["stand_in"],
        }
    ]
    assert records[0]["stand_in"].startswith("anon-")
    assert "A123456789" not in json.dumps([masked, records])


def test_the_documented_strings_are_not_masked() -> None:
    """They are fields, and their text is the reading."""
    masked, records = ihomemanager.masked_text(_dump(_device()))

    assert all(record["register"] not in (8001, 8318) for record in records)
    assert masked["input"]["8317"] is not None
    assert {"protocol_number", "application_software_version"} == TEXT_FIELDS


@pytest.mark.parametrize(
    "words",
    [
        [0x4131, 0x3233],  # two words: shorter than any serial
        [0x2020, 0x2D2D, 0x2020],  # printable, but no letters or digits
        [0x0905, 0x1234, 0x0001],  # numbers
    ],
)
def test_what_is_not_text_is_published(words) -> None:
    dump = _dump({"input": {}, "holding": {}})
    for offset, word in enumerate(words):
        dump["input"][str(8400 + offset)] = word
    masked, records = ihomemanager.masked_text(dump)

    assert records == []
    assert [masked["input"][str(8400 + i)] for i in range(len(words))] == words


def test_every_documented_field_is_inside_a_band() -> None:
    covered = {
        (space, address)
        for space, start, count, _why in IHOMEMANAGER_BANDS
        for address in range(start, start + count)
    }
    for component in ihomemanager.COMPONENTS.values():
        for name, field in component.declared_fields.items():
            for address in range(field.address, field.address + field.count):
                assert (component.register_space, address) in covered, name


def test_the_documented_bands_come_before_the_gaps() -> None:
    """A budget that runs out then costs exploration, never a field."""
    whys = [why for _space, _start, _count, why in IHOMEMANAGER_BANDS]
    first_gap = next(i for i, why in enumerate(whys) if why.startswith("undocumented"))
    assert all(why.startswith("undocumented") for why in whys[first_gap:])
    assert block_count(IHOMEMANAGER_BANDS[:first_gap]) == first_gap


def test_every_field_has_a_source() -> None:
    for component in ihomemanager.COMPONENTS.values():
        for name in component.declared_fields:
            assert ihomemanager.CONFIDENCE[name.removesuffix("_raw")]


def _connection(device: dict[str, dict[int, int]] | None):
    """Return a stand-in for `ModbusConnection` with one unit at 247.

    Addresses the device does not hold are refused with 0x02, as the
    document says an unavailable register is.
    """

    class Unit:
        def __init__(self) -> None:
            self.mock = MockModbusConnection().for_unit(247)
            self.mock.input = dict(device["input"]) if device else {}
            self.mock.holding = dict(device["holding"]) if device else {}

        async def _read(self, table, address, count):
            if device is None:
                raise ModbusTimeoutError("Response timeout")
            if any(a not in table for a in range(address, address + count)):
                raise IllegalDataAddressError("illegal data address")
            return [table[a] for a in range(address, address + count)]

        async def read_input_registers(self, address, count):
            return await self._read(self.mock.input, address, count)

        async def read_holding_registers(self, address, count):
            return await self._read(self.mock.holding, address, count)

    class Connection:
        def __init__(self, params, timeout):
            assert params.port == 503
            self.unit = Unit()

        def for_unit(self, unit_id):
            assert unit_id == 247
            return self.unit

        async def close(self):
            pass

    return Connection


def _documented_device() -> dict[str, dict[int, int]]:
    """`_device`, answering every documented address and refusing the gaps."""
    device = _device()
    for space, start, count, why in IHOMEMANAGER_BANDS:
        if why.startswith("undocumented"):
            continue
        for address in range(start, start + count):
            device[space].setdefault(address, 0)
    return device


async def _survey(tmp_path, device):
    found = ihomemanager_direct.Found("192.0.2.40", 503, "iHomeManager")
    answers = SimpleNamespace(timeout=1, reporter="tester", comment="")
    with (
        patch.object(ihomemanager_direct, "ModbusConnection", _connection(device)),
        patch("sungrow_modbus.dump.asyncio.sleep", _no_sleep),
    ):
        return await ihomemanager_direct.async_survey(
            found, answers, tmp_path, lambda _text: None, address_tail="000.040"
        )


async def _no_sleep(_seconds):
    return None


async def test_a_survey_writes_an_ihomemanager_document(tmp_path) -> None:
    reading = await _survey(tmp_path, _documented_device())

    assert reading.code == 0
    document = reading.document
    assert document["document"] == "ihomemanager"
    assert "device" not in document
    section = document["ihomemanager"]
    assert section["unit"] == 247
    assert section["port"] == 503
    assert section["readings"]["protocol_version"]["value"] == "V1.0.2"
    assert reading.written.name == "ihomemanager-ihm-v1-2-3-tester-port503.json"
    assert json.loads(reading.written.read_text()) == document


async def test_a_refused_gap_is_recorded_as_asked_and_not_answered(tmp_path) -> None:
    reading = await _survey(tmp_path, _documented_device())

    dump = reading.document["ihomemanager"]["register_dump"]
    assert dump["input"]["8100"] is None  # 8101, undocumented and refused
    assert dump["input"]["7999"] == 0x072A


async def test_a_serial_in_a_gap_never_reaches_the_file(tmp_path) -> None:
    reading = await _survey(tmp_path, _documented_device())

    text = reading.written.read_text()
    assert "A123456789" not in text
    words = reading.document["ihomemanager"]["register_dump"]["input"]
    assert [words[str(8400 + i)] for i in range(5)] == [None] * 5
    assert reading.document["ihomemanager"]["masked_text"][0]["register"] == 8401


async def test_an_ihomemanager_that_answers_nothing_writes_nothing(tmp_path) -> None:
    reading = await _survey(tmp_path, None)

    assert reading.code == 1
    assert reading.written is None
    assert not list(tmp_path.iterdir())


async def test_a_second_reading_from_another_address_does_not_overwrite(
    tmp_path,
) -> None:
    first = await _survey(tmp_path, _documented_device())
    data = json.loads(first.written.read_text())
    data["ip_address_last_two_octets"] = "000.041"
    first.written.write_text(json.dumps(data))

    second = await _survey(tmp_path, _documented_device())

    assert second.written != first.written
    assert second.written.name.endswith("-000-040.json")


async def test_the_survey_reads_an_ihomemanager_instead_of_skipping_it() -> None:
    """Found by `identify`, it is collected for reading, not reported and dropped."""
    args = argparse.Namespace(host=["192.0.2.40"], port=503, unit=None)
    who = SimpleNamespace(kind="ihomemanager", model="iHomeManager", unit=247)

    async def identify(host, port):
        return who

    async def no_wallbox(host):
        return None

    with (
        patch.object(probe, "identify", identify),
        patch.object(probe, "described", lambda _who: "an iHomeManager"),
        patch.object(sungrow_survey.wallbox_direct, "async_identify", no_wallbox),
    ):
        inverters = await sungrow_survey._find(args, lambda *_a: None)

    assert inverters == []
    assert [
        ihomemanager_direct.Found("192.0.2.40", 503, "iHomeManager")
    ] == sungrow_survey._MANAGERS


@pytest.mark.parametrize("path", IHOMEMANAGER_DOCUMENTS, ids=lambda p: p.stem)
def test_a_committed_document_derives_its_name_and_hides_its_text(path) -> None:
    """Held to every committed reading, once there is one.

    Its name is rebuilt from its contents, allowing the address-tail or
    number suffix a second reading takes; and masking what it publishes
    again finds nothing, so no text survived in a gap.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    label = ihomemanager.label_for(document)
    assert path.stem == label or path.stem.startswith(f"{label}-")

    section = document["ihomemanager"]
    _again, records = ihomemanager.masked_text(section["register_dump"])
    assert records == []
    assert all(
        set(record) == {"space", "register", "count", "stand_in"}
        for record in section["masked_text"]
    )


async def test_a_unit_247_device_that_is_not_an_ihomemanager_is_not_read() -> None:
    """A Logger answers at unit 247 too; it is reported, not read as an iHM."""
    args = argparse.Namespace(host=["192.0.2.41"], port=502, unit=None)
    who = SimpleNamespace(
        kind="unit247", model="a device at unit 247", unit=247, device_type_code=0x0130
    )
    said: list[str] = []

    async def identify(host, port):
        return who

    async def no_wallbox(host):
        return None

    with (
        patch.object(probe, "identify", identify),
        patch.object(probe, "described", lambda _who: "a device at unit 247"),
        patch.object(sungrow_survey.wallbox_direct, "async_identify", no_wallbox),
    ):
        inverters = await sungrow_survey._find(args, lambda text="": said.append(text))

    assert inverters == []
    assert sungrow_survey._MANAGERS == []
    assert any("0x0130" in line for line in said)


def test_the_replay_line_keeps_the_ihomemanagers_port() -> None:
    """It answers on 502, 503 or 504; a replay on 502 would ask the wrong one."""
    asked = argparse.Namespace(
        port=504, timeout=10.0, address="hidden", reporter="tester", comment=""
    )
    line = sungrow_survey.replay_command(asked)
    assert "--port 504" in line
    assert "--timeout" not in line


SEED = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "dev"
    / "simulator_ihomemanager.json"
)


def test_the_simulator_seed_decodes_as_an_ihomemanager() -> None:
    """The dev loop's iHomeManager, held to the map so neither drifts."""
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    dump: dict[str, dict[str, int]] = {"input": {}, "holding": {}}
    for space in ("input", "holding"):
        for start, words in seed[space].items():
            for offset, word in enumerate(words):
                dump[space][str(int(start) + offset)] = word

    masked, records = ihomemanager.masked_text(dump)
    readings = ihomemanager.readings(masked)

    assert readings["device_type_code"]["value"] == "0x072A"
    assert readings["protocol_version"]["value"] == "V1.0.2"
    missing = {
        name.removesuffix("_raw")
        for component in ihomemanager.COMPONENTS.values()
        for name in component.declared_fields
    } - set(readings)
    assert not missing, f"the seed does not answer {sorted(missing)}"
    assert [record["register"] for record in records] == [8401]
