"""Tests for backend-neutral endpoint identification."""

from typing import Any

import pytest

from sungrow_modbus.discovery import async_identify


class _FakeUnit:
    def __init__(self, registers: dict[int, list[int]]) -> None:
        self.registers = registers

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        if address not in self.registers:
            raise TimeoutError
        return self.registers[address][:count]

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        return await self.read_input_registers(address, count)


class _FakeConnection:
    def __init__(self, units: dict[int, dict[int, list[int]]]) -> None:
        self.units = units
        self.asked: list[int] = []

    def for_unit(self, unit: int) -> _FakeUnit:
        self.asked.append(unit)
        return _FakeUnit(self.units.get(unit, {}))

    async def close(self) -> None:
        return None


def factory(connection: _FakeConnection) -> Any:
    def make(*_args: object, **_kwargs: object) -> _FakeConnection:
        return connection

    return make


@pytest.mark.asyncio
async def test_identify_finds_cluster_unit_without_reading_later_units() -> None:
    connection = _FakeConnection(
        {2: {4989: [0x4139, 0x3837, 0x3635, 0x3433, 0x3231], 4999: [0x0E0F]}}
    )

    identity = await async_identify("192.0.2.1", connection_factory=factory(connection))

    assert identity.serial == "A987654321"
    assert identity.unit == 2
    assert identity.device_type_code == 0x0E0F
    assert connection.asked == [1, 2]


@pytest.mark.asyncio
async def test_identify_stops_when_a_unit_answers_without_a_serial() -> None:
    connection = _FakeConnection({1: {4989: [0] * 10}})

    identity = await async_identify("192.0.2.2", connection_factory=factory(connection))

    assert identity.serial is None
    assert identity.error == "answered, but reported no serial"
    assert connection.asked == [1]


@pytest.mark.asyncio
async def test_identify_finds_ihomemanager_after_inverter_candidates() -> None:
    connection = _FakeConnection({247: {7999: [0x072A], 8000: [0x5631, 0x2E30]}})

    identity = await async_identify("192.0.2.3", connection_factory=factory(connection))

    assert identity.kind == "ihomemanager"
    assert identity.unit == 247
    assert identity.device_type_code == 0x072A
    assert identity.model == "iHomeManager (protocol V1.0)"
    assert connection.asked == [1, 2, 3, 4, 5, 247]


@pytest.mark.asyncio
async def test_another_type_code_at_unit_247_is_not_an_ihomemanager() -> None:
    """A Sungrow Logger answers a type code at 8000 on unit 247 too.

    Only the iHomeManager's documented 0x072A names one; anything else is
    reported by its code, so a Logger is never read as an iHomeManager.
    """
    connection = _FakeConnection({247: {7999: [0x0130]}})

    identity = await async_identify("192.0.2.4", connection_factory=factory(connection))

    assert identity.kind == "unit247"
    assert identity.unit == 247
    assert identity.device_type_code == 0x0130
    assert identity.error is None
    assert "0x0130" in identity.model


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "model"),
    [(0x0705, "Logger3000"), (0x0710, "Logger1000"), (0x0718, "Logger4000")],
)
async def test_a_logger_is_named_by_its_type_code(code, model) -> None:
    connection = _FakeConnection({247: {7999: [code]}})

    identity = await async_identify("192.0.2.5", connection_factory=factory(connection))

    assert identity.kind == "logger"
    assert model in identity.model
