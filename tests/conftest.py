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
#:
#: Two of these entries are the difference between a plausible double and a
#: misleading one, and both were found by a test that expected the hardware's
#: behaviour and got the mock's:
#:
#: * **5001 (register 5002) is the output type**, and an SH10RT is 3P4L. Left
#:   unseeded it reads 0, which is "single phase" — so the double contradicted
#:   its own model code, and every test silently exercised the single-phase
#:   path.
#: * **An unseeded address reads 0, but a real inverter sends 0xFFFF** for a
#:   measuring point it does not have. Without the sentinels below, MPPT3 and
#:   MPPT4 probe as *present* on a two-tracker inverter, and the capability
#:   gating this project is built around is never exercised at all.
SH10RT_INPUT_REGISTERS: dict[int, int | list[int]] = {
    4951: [0x0002, 0x0000],
    4953: encode_string("SAPPHIRE-H_01011.95.12", 15),
    4968: encode_string("SAPPHIRE-H_03011.95.12", 15),
    4989: encode_string(SERIAL, 10),
    4999: 0x0E03,
    5000: 100,
    5001: 1,  # reg 5002: 3P4L, which is what an SH10RT is
    5014: 0xFFFF,  # MPPT3 voltage: absent, as the specification spells it
    5015: 0xFFFF,  # MPPT3 current
    5016: [0x1B58, 0x0000],
    5114: 0xFFFF,  # MPPT4 voltage
    5115: 0xFFFF,  # MPPT4 current
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
