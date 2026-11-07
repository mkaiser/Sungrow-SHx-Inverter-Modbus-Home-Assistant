"""The SG string inverters' own map, read only.

The addresses are ha-modbus-manager's, from Sungrow's string-inverter protocol
V1.1.53; no SG has been diagnosed. What is asserted here is that the map
decodes as the protocol says, that an SG is told from a hybrid by input 5000
alone, and that nothing in it can write.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus import string_inverter
from sungrow_modbus.const import DEVICE_TYPES
from sungrow_modbus.diagnosis_document import stand_in
from sungrow_modbus.discovery import async_identify
from sungrow_modbus.identity import STRING_INVERTER
from sungrow_modbus.model import words_text
from sungrow_modbus.string_inverter import (
    COMPONENTS,
    MODELS,
    SungrowStringInverter,
    is_string_inverter,
    model_for,
)

DIAGNOSIS = (
    Path(__file__).resolve().parents[1] / "device-diagnosis" / "scripts" / "python"
)
sys.path.insert(0, str(DIAGNOSIS))

import probe  # noqa: E402
import string_inverter_direct  # noqa: E402
import sungrow_diagnosis  # noqa: E402

from .corpus import STRING_INVERTER_DOCUMENTS  # noqa: E402

#: An SG5.0RS at midday, as the protocol lays it out (protocol addresses).
WORDS = {
    4999: 0x2606,  # device type code
    5000: 50,  # 5.0 kW
    5001: 0,  # single phase
    5002: 123,  # 12.3 kWh today
    5003: 4567,  # 4567 kWh lifetime, low word first
    5004: 0,
    5007: 412,  # 41.2 degrees
    5010: 3601,  # MPPT1 360.1 V
    5011: 52,  # 5.2 A
    5014: 0xFFFF,  # no MPPT3
    5016: 1890,  # DC 1890 W
    5017: 0,
    5018: 2301,  # 230.1 V
    5019: 0xFFFF,
    5030: 1850,  # AC 1850 W
    5031: 0,
    5034: 999,  # PF 0.999
    5035: 500,  # 50.0 Hz
    5037: 0x8100,  # derating run
    5082: 0xFC18,  # meter -1000 W: low word, then the high word
    5083: 0xFFFF,
}


def _device(words: dict[int, int]) -> SungrowStringInverter:
    unit = MockModbusConnection().for_unit(1)
    unit.input = dict(words)
    return SungrowStringInverter(unit)


def test_an_sg_is_told_from_a_hybrid_by_its_type_code() -> None:
    assert model_for(0x2606) == "SG5.0RS"
    assert is_string_inverter(0x2433)
    # A hybrid's code is never an SG's, and no SG code is a hybrid's.
    assert not is_string_inverter(0x0E03)
    assert not set(MODELS) & set(DEVICE_TYPES)
    assert not is_string_inverter(None)


@pytest.mark.asyncio
async def test_the_realtime_block_decodes_as_the_protocol_says() -> None:
    device = _device(WORDS)
    report = await device.async_update()
    assert not report.failed
    assert device.model == "SG5.0RS"
    assert device.field("daily_pv_generation") == 12.3
    assert device.field("total_pv_generation") == 4567
    assert device.field("inverter_temperature") == 41.2
    assert device.field("mppt1_voltage") == 360.1
    assert device.field("mppt1_power") == pytest.approx(
        device.field("mppt1_voltage") * device.field("mppt1_current")
    )
    assert device.field("mppt3_voltage") is None, "0xFFFF is no tracker"
    assert device.field("mppt3_power") is None
    assert device.field("phase_b_voltage") is None
    assert device.field("total_dc_power") == 1890
    assert device.field("total_active_power") == 1850
    assert device.field("power_factor") == 0.999
    assert device.field("work_state") == "derating run"
    assert device.field("meter_active_power") == -1000


@pytest.mark.asyncio
async def test_a_block_refused_costs_only_itself() -> None:
    """The meter block is undocumented on RS; a refusal leaves the rest."""
    from modbus_connection import ModbusExceptionError

    device = _device(WORDS)
    real = device._unit.read_input_registers

    async def refuse_meter(address: int, count: int):
        if address == 5082:
            raise ModbusExceptionError(0x02)
        return await real(address, count)

    device._unit.read_input_registers = refuse_meter
    report = await device.async_update()
    assert set(report.failed) == {"sg_meter"}
    assert device.field("total_dc_power") == 1890


def test_nothing_in_the_map_writes() -> None:
    for component in COMPONENTS.values():
        for name, field in vars(component).items():
            assert not getattr(field, "writable", False), f"{component.__name__}.{name}"


def _text(text: str, count: int) -> list[int]:
    """Text as register words, high byte first, NUL padded to `count` words."""
    raw = text.encode("ascii").ljust(count * 2, b"\0")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, count * 2, 2)]


def _sg() -> dict[str, dict[int, int]]:
    """`WORDS` with its serial and firmware, answering the first band whole."""
    words = dict.fromkeys(range(4949, 5159), 0)
    words.update(WORDS)
    for offset, word in enumerate(_text("A123456789", 10)):
        words[4989 + offset] = word
    for offset, word in enumerate(_text("ARM_TEST_V1", 15)):
        words[4953 + offset] = word
    for offset, word in enumerate(_text("DSP_TEST_V1", 15)):
        words[4968 + offset] = word
    return {"input": words, "holding": {5006: 0x00AA, 5007: 1000}}


def _connection(device: dict[str, dict[int, int]] | None):
    """Return a stand-in for `ModbusConnection`, refusing what the device lacks."""

    class Unit:
        async def _read(self, table: dict[int, int], address: int, count: int):
            if device is None:
                raise ModbusTimeoutError("Response timeout")
            if any(a not in table for a in range(address, address + count)):
                raise IllegalDataAddressError("illegal data address")
            return [table[a] for a in range(address, address + count)]

        async def read_input_registers(self, address: int, count: int):
            return await self._read(device["input"] if device else {}, address, count)

        async def read_holding_registers(self, address: int, count: int):
            return await self._read(device["holding"] if device else {}, address, count)

    class Connection:
        def __init__(self, params: Any, timeout: float) -> None:
            assert params.port == 502

        def for_unit(self, unit: int) -> Unit:
            assert unit == 1
            return Unit()

        async def close(self) -> None:
            return None

    return Connection


async def _no_sleep(_seconds: float) -> None:
    return None


async def _diagnosis(tmp_path: Path, device: dict[str, dict[int, int]] | None):
    found = string_inverter_direct.Found("192.0.2.50", 502, 1, "SG5.0RS")
    answers = SimpleNamespace(timeout=1, reporter="tester", comment="")
    with (
        patch.object(string_inverter_direct, "ModbusConnection", _connection(device)),
        patch("sungrow_modbus.dump.asyncio.sleep", _no_sleep),
    ):
        return await string_inverter_direct.async_diagnosis(
            found, answers, tmp_path, lambda _text: None, address_tail="000.050"
        )


async def test_identify_names_an_sg_by_its_kind() -> None:
    """The config flow ignores `kind`; the diagnosis routes on it."""

    class Unit:
        async def read_input_registers(self, address: int, count: int) -> list[int]:
            words = _sg()["input"]
            return [words[address + i] for i in range(count)]

    class Connection:
        def for_unit(self, _unit: int) -> Unit:
            return Unit()

        async def close(self) -> None:
            return None

    identity = await async_identify(
        "192.0.2.50", connection_factory=lambda *_a, **_k: Connection()
    )
    assert identity.kind == STRING_INVERTER
    assert identity.model == "SG5.0RS"
    assert identity.serial == "A123456789"


async def test_a_diagnosis_writes_an_sg_document_without_its_serial(tmp_path) -> None:
    reading = await _diagnosis(tmp_path, _sg())

    assert reading.code == 0
    document = reading.document
    assert document["document"] == "string_inverter"
    assert document["device"] == {
        "device_type_code": "0x2606",
        "device_type": "SG5.0RS",
        "output_type": "single phase",
        "serial_anonymized_hashed": stand_in("A123456789"),
    }
    assert document["firmware"] == {"arm": "ARM_TEST_V1", "dsp": "DSP_TEST_V1"}
    section = document["string_inverter"]
    assert section["unit"] == 1
    dump = section["register_dump"]["input"]
    assert [dump[str(4989 + i)] for i in range(10)] == [None] * 10
    assert section["readings"]["total_dc_power"] == {
        "register": 5017,
        "value": 1890,
        "unit": "W",
    }
    assert section["readings"]["work_state"]["means"] == "derating run"
    written = reading.written.read_text()
    assert "A123456789" not in written
    assert json.loads(written) == document
    assert reading.written.name == (f"sg5-0rs-1p-tester-{stand_in('A123456789')}.json")


async def test_an_sg_that_answers_nothing_writes_nothing(tmp_path) -> None:
    reading = await _diagnosis(tmp_path, None)

    assert reading.code == 1
    assert reading.written is None
    assert not list(tmp_path.iterdir())


async def test_the_diagnosis_never_reads_an_sg_as_a_hybrid() -> None:
    """An SG is collected for its own reader, never for `_diagnosis`.

    So neither the block test nor the capability test can reach it.
    """
    args = argparse.Namespace(host=["192.0.2.50"], port=502, unit=None)
    who = SimpleNamespace(kind="string_inverter", model="SG5.0RS", unit=1, error=None)

    async def identify(host, port):
        return who

    async def no_wallbox(host):
        return None

    with (
        patch.object(probe, "identify", identify),
        patch.object(probe, "described", lambda _who: "an SG"),
        patch.object(sungrow_diagnosis.wallbox_direct, "async_identify", no_wallbox),
    ):
        inverters = await sungrow_diagnosis._find(args, lambda *_a: None)

    assert inverters == []
    assert [
        string_inverter_direct.Found("192.0.2.50", 502, 1, "SG5.0RS")
    ] == sungrow_diagnosis._STRING_INVERTERS


@pytest.mark.parametrize("path", STRING_INVERTER_DOCUMENTS, ids=lambda p: p.stem)
def test_a_committed_document_derives_its_name_and_hides_its_serial(path) -> None:
    """Held to every committed reading, once there is one."""
    document = json.loads(path.read_text(encoding="utf-8"))
    label = string_inverter.label_for(document)
    assert path.stem == label or path.stem.startswith(f"{label}-")
    dump = document["string_inverter"]["register_dump"].get("input", {})
    assert all(dump.get(str(4989 + i)) is None for i in range(10))


async def test_a_lost_link_fails_the_poll_as_on_a_hybrid() -> None:
    """One retry per component, then the poll raises: "connection lost"."""
    from modbus_connection import ModbusConnectionError

    device = _device(WORDS)
    asked: list[int] = []

    async def lose(address: int, count: int):
        asked.append(address)
        raise ModbusConnectionError("Connection lost before response was received")

    device._unit.read_input_registers = lose
    with pytest.raises(ModbusConnectionError):
        await device.async_update_tier("realtime")
    assert len(asked) == 2, "one read, one retry"


async def test_a_lost_link_once_is_retried() -> None:
    from modbus_connection import ModbusConnectionError

    device = _device(WORDS)
    real = device._unit.read_input_registers
    lost: list[int] = []

    async def lose_once(address: int, count: int):
        if not lost:
            lost.append(address)
            raise ModbusConnectionError("Connection lost before response was received")
        return await real(address, count)

    device._unit.read_input_registers = lose_once
    report = await device.async_update_tier("realtime")
    assert report.updated == {"sg_realtime"}
    assert device.field("total_dc_power") == 1890


def test_the_simulator_seed_is_the_diagnosis_it_came_from() -> None:
    """`scripts/dev/simulator_sg.json` is bleughb's dump, word for word.

    Only the serial differs: the diagnosis masked it, the seed carries the
    placeholder, so the masking runs end to end against the simulator.
    """
    repo = Path(__file__).resolve().parents[1]
    seed = json.loads((repo / "scripts/dev/simulator_sg.json").read_text())
    diagnosis = json.loads(
        (
            repo
            / "device-diagnosis/results/string_inverter"
            / "sg5-0rs-1p-bleughb-anon-85541281016.json"
        ).read_text()
    )["string_inverter"]["register_dump"]

    for space in ("input", "holding"):
        served = {
            int(start) + offset: word
            for start, words in seed[space].items()
            for offset, word in enumerate(words)
        }
        measured = {int(a): w for a, w in diagnosis[space].items() if w is not None}
        serial = range(4989, 4999) if space == "input" else range(0)
        assert {a: w for a, w in served.items() if a not in serial} == measured
    assert (
        words_text([seed["input"]["4949"][4989 - 4949 + i] for i in range(10)]).strip()
        == "A123456789"
    )


def test_every_model_has_a_tracker_count() -> None:
    """`serves` falls back to "keep it" without one; every mapped model has one."""
    from sungrow_modbus.string_inverter.registers import MODELS, MPPT_COUNTS

    assert set(MPPT_COUNTS) == set(MODELS)
    assert MPPT_COUNTS[0x2606] == 2, "measured: two trackers answer on an SG5.0RS"
