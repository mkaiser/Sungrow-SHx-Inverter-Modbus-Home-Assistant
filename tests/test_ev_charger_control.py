"""The inverter's EV charger block, held to what gerd's inverter did on 2026-11-14."""

from __future__ import annotations

import asyncio

from modbus_connection.mock import MockModbusConnection
import pytest

from sungrow_modbus.hybrid_inverter import ev_charger as ev


def test_the_protocol_addresses_are_the_ones_written_on_site() -> None:
    """The writes that worked went to protocol 33539, 33540, 33544 and 33549."""
    assert (ev.CHARGING, ev.MODE, ev.USER_CURRENT, ev.GRID_SURPLUS) == (
        33539,
        33540,
        33544,
        33549,
    )
    fields = ev.EvChargerControl.declared_fields
    assert fields["charging_raw"].address == ev.CHARGING
    assert fields["mode_raw"].address == ev.MODE
    assert fields["user_current"].address == ev.USER_CURRENT
    assert fields["grid_surplus_raw"].address == ev.GRID_SURPLUS


def test_the_block_decodes_what_was_read() -> None:
    """13:17, user defined at 10 A, charging: 170, 163, 0, 0, 0, 100 ... 85."""
    words = [170, 163, 0, 0, 0, 100, 0, 0, 0, 0, 85]
    unit = MockModbusConnection().for_unit(1)
    unit.holding = {ev.CHARGING + i: word for i, word in enumerate(words)}
    block = ev.EvChargerControl(unit)
    asyncio.run(block.async_update())

    assert block.charging is True
    assert block.mode == "user_defined"
    assert block.user_current == pytest.approx(10.0)
    assert block.grid_surplus_raw == ev.OFF


@pytest.mark.parametrize(
    ("amps", "word"), [(6.0, 60), (8.0, 80), (10.0, 100), (12.0, 120), (32.0, 320)]
)
def test_a_current_inside_the_range_is_written_at_a_tenth_of_an_ampere(
    amps: float, word: int
) -> None:
    assert ev.user_current_word(amps, 32.0) == word


@pytest.mark.parametrize("amps", [5.0, 0.0, 33.0])
def test_a_current_outside_six_amperes_to_the_rating_is_never_written(
    amps: float,
) -> None:
    """5 A was refused by the inverter; 33 A it took, so the cap is ours."""
    with pytest.raises(ValueError):
        ev.user_current_word(amps, 32.0)


def test_the_current_is_written_only_in_user_defined_mode() -> None:
    """In fast charge the inverter refused every write, with exception 0x04."""
    assert ev.current_writes(8.0, mode_raw=ev.USER_DEFINED, rating_a=32.0) == [
        (ev.USER_CURRENT, 80)
    ]
    for mode in (ev.FAST, ev.PV_SURPLUS, 0):
        with pytest.raises(ValueError):
            ev.current_writes(8.0, mode_raw=mode, rating_a=32.0)


def test_a_mode_that_ends_the_session_is_followed_by_charging_on() -> None:
    """User defined to fast charge ended the session; charging on started it again."""
    assert ev.mode_writes(ev.FAST, charge=True) == [
        (ev.MODE, ev.FAST),
        (ev.CHARGING, ev.ON),
    ]
    assert ev.mode_writes(ev.PV_SURPLUS, charge=True)[-1] == (ev.CHARGING, ev.ON)
    assert ev.mode_writes(ev.FAST, charge=False) == [(ev.MODE, ev.FAST)]


def test_user_defined_mode_switches_charging_on_by_itself() -> None:
    assert ev.mode_writes(ev.USER_DEFINED, charge=True) == [(ev.MODE, ev.USER_DEFINED)]


def test_an_unknown_mode_is_never_written() -> None:
    with pytest.raises(ValueError):
        ev.mode_writes(164, charge=True)


def test_start_and_stop_are_the_on_and_off_words() -> None:
    assert ev.charging_writes(True) == [(ev.CHARGING, 0xAA)]
    assert ev.charging_writes(False) == [(ev.CHARGING, 0x55)]


@pytest.mark.parametrize(
    ("mode", "managed"),
    [(160, True), (161, True), (163, True), (0, None), (None, None), (9999, None)],
)
def test_a_managed_wallbox_is_told_only_by_a_named_mode(
    mode: int | None, managed: bool | None
) -> None:
    """What an inverter without a wallbox reads here is not measured."""
    assert ev.manages_a_wallbox(mode) is managed
