"""Which unit a wallbox answers on behind a plain Modbus TCP endpoint.

A WiNet-S forwards a wallbox on its RS485 bus at a unit of its own choosing:
3 here (an AC22E-01), 2 and 3 in the ioBroker thread and evcc discussion
#7104, 2 in ha-modbus-manager issue #127, 4 for an AC011E-01 in issue #786
(2026-11-12). The search tries each, and only a model name that is a Sungrow
wallbox's ("AC...") counts: unit 2 is also where some endpoints answer an SBR.
"""

from __future__ import annotations

from collections.abc import Callable

from modbus_connection import ModbusExceptionError, ModbusTimeoutError
import pytest

from sungrow_modbus.wallbox import MODEL_NAME, UNITS, probe_units


def _words(text: str) -> list[int]:
    raw = text.encode("ascii").ljust(MODEL_NAME.length * 2, b"\x00")
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, len(raw), 2)]


class _Unit:
    """One unit id behind the endpoint: a name, zeros, a refusal or silence."""

    def __init__(self, answer: object) -> None:
        self.answer = answer
        self.asked = 0

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        self.asked += 1
        assert (address, count) == (MODEL_NAME.address, MODEL_NAME.length)
        if isinstance(self.answer, BaseException):
            raise self.answer
        assert isinstance(self.answer, list)
        return self.answer


def _endpoint(
    answers: dict[int, object],
) -> tuple[dict[int, _Unit], Callable[[int], _Unit]]:
    # A unit the dongle does not forward answers zeros, as a WiNet-S does.
    units = {
        unit: _Unit(answers.get(unit, [0] * MODEL_NAME.length)) for unit in range(256)
    }
    return units, lambda unit_id: units[unit_id]


def test_the_units_tried_and_their_order() -> None:
    # 3 first, as measured here; 248 last, for an adapter wired to the wallbox.
    assert UNITS == (3, 2, 4, 248)


@pytest.mark.parametrize("unit", [2, 3, 4, 248])
async def test_a_wallbox_is_found_on_each_unit_it_is_reported_on(unit: int) -> None:
    _units, unit_for = _endpoint({unit: _words("AC011E-01")})
    assert await probe_units(unit_for) == unit


async def test_the_first_unit_that_names_a_wallbox_wins() -> None:
    units, unit_for = _endpoint({3: _words("AC22E-01"), 4: _words("AC011E-01")})
    assert await probe_units(unit_for) == 3
    assert units[4].asked == 0


async def test_a_name_that_is_not_a_wallbox_does_not_count() -> None:
    # Printable, but not a Sungrow wallbox: an SBR or anything else at unit 2.
    _units, unit_for = _endpoint({2: _words("SBR096")})
    assert await probe_units(unit_for) is None


async def test_a_refusal_counts_as_an_answer_and_the_search_goes_on() -> None:
    # A refusal is the endpoint answering, so the dongle-only units are asked.
    _units, unit_for = _endpoint(
        {3: ModbusExceptionError(2), 2: [0] * MODEL_NAME.length, 4: _words("AC011E-01")}
    )
    assert await probe_units(unit_for) == 4


async def test_a_silent_endpoint_is_asked_only_3_and_248() -> None:
    # The inverter's own LAN port goes silent on wallbox units: each one asked
    # costs a timeout, so 2 and 4 are left out, as before they were tried.
    silent = ModbusTimeoutError("no answer")
    units, unit_for = _endpoint({3: silent, 2: silent, 4: silent, 248: silent})
    assert await probe_units(unit_for) is None
    assert {unit: units[unit].asked for unit in (3, 2, 4, 248)} == {
        3: 1,
        2: 0,
        4: 0,
        248: 1,
    }


async def test_zeros_everywhere_are_no_wallbox() -> None:
    _units, unit_for = _endpoint({})
    assert await probe_units(unit_for) is None
