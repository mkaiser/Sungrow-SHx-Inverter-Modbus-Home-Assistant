"""Decoding tests for the Sungrow SHx device library.

These run entirely against the in-memory mock backend that ships with
modbus-connection, so they need no inverter and no network.
"""

from __future__ import annotations

from modbus_connection import ModbusProtocolError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import Capability, SungrowInverter, model_for

# "A123456789" left-padded the way the inverter reports it, as 16-bit words.
SERIAL = "A123456789"


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
    report = await inverter.async_update_tier("fast")

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

    report = await inverter.async_update_tier("fast")

    assert "fast_input" not in report.updated
    assert "fast_input" in report.failed


async def test_an_absent_register_does_not_empty_its_whole_tier(
    unit: MockModbusUnit,
) -> None:
    """Registers 2611 and beyond are unreadable on the reference SH10RT.

    Not silent, not sentinel-valued: a single-register read of 2612 fails with
    a protocol error. They hold two firmware strings, and while they were
    pooled into `slowest_input`'s one 58-register read, those two absent
    registers left all 36 other slowest-tier fields permanently empty -- on
    the maintainer's own inverter. `scripts/layout.py` now reads each on its
    own, so the cost of an absent register is that register.
    """
    for address in (2612, 2628):
        unit.fail_read(
            address,
            ModbusProtocolError("no such register"),
            register_type="input",
        )
    inverter = SungrowInverter(unit)

    report = await inverter.async_update_tier("slowest")

    assert set(report.failed) == {"sub_controller_firmware", "battery_firmware"}
    assert "slowest_input" in report.updated
    # The point of the fix: the tier's other fields carry values.
    assert inverter.slowest_input.sungrow_version_1 is not None


async def test_an_all_null_string_reads_as_no_value(unit: MockModbusUnit) -> None:
    """Sungrow fills a UTF-8 field it has nothing for with 0x00.

    The reference SH10RT does exactly that for the battery firmware string,
    having a Pylontech rather than a Sungrow pack. Decoded literally that is
    "", which would reach Home Assistant as a reading and, worse, count as
    evidence of a battery firmware when capabilities are probed.
    """
    unit.input[2581] = _words("SAPPHIRE-H_01011.95.12", 11)
    unit.input[2628] = [0] * 15
    inverter = SungrowInverter(unit)

    await inverter.async_update_tier("slowest")

    assert inverter.field("sungrow_version_4_sungrow_battery") is None
    assert Capability.BATTERY_FIRMWARE not in inverter.capabilities()
    # A string that is present still arrives intact.
    assert inverter.field("sungrow_version_1") == "SAPPHIRE-H_01011.95.12"
