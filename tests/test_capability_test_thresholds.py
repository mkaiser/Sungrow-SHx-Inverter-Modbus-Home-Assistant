"""The start thresholds (33149, 33150) and the charge window's headroom.

The battery's power is scripted window by window, the way the windows' tests
script it: what is tested is the procedure -- when it runs, what it writes,
how it judges a stop, and that the threshold goes back to its word.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from modbus_connection.mock import MockModbusUnit
import pytest

from sungrow_modbus import SungrowInverter
from sungrow_modbus.capability_test import (
    CONFIRMED,
    NO_EFFECT,
    CapabilityTest,
    Options,
    ledger,
)
from sungrow_modbus.capability_test.procedure import Sample

CHARGE_START = 33148  # holding 33149, 10 W
DISCHARGE_START = 33149  # holding 33150, 10 W
SOC = 13022


class FakeClock:
    """A clock that agrees to anything, so a budget costs no time."""

    def __init__(self) -> None:
        """Start at an arbitrary origin."""
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake time."""
        return self.now

    async def sleep(self, seconds: float) -> None:
        """Advance instead of waiting."""
        self.now += seconds


@pytest.fixture
def house(sungrow_unit: MockModbusUnit) -> MockModbusUnit:
    """Return an SH10RT at 60 % with both thresholds at 100 W."""
    sungrow_unit.input[SOC] = 600
    sungrow_unit.holding[CHARGE_START] = 10
    sungrow_unit.holding[DISCHARGE_START] = 10
    return sungrow_unit


async def _run(unit: MockModbusUnit, **options: Any) -> CapabilityTest:
    inverter = SungrowInverter(unit)
    await inverter.async_update()
    run = CapabilityTest(inverter, options=Options(**options), clock=FakeClock())
    run._plan_budget()
    await run._preflight()
    return run


def _script(run: CapabilityTest, battery: list[float], *, export: float = 0.0) -> None:
    """Script battery power, in the inverter's sign: negative charging."""
    values = iter(battery)
    last = battery[-1]

    async def sample() -> Sample:
        return Sample(
            at=run.clock.monotonic(),
            pv=1000.0,
            battery=next(values, last),
            export=export,
            load=800.0,
            soc=60.0,
        )

    run._sample = sample  # type: ignore[method-assign]


def _check(results: list[Any], name: str) -> Any:
    return next(row for row in results if row.check == name)


async def test_a_threshold_above_the_charge_stops_it_and_goes_back(
    house: MockModbusUnit,
) -> None:
    run = await _run(house)
    assert any(p.field == "battery_charging_start_power" for p in run.plan)
    # One look, then before, during and after; the discharge check looks too.
    _script(run, [-600.0] * 11 + [0.0] * 10 + [-600.0] * 10 + [0.0])
    results = await run._start_power_effects()
    row = _check(results, "charging start threshold")
    assert row.verdict == CONFIRMED
    assert row.commanded == 1000
    assert house.holding[CHARGE_START] == 10


async def test_a_charge_that_carries_on_is_recorded_as_such(
    house: MockModbusUnit,
) -> None:
    run = await _run(house)
    _script(run, [-600.0] * 40)
    row = _check(await run._start_power_effects(), "charging start threshold")
    assert row.verdict == NO_EFFECT
    assert house.holding[CHARGE_START] == 10


async def test_a_threshold_above_the_discharge_stops_it(
    house: MockModbusUnit,
) -> None:
    run = await _run(house, skip=frozenset({"charging start threshold"}))
    _script(run, [600.0] * 11 + [0.0] * 10 + [600.0] * 10)
    row = _check(await run._start_power_effects(), "discharging start threshold")
    assert row.verdict == CONFIRMED
    assert house.holding[DISCHARGE_START] == 10


@pytest.mark.parametrize(
    ("battery", "export"),
    [(-100.0, 0.0), (-900.0, 0.0), (-600.0, 400.0)],
    ids=["too-little", "too-much-for-the-maximum", "spilling-to-the-grid"],
)
async def test_a_flow_the_threshold_cannot_gate_is_left_alone(
    house: MockModbusUnit, battery: float, export: float
) -> None:
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house, skip=frozenset({"discharging start threshold"}))
    _script(run, [battery] * 5, export=export)
    assert await run._start_power_effects() == []
    assert CHARGE_START not in writes
    note = next(n for n in run.unestablished if n.startswith("no charging threshold"))
    assert ledger.note_check(note) == "charging start threshold"


def test_auto_repeat_waits_for_a_small_charge_with_nothing_exported() -> None:
    folded = ledger.fold(
        [
            {
                "read_at": "t1",
                "block": {
                    "outcome": 3,
                    "readback": [],
                    "effects": [],
                    "conditions": {},
                    "not_established": ["no charging threshold check: not now"],
                },
            }
        ]
    )
    small = ledger.Live(pv=900.0, battery=-500.0, export=0.0, soc=60.0)
    large = ledger.Live(pv=4000.0, battery=-2500.0, export=0.0, soc=60.0)
    spilling = ledger.Live(pv=1500.0, battery=-500.0, export=600.0, soc=60.0)
    assert "charging start threshold" in ledger.due(folded, small)
    assert "charging start threshold" not in ledger.due(folded, large)
    assert "charging start threshold" not in ledger.due(folded, spilling)


# -- the charge window's headroom ---------------------------------------------


async def test_a_window_under_a_full_charge_is_not_written(
    house: MockModbusUnit,
) -> None:
    """The pack at its ceiling from PV: no room for a window to start anything."""
    house.holding.update(
        dict(zip(range(4999, 5005), (2026, 10, 31, 14, 0, 0), strict=True))
    )
    house.holding.update({**dict.fromkeys(range(33207, 33219), 0), 33207: 0x55})
    house.holding[13057] = 1000  # max SoC 100 %
    writes: list[int] = []
    house.on_write(lambda event: writes.append(event.address))
    run = await _run(house, charge_window=True)
    run.snapshot.battery_ceiling = 3000.0
    _script(run, [-2900.0] * 5)
    assert await run._charge_window_effect() == []
    assert not [address for address in writes if 33207 <= address <= 33218]
    assert any("no room to start" in note for note in run.unestablished)


# -- the feed-in ratio beside the export limit ----------------------------------


async def test_the_feed_in_ratio_is_recorded_beside_the_export_limit(
    house: MockModbusUnit,
) -> None:
    """13088 read before and while the limit holds; recorded, never judged."""
    house.holding[13086] = 0xAA  # feed-in limitation on
    house.holding[13087] = 1000  # 13088: 100.0 %
    house.input[5621] = 0  # export limit minimum
    house.input[5622] = 1000  # export limit maximum, 10 W per count
    run = await _run(house)
    _script(run, [0.0] * 40, export=3000.0)

    async def bracket(_check: str, *_args: Any, **_kwargs: Any) -> Any:
        apply = _args[3]
        house.holding[13087] = 300  # the inverter restates the limit
        assert await apply() is None
        return SimpleNamespace(detail=None, _replace=lambda **kw: kw)

    run._bracket = bracket  # type: ignore[method-assign]
    await run._export_effect()
    ratio = run.conditions["feed_in_ratio"]
    assert ratio["before_percent"] == 100.0
    assert ratio["during_percent"] == 30.0
    assert ratio["limit_w"] > 0
