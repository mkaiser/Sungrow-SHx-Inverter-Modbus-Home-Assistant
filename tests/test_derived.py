"""The arithmetic the YAML package did with templates.

These are the values a user sees rather than the registers behind them, so
they are checked against inputs chosen to make each formula legible. The
formulas are `modbus_sungrow.yaml`'s, not an improvement on them: a
replacement that computed something better would still be wrong, because the
number has to match what the entity showed yesterday.
"""

from __future__ import annotations

from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus import TIER_COMPONENTS, SungrowInverter
from sungrow_modbus.derived import RUNNING_STATES


def _int32(value: int) -> tuple[int, int]:
    """Return a signed 32-bit value as the two words Sungrow sends, low first."""
    raw = value & 0xFFFFFFFF
    return raw & 0xFFFF, raw >> 16


#: Registers scaled so the arithmetic is easy to follow: 400.0 V, 10.0 A, and
#: a 100 kWh pack held between 10 % and 90 %, half full, at 95 % health.
INPUT = {
    5010: 4000,  # MPPT1 voltage, x0.1
    5011: 100,  # MPPT1 current, x0.1
    5014: 0xFFFF,  # MPPT3 voltage: the "unavailable" sentinel
    5015: 0xFFFF,  # MPPT3 current
    5018: 2300,  # phase A voltage, x0.1
    13030: 200,  # phase A current, x0.1
    12999: 0x0040,  # running state: Running
    13000: 0x01 | 0x10,  # PV generating, exporting
    5213: 1500,  # battery power: positive is discharge
    13009: 2500,  # export power raw: positive is export
    13022: 500,  # battery level, x0.1
    5638: 10000,  # capacity high precision, x0.01 -> 100.0 kWh
    13023: 950,  # state of health, x0.1
    13001: 300,  # daily PV generation, x0.1 -> 30.0
    13044: 100,  # daily exported, x0.1 -> 10.0
    13035: 50,  # daily imported, x0.1 -> 5.0
    13039: 80,  # daily battery charge, x0.1 -> 8.0
    13025: 40,  # daily battery discharge, x0.1 -> 4.0
}
HOLDING = {13057: 900, 13058: 100}  # max SoC 90.0 %, min SoC 10.0 %


async def _inverter(overrides: dict[int, int] | None = None) -> SungrowInverter:
    """Return an inverter holding the values above, with any overrides.

    Overrides are raw register words, so a negative reading is written as its
    two's complement — which is how the inverter sends it.
    """
    unit = MockModbusConnection().for_unit(1)
    unit.input = {**INPUT, **(overrides or {})}
    unit.holding = dict(HOLDING)
    device = SungrowInverter(unit)
    for tier in TIER_COMPONENTS:
        await device.async_update_tier(tier)
    return device


@pytest.fixture
async def inverter() -> SungrowInverter:
    """Return the inverter every test below reads."""
    return await _inverter()


async def test_power_is_voltage_times_current(inverter: SungrowInverter) -> None:
    assert inverter.derived.mppt1_power == 4000  # 400.0 V x 10.0 A
    assert inverter.derived.phase_a_power == 4600  # 230.0 V x 20.0 A


async def test_an_unavailable_input_makes_the_value_unavailable(
    inverter: SungrowInverter,
) -> None:
    # MPPT3 answers 0xFFFF, which the specification defines as unavailable and
    # a two-tracker inverter returns permanently. The product must not become
    # a plausible number.
    assert inverter.derived.mppt3_power is None


async def test_the_running_state_is_decoded(inverter: SungrowInverter) -> None:
    assert inverter.derived.inverter_state == "Running"


async def test_an_unknown_running_state_is_reported_not_hidden() -> None:
    # A state Sungrow adds after this table was written has to be visible, or
    # nobody finds out it exists.
    assert 0x7FFE not in RUNNING_STATES
    device = await _inverter({12999: 0x7FFE})
    assert device.derived.inverter_state == "Unknown (0x7FFE)"


async def test_battery_flow_splits_by_sign(inverter: SungrowInverter) -> None:
    assert inverter.derived.battery_discharging_power == 1500
    assert inverter.derived.battery_charging_power == 0
    assert inverter.derived.battery_discharging_power_signed == 1500
    assert inverter.derived.battery_charging_power_signed == -1500


async def test_grid_flow_splits_by_sign(inverter: SungrowInverter) -> None:
    assert inverter.derived.export_power == 2500
    assert inverter.derived.import_power == 0


async def test_charging_reverses_both_splits() -> None:
    # Both are signed 32-bit, so a negative needs both words.
    battery_low, battery_high = _int32(-800)
    grid_low, grid_high = _int32(-1200)
    device = await _inverter(
        {
            5213: battery_low,
            5214: battery_high,
            13009: grid_low,
            13010: grid_high,
        }
    )
    assert device.derived.battery_charging_power == 800
    assert device.derived.battery_discharging_power == 0
    assert device.derived.import_power == 1200
    assert device.derived.export_power == 0


async def test_the_nominal_level_maps_onto_the_usable_range(
    inverter: SungrowInverter,
) -> None:
    # Half of the range between 10 % and 90 % is 50 % of the whole pack.
    assert inverter.derived.battery_level_nominal == 50.0


async def test_battery_energy_follows_the_soc_limits(
    inverter: SungrowInverter,
) -> None:
    # A 100 kWh pack held between 10 % and 90 % holds 80 kWh usable,
    assert inverter.derived.battery_charge == 80.0
    # discounted by 95 % state of health,
    assert inverter.derived.battery_charge_health_rated == 76.0
    # and half the pack nominally is 50 kWh.
    assert inverter.derived.battery_charge_nominal == 50.0


async def test_the_power_flow_flags_are_bits(inverter: SungrowInverter) -> None:
    assert inverter.derived.pv_generating is True
    assert inverter.derived.exporting_power is True
    assert inverter.derived.battery_charging is False
    assert inverter.derived.importing_power is False


async def test_consumption_is_generation_less_what_left(
    inverter: SungrowInverter,
) -> None:
    # 30 made, 10 exported, 5 imported, 8 stored, 4 released.
    assert inverter.derived.daily_consumed_energy == pytest.approx(21.0)
