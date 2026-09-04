"""Shared fixtures for the Sungrow SHx tests."""

from __future__ import annotations

from collections.abc import Generator

from modbus_connection.mock import MockModbusConnection, MockModbusUnit
import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]

SERIAL = "A2340600123"


def encode_string(text: str, registers: int) -> list[int]:
    """Encode an ASCII string into null-padded 16-bit registers."""
    raw = text.encode("ascii").ljust(registers * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, registers * 2, 2)]


#: An inverter answering like an SH10RT producing 7 kW.
SH10RT_INPUT_REGISTERS: dict[int, int | list[int]] = {
    4951: [0x0002, 0x0000],
    4953: encode_string("SAPPHIRE-H_01011.95.12", 15),
    4968: encode_string("SAPPHIRE-H_03011.95.12", 15),
    4989: encode_string(SERIAL, 10),
    4999: 0x0E03,
    5000: 100,
    5016: [0x1B58, 0x0000],
}


@pytest.fixture
def sungrow_unit() -> MockModbusUnit:
    """Return a mock unit answering like an SH10RT."""
    unit = MockModbusConnection().for_unit(1)
    unit.input = dict(SH10RT_INPUT_REGISTERS)
    return unit


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Load custom_components/ in every Home Assistant test."""
    yield
