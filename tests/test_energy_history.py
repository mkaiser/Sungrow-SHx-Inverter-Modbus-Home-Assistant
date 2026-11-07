"""The inverter's own energy history, input 6227-6637, over the cable.

Per quantity -- PV generation, direct consumption from PV, export from PV --
one sensor for this month and one for this year, by the inverter's clock,
with the months or years behind each in a `history` attribute. What matters:
the right register is "this month", the yearly slots sit where peter-sm's
dump puts them, and a house whose dongle refuses the block gets nothing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from modbus_connection.mock import MockModbusUnit
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.sungrow_modbus.const import (
    CONF_CAPABILITY_TEST_EXPORT,
    CONF_CAPABILITY_TEST_PV_CUT,
    CONF_CAPABILITY_TEST_RESTART,
    CONF_UNIT_ID,
    DOMAIN,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from sungrow_modbus.hybrid_inverter.capabilities import (
    PROBES,
    ZERO_MEANS_ABSENT,
    Capability,
)
from sungrow_modbus.hybrid_inverter.derived import Derived

from .conftest import SERIAL

ENTRY_DATA = {CONF_HOST: "127.0.0.1", CONF_PORT: 5020, CONF_UNIT_ID: 1}

#: Protocol addresses, one below the registers.
CLOCK = 4999  # holding 5000-5005

#: peter-sm's cable, 2026-10-31: monthly start, twelve months (0.1 kWh),
#: yearly start, and 2024-2026 as U32 totals.
PETER_SM: dict[str, tuple[int, tuple[int, ...], int, tuple[int, ...]]] = {
    "pv_generation": (
        6226,
        (56, 1459, 6536, 11967, 14241, 13539, 14082, 11958, 6904, 3362, 0, 0),
        6249,
        (78412, 85419, 84104),
    ),
    "direct_consumption": (
        6416,
        (56, 1147, 2520, 2687, 3039, 3724, 3872, 2924, 2071, 1466, 0, 0),
        6428,
        (24160, 27076, 23506),
    ),
    "export_from_pv": (
        6595,
        (0, 66, 1164, 5638, 8018, 6672, 7498, 6318, 2075, 329, 0, 0),
        6607,
        (35767, 36021, 37778),
    ),
}

KEYS = tuple(
    f"{quantity}_this_{period}" for quantity in PETER_SM for period in ("month", "year")
)


def _seed(
    unit: MockModbusUnit, *, clock: tuple[int, ...] = (2026, 10, 31, 14, 0, 0)
) -> None:
    """Give the unit peter-sm's history and a clock."""
    unit.holding.update(dict(zip(range(CLOCK, CLOCK + 6), clock, strict=True)))
    for monthly, months, yearly, years in PETER_SM.values():
        unit.input.update(dict(zip(range(monthly, monthly + 12), months, strict=True)))
        # The fifteen slots from 2015, empty before 2024; the reserved words
        # between the PV months and years answer over the cable too.
        unit.input.update(dict.fromkeys(range(monthly + 12, yearly + 30), 0))
        for index, total in enumerate(years):
            address = yearly + 2 * (9 + index)
            unit.input[address] = total & 0xFFFF
            unit.input[address + 1] = total >> 16


class _Inverter:
    """Answers `field` from a dict, which is all `Derived` asks of it."""

    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values

    def field(self, name: str) -> Any:
        return self.values.get(name)


def _derived(year: int, month: int, **values: float) -> Derived:
    return Derived(
        _Inverter({"system_clock_year": year, "system_clock_month": month, **values})  # type: ignore[arg-type]
    )


# -- the arithmetic --------------------------------------------------------------


def test_this_month_is_the_inverters_month() -> None:
    derived = _derived(
        2026, 3, pv_generation_month_03=653.6, pv_generation_month_04=1.0
    )
    assert derived.pv_generation_this_month == 653.6


