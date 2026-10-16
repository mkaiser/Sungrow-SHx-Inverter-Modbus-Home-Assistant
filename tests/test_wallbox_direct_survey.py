"""The survey of a wallbox at its own address, over TLS.

Driven with a mock unit answering the words the committed AC22E-01 reading
holds, so what is checked is the shape of the document and what it keeps
out of it, not the wallbox.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusConnection

SURVEY = (
    Path(__file__).resolve().parents[1] / "device-fingerprints" / "scripts" / "python"
)
sys.path.insert(0, str(SURVEY))

import probe  # noqa: E402
import sungrow_survey  # noqa: E402
import wallbox_direct  # noqa: E402

FIXTURE = Path(__file__).parent / "data" / "wallbox_ac22e01_completed_session.json"

#: An invented serial, as the wallbox would answer it at input 21200.
SERIAL_WORDS = [0x4139, 0x3837, 0x3635, 0x3433, 0x3231, 0x0000]
#: The short code at 21210-21213 that only the direct path answers.
CODE_WORDS = [0x4150, 0x3030, 0x3130, 0x3231]


class _Silent:
    """A wallbox that answers no read at all, as a real one times out."""

    async def read_input_registers(self, *_args):
        raise ModbusTimeoutError("Response timeout")

    async def read_holding_registers(self, *_args):
        raise ModbusTimeoutError("Response timeout")


def _connection(words: dict | None):
    """Return a stand-in for `ModbusConnection` answering these words."""
    if words is None:
        dump = json.loads(FIXTURE.read_text())["wallbox"]["register_dump"]
        words = {
            space: {int(a): v for a, v in values.items() if v is not None}
            for space, values in dump.items()
        }
        words["input"].update(dict(zip(range(21200, 21206), SERIAL_WORDS, strict=True)))
        words["input"].update(dict(zip(range(21210, 21214), CODE_WORDS, strict=True)))

    class Connection:
        def __init__(self, params, timeout):
            assert params.port == 516
            assert params.verify is False
            self.unit = MockModbusConnection().for_unit(248)
            self.unit.input = dict(words.get("input", {}))
            self.unit.holding = dict(words.get("holding", {}))

        def for_unit(self, unit_id):
            assert unit_id == 248
            return self.unit if words else _Silent()

        async def close(self):
            pass

    return Connection


async def _survey(tmp_path, words=None):
    found = wallbox_direct.Found("192.0.2.23", "AC22E-01")
    answers = SimpleNamespace(timeout=1, reporter="tester", comment="")
    with patch.object(wallbox_direct, "ModbusConnection", _connection(words)):
        return await wallbox_direct.async_survey(
            found,
            answers,
            tmp_path,
            lambda _text: None,
            address_tail="000.023",
            local_time=probe._local_time,
        )


async def test_a_direct_wallbox_survey_writes_a_wallbox_document(tmp_path) -> None:
    reading = await _survey(tmp_path)

    assert reading.code == 0
    document = reading.document
    assert document["document"] == "wallbox"
    assert "device" not in document
    section = document["wallbox"]
    assert section["unit"] == 248
    assert section["path"] == "tls"
    assert section["readings"]["model_name"]["value"] == "AC22E-01"
    assert section["serial_anonymized_hashed"].startswith("anon-")
    assert reading.written.name == (
        f"ac22e01-tester-{section['serial_anonymized_hashed']}-wallbox-tls.json"
    )
    assert json.loads(reading.written.read_text()) == document


async def test_neither_the_serial_nor_the_unknown_code_is_published(tmp_path) -> None:
    """The serial is masked, and 21210-21213 until a second unit says what it is."""
    reading = await _survey(tmp_path)

    published = reading.document["wallbox"]["register_dump"]["input"]
    assert [published[str(a)] for a in range(21200, 21206)] == [None] * 6
    assert [published[str(a)] for a in range(21210, 21214)] == [None] * 4
    assert "A987654321" not in reading.written.read_text()


async def test_a_wallbox_that_answers_nothing_writes_nothing(tmp_path) -> None:
    reading = await _survey(tmp_path, words={})

    assert reading.code == 1
    assert reading.written is None
    assert not list(tmp_path.iterdir())


async def test_a_wallbox_address_given_by_hand_is_not_asked_as_an_inverter() -> None:
    """No 502 there, so the inverter survey would only read nothing."""
    args = argparse.Namespace(host=["192.0.2.23"], port=502, unit=1)
    found = wallbox_direct.Found("192.0.2.23", "AC22E-01")

    async def identify(host):
        return found

    async def closed(*_args):
        return False

    with (
        patch.object(wallbox_direct, "async_identify", identify),
        patch.object(probe, "_tcp_open", closed),
    ):
        inverters = await sungrow_survey._find(args, lambda *_a: None)

    assert inverters == []
    assert [found] == sungrow_survey._WALLBOXES
