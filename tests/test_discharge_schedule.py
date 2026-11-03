"""The discharge schedules, registers 33151-33158 and 33179-33187 (#785).

Outside Sungrow's protocol document: Korsberg has used them for years, and two
houses on P023 answer the same layout. Read only, so what matters is that each
window reads as the owner set it -- including the 24:00 that ends one at
midnight -- and that an inverter without them gets none of it.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_CONTROL_TEST_EXPORT,
    CONF_CONTROL_TEST_PV_CUT,
    CONF_CONTROL_TEST_RESTART,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.hybrid_inverter.capabilities import (
    MODE_CODES_ONLY,
    PROBES,
    Capability,
)
from sungrow_modbus.hybrid_inverter.derived import Derived

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses, one below the registers: 33151 is at 33150.
WEEKDAY = 33150
WEEKEND_ENABLE = 33178
WEEKEND = 33179

#: peter-sm's schedule as its survey reads it: the first window 00:00-24:00
#: on both days, the second unused, the weekend on.
SCHEDULE: dict[int, int] = {
    **dict(zip(range(WEEKDAY, WEEKDAY + 8), (0, 0, 24, 0, 0, 0, 0, 0), strict=True)),
    WEEKEND_ENABLE: 0xAA,
    **dict(zip(range(WEEKEND, WEEKEND + 8), (0, 0, 24, 0, 0, 0, 0, 0), strict=True)),
}

PARTS = tuple(
    f"{part}_{unit}" for part in ("start", "end") for unit in ("hour", "minute")
)


class _Inverter:
    """Answers `field` from a dict, which is all `Derived` asks of it."""

    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def field(self, name: str) -> Any:
        return self.values.get(name)


def _derived(day: str, number: int, words: tuple[int, int, int, int]) -> Derived:
    names = (f"{day}_discharge_{part.replace('_', f'_{number}_')}" for part in PARTS)
    return Derived(_Inverter(dict(zip(names, words, strict=True))))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("words", "shown"),
    [
        ((0, 0, 24, 0), "00:00-24:00"),
        ((22, 30, 6, 5), "22:30-06:05"),
        ((0, 0, 0, 0), "00:00-00:00"),
        # 24 is midnight at the end of the day; 24 with minutes is no time.
        ((0, 0, 24, 30), None),
        ((25, 0, 6, 0), None),
        ((0, 60, 6, 0), None),
    ],
)
def test_a_window_reads_as_its_two_times(
    words: tuple[int, int, int, int], shown: str | None
) -> None:
    assert _derived("weekday", 1, words).weekday_discharge_window_1 == shown
    assert _derived("weekend", 2, words).weekend_discharge_window_2 == shown


def test_a_missing_register_is_no_window() -> None:
    assert Derived(_Inverter({})).weekday_discharge_window_1 is None  # type: ignore[arg-type]


@pytest.mark.parametrize(("raw", "on"), [(0xAA, True), (0x55, False), (0, None)])
def test_the_weekend_flag_is_a_mode_code(raw: int, on: bool | None) -> None:
    derived = Derived(_Inverter({"weekend_discharge_raw": raw}))  # type: ignore[arg-type]
    assert derived.weekend_discharge is on


def test_only_a_mode_code_grants_the_schedule() -> None:
    """The hours read 0 on a house that never set them; the flag decides."""
    assert PROBES[Capability.DISCHARGE_SCHEDULE] == ("weekend_discharge_raw",)
    assert Capability.DISCHARGE_SCHEDULE in MODE_CODES_ONLY


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    options: dict[str, Any] = {
        CONF_CONTROL_TEST_RESTART: False,
        CONF_CONTROL_TEST_EXPORT: False,
        CONF_CONTROL_TEST_PV_CUT: False,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        options=options,
        unique_id=SERIAL,
        title="SH10RT",
    )
    entry.add_to_hass(hass)
    with patch("custom_components.sungrow_modbus.async_get_unit", return_value=unit):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def _entity(hass: HomeAssistant, domain: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{SERIAL}_{key}")


async def test_the_schedules_read_as_windows_and_a_flag(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    sungrow_unit.holding.update(SCHEDULE)
    await _setup(hass, sungrow_unit)

    shown = {}
    for key in (
        "weekday_discharge_window_1",
        "weekday_discharge_window_2",
        "weekend_discharge_window_1",
        "weekend_discharge_window_2",
    ):
        entity_id = _entity(hass, "sensor", key)
        assert entity_id is not None, key
        shown[key] = hass.states.get(entity_id).state
    assert shown == {
        "weekday_discharge_window_1": "00:00-24:00",
        "weekday_discharge_window_2": "00:00-00:00",
        "weekend_discharge_window_1": "00:00-24:00",
        "weekend_discharge_window_2": "00:00-00:00",
    }
    flag = _entity(hass, "binary_sensor", "weekend_discharge")
    assert flag is not None
    assert hass.states.get(flag).state == "on"


async def test_nothing_writes_them(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Read only until a watched write: no time, switch or number for them."""
    sungrow_unit.holding.update(SCHEDULE)
    await _setup(hass, sungrow_unit)

    registry = er.async_get(hass)
    writable = {
        entry.unique_id
        for entry in registry.entities.values()
        if entry.domain in {"time", "switch", "number", "select"}
    }
    assert not {uid for uid in writable if "_discharge_" in uid and "power" not in uid}


async def test_an_inverter_without_them_gets_none_of_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Unseeded, the weekend flag reads 0, which no Sungrow mode register holds."""
    await _setup(hass, sungrow_unit)

    assert _entity(hass, "sensor", "weekday_discharge_window_1") is None
    assert _entity(hass, "sensor", "weekend_discharge_window_1") is None
    assert _entity(hass, "binary_sensor", "weekend_discharge") is None