@pytest.mark.parametrize(
    ("year", "month"), [(2026, 13), (2026, 0), (1999, 5), (2100, 5)]
)
def test_a_clock_out_of_range_is_no_month(year: int, month: int) -> None:
    derived = _derived(
        year, month, pv_generation_month_05=1.0, pv_generation_year_2026=1.0
    )
    assert derived.pv_generation_this_month is None
    assert derived.pv_generation_this_year is None
    assert derived.history("pv_generation_this_month") == {}


def test_after_the_fifteenth_year_there_is_no_year() -> None:
    assert _derived(2030, 1).pv_generation_this_year is None


def test_the_months_stop_at_this_one() -> None:
    """The months after it were cleared at the new year: not months of 0 kWh."""
    months = {f"pv_generation_month_{m:02d}": float(m) for m in range(1, 13)}
    history = _derived(2026, 3, **months).history("pv_generation_this_month")
    assert history == {"2026-01": 1.0, "2026-02": 2.0, "2026-03": 3.0}


def test_a_year_at_zero_is_before_the_installation() -> None:
    years = {f"pv_generation_year_{y}": 0.0 for y in range(2015, 2030)}
    years |= {"pv_generation_year_2025": 8541.9, "pv_generation_year_2026": 120.0}
    history = _derived(2026, 1, **years).history("pv_generation_this_year")
    assert history == {"2025": 8541.9, "2026": 120.0}


def test_the_history_is_probed_on_the_months_and_zero_is_absence() -> None:
    assert PROBES[Capability.ENERGY_HISTORY] == tuple(
        f"pv_generation_month_{m:02d}" for m in range(1, 13)
    )
    assert Capability.ENERGY_HISTORY in ZERO_MEANS_ABSENT


# -- on a device page ------------------------------------------------------------


async def _setup(hass: HomeAssistant, unit: MockModbusUnit) -> MockConfigEntry:
    options: dict[str, Any] = {
        CONF_CAPABILITY_TEST_RESTART: False,
        CONF_CAPABILITY_TEST_EXPORT: False,
        CONF_CAPABILITY_TEST_PV_CUT: False,
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


def _entity(hass: HomeAssistant, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_{key}")


async def test_peter_sms_history_reads_back_as_his_totals(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    _seed(sungrow_unit)
    await _setup(hass, sungrow_unit)

    states = {}
    for key in KEYS:
        entity_id = _entity(hass, key)
        assert entity_id is not None, key
        states[key] = hass.states.get(entity_id)

    assert {key: float(state.state) for key, state in states.items()} == {
        "pv_generation_this_month": 336.2,
        "pv_generation_this_year": 8410.4,
        "direct_consumption_this_month": 146.6,
        "direct_consumption_this_year": 2350.6,
        "export_from_pv_this_month": 32.9,
        "export_from_pv_this_year": 3777.8,
    }
    pv_month = states["pv_generation_this_month"]
    assert pv_month.attributes["state_class"] == "total_increasing"
    assert pv_month.attributes["unit_of_measurement"] == "kWh"
    assert list(pv_month.attributes["history"]) == [
        f"2026-{m:02d}" for m in range(1, 11)
    ]
    assert states["pv_generation_this_year"].attributes["history"] == {
        "2024": 7841.2,
        "2025": 8541.9,
        "2026": 8410.4,
    }


@pytest.mark.parametrize("quantity", sorted(PETER_SM))
def test_each_year_so_far_is_the_sum_of_its_months(quantity: str) -> None:
    """What placed the yearly slots: 2026's slot holds this year's months."""
    _, months, _, years = PETER_SM[quantity]
    assert sum(months) == years[-1]


async def test_a_house_without_the_block_gets_none_of_it(
    hass: HomeAssistant, sungrow_unit: MockModbusUnit
) -> None:
    """Unseeded, every month reads 0: what a model outside the block answers."""
    await _setup(hass, sungrow_unit)

    assert not [key for key in KEYS if _entity(hass, key) is not None]
