"""Decoding tests for the Sungrow SHx device library.

These run entirely against the in-memory mock backend that ships with
modbus-connection, so they need no inverter and no network.
"""

from __future__ import annotations

from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter, model_for

# "A2340600123" left-padded the way the inverter reports it, as 16-bit words.
SERIAL = "A2340600123"


def _words(text: str, length: int) -> list[int]:
    """Encode an ASCII string into `length` null-padded registers."""
    raw = text.encode("ascii").ljust(length * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, length * 2, 2)]


@pytest.fixture
def unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """Return a mock unit answering like an SH10RT."""
    mock_modbus_unit.input = {
        4951: [0x0002, 0x0000],  # protocol version, low word first
        4953: _words("SAPPHIRE-H_01011.95.12", 15),
        4968: _words("SAPPHIRE-H_03011.95.12", 15),
        4989: _words(SERIAL, 10),
        4999: 0x0E03,  # SH10RT
        5000: 100,  # x100 -> 10000 W rated
        5016: [0x1B58, 0x0000],  # 7000 W total DC power, low word first
    }
    return mock_modbus_unit


async def test_identity_decodes(unit: MockModbusUnit) -> None:
    """Serial, model code and rated power come back decoded."""
    inverter = SungrowInverter(unit)
    await inverter.async_update_identity()

    assert inverter.serial_number == SERIAL
    assert inverter.device_type_code == 0x0E03
    assert inverter.model == "SH10RT"
    assert inverter.identity.nominal_output_power == 10000
    assert inverter.identity.arm_software == "SAPPHIRE-H_01011.95.12"


async def test_identity_is_one_block_read(unit: MockModbusUnit) -> None:
    """The identity fields pool into a single input-register read."""
    inverter = SungrowInverter(unit)
    await inverter.async_update_identity()

    assert len(unit.read_events) == 1
    event = unit.read_events[0]
    assert event.register_type == "input"
    assert event.address == 4951
    # 4951 to 5001 inclusive: the block grew by one when the output type
    # register was added, and is still a single read.
    assert event.count == 51


async def test_total_dc_power_is_word_swapped(unit: MockModbusUnit) -> None:
    """A 32-bit Sungrow value arrives low word first."""
    inverter = SungrowInverter(unit)
    report = await inverter.async_update_tier(10)

    assert inverter.fast_input.total_dc_power == 7000
    # Tier 10 covers both the input and holding components.
    assert "fast_input" in report.updated
    assert not report.failed


async def test_unknown_device_type_has_no_model(unit: MockModbusUnit) -> None:
    """An unrecognised code leaves the model unset rather than guessing."""
    unit.input[4999] = 0xBEEF
    inverter = SungrowInverter(unit)
    await inverter.async_update_identity()

    assert inverter.device_type_code == 0xBEEF
    assert inverter.model is None
    assert model_for(None) is None


async def test_failed_component_is_reported_not_raised(
    unit: MockModbusUnit,
) -> None:
    """A block that times out is recorded against its component."""
    unit.fail_read(5016, ModbusTimeoutError("no answer"), register_type="input")
    inverter = SungrowInverter(unit)

    report = await inverter.async_update_tier(10)

    assert "fast_input" not in report.updated
    assert "fast_input" in report.failed
