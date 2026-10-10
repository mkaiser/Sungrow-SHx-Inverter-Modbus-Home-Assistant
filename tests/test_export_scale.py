"""Asking an inverter how it writes 13074, without changing what it holds.

The probe in `sungrow_modbus.export_scale` makes one write to a real house's
export limit. The claim that makes that acceptable is that the write is a
no-op on one firmware and refused on the other, so **nothing changes on
either**. That claim is what is tested hardest here: against a fake inverter
that does what the measured firmwares do, over every held value and bound in a
grid, on both firmwares and with and without 16-bit wrapping.

The fake is built from measurements, not from the probe's own reasoning:

* a multiplying firmware multiplies **before** the range check (3400 became
  34000 and was refused at the reference house, 2026-09-19);
* a refusal is exception 0x04 and leaves the register as it was;
* with feed-in limitation off (0x55) the register ignores writes with no
  exception at all;
* through a WiNet-S a readback is a stale cache, so only the refusal can be
  trusted (gerd, 2026-09-19).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import itertools

from modbus_connection import ServerDeviceBusyError, ServerDeviceFailureError
import pytest

from sungrow_modbus.addresses import Address
from sungrow_modbus.export_scale import (
    LIMIT,
    MAXIMUM,
    MINIMUM,
    MODE,
    MODE_ON,
    MULTIPLIER,
    Plan,
    async_probe,
    choose,
)

OFF = 0x55


@dataclass
class Inverter:
    """Register 13074 and its neighbours, as the two measured firmwares behave."""

    multiplies: bool
    held: int
    minimum: int
    maximum: int
    mode: int = MODE_ON
    wraps: bool = False
    """Multiply in 16 bits, as a firmware might."""
    stale: bool = False
    """Answer reads from a cache, as a WiNet-S does."""
    busy: bool = False
    writes: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Remember what the probe found, to check it is still there after."""
        self.found = (self.held, self.mode)

    async def async_read(self, where: Address) -> list[int]:
        """Answer the four registers the probe reads, stale if a dongle."""
        if where == LIMIT:
            return [self.found[0] if self.stale else self.held]
        if where == MODE:
            return [self.found[1] if self.stale else self.mode]
        if where == MINIMUM:
            return [self.minimum // 10]
        if where == MAXIMUM:
            return [self.maximum // 10]
        raise AssertionError(f"unexpected read {where}")

    async def async_write_word(self, address: int, word: int) -> None:
        """Store, multiply, refuse or ignore, as the measured firmwares do."""
        self.writes.append((address, word))
        if self.busy:
            raise ServerDeviceBusyError
        if address == MODE.address:
            self.mode = word
            return
        assert address == LIMIT.address
        if self.mode != MODE_ON:
            return  # ignored, and silently
        stored = word * MULTIPLIER if self.multiplies else word
        if self.wraps:
            stored %= 0x10000
        if not self.minimum <= stored <= self.maximum:
            raise ServerDeviceFailureError
        self.held = stored

    @property
    def unchanged(self) -> bool:
        """Whether the limit and the mode both hold what they held."""
        return (self.held, self.mode) == self.found


# -- the houses this was measured at ---------------------------------------


@pytest.mark.parametrize(
    ("house", "inverter", "lift", "expected"),
    [
        # Limitation off, limit at the maximum: lifting caps nothing.
        ("reference", Inverter(True, 10000, 0, 10000, OFF), True, 10),
        ("bar12", Inverter(True, 10000, 0, 10000, OFF), True, 10),
        ("gerd", Inverter(True, 8000, 0, 8000, OFF), True, 10),
        # Limitation on, 1:1, cluster-sized bounds.
        ("fwitten master", Inverter(False, 24990, 11880, 24990), False, 1),
        ("fwitten slave", Inverter(False, 11880, 11880, 24990), False, 1),
    ],
)
async def test_each_measured_house_gets_its_measured_answer(
    house, inverter, lift, expected
) -> None:
    """Each answer matches what part B measured there by writing for real."""
    result = await async_probe(inverter, lift_mode=lift)

    assert result.write_units_per_count == expected, (house, result.reason)
    assert inverter.unchanged, house
    assert not result.left_changed


async def test_a_zero_export_house_is_not_asked() -> None:
    """jm493: 0 W held, 0 W minimum -- no word is refused by either firmware."""
    inverter = Inverter(True, 0, 0, 15000)
    result = await async_probe(inverter)

    assert result.write_units_per_count is None
    assert inverter.writes == []


async def test_with_limitation_off_it_asks_only_with_leave_to_lift() -> None:
    """Off, every write is ignored without an exception: no answer means anything."""
    inverter = Inverter(True, 10000, 0, 10000, OFF)
    result = await async_probe(inverter)

    assert result.write_units_per_count is None
    assert "off" in result.reason
    assert inverter.writes == []


async def test_it_never_lifts_the_mode_under_a_limit_that_would_bite() -> None:
    """Switching it on with 3000 held would cap a 10 kW house at 3 kW."""
    inverter = Inverter(True, 3000, 0, 10000, OFF)
    result = await async_probe(inverter, lift_mode=True)

    assert result.write_units_per_count is None
    assert "curtails" in result.reason
    assert inverter.writes == []


async def test_a_lifted_mode_goes_back_to_the_word_it_held() -> None:
    """Back to the found word, not to a named "off"."""
    inverter = Inverter(True, 10000, 0, 10000, mode=0x57)
    await async_probe(inverter, lift_mode=True)

    assert inverter.mode == 0x57
    assert inverter.writes[0] == (MODE.address, MODE_ON)
    assert inverter.writes[-1] == (MODE.address, 0x57)


async def test_a_dry_run_reads_and_writes_nothing() -> None:
    inverter = Inverter(True, 10000, 0, 10000, OFF)
    result = await async_probe(inverter, lift_mode=True, dry_run=True)

    assert inverter.writes == []
    assert result.reason.startswith("dry run: would write 10000")


async def test_the_answer_survives_a_dongle_s_stale_readback() -> None:
    """Decided by the refusal, which is the inverter's own reply."""
    inverter = Inverter(True, 10000, 0, 10000, stale=True)
    result = await async_probe(inverter)

    assert result.write_units_per_count == 10


async def test_a_busy_device_settles_nothing() -> None:
    """0x06 is "ask me later", not "out of range"."""
    inverter = Inverter(True, 10000, 0, 10000, busy=True)
    result = await async_probe(inverter)

    assert result.write_units_per_count is None
    assert inverter.held == 10000


# -- the claim the whole probe rests on ----------------------------------------

HELD = range(0, 30001, 1990)
BOUNDS = [(0, 5000), (0, 10000), (0, 15000), (0, 24990), (11880, 24990), (0, 60000)]


@pytest.mark.parametrize(
    ("multiplies", "wraps"), [(True, False), (True, True), (False, False)]
)
async def test_it_never_changes_the_register_and_is_never_wrong(
    multiplies, wraps
) -> None:
    """Every held value and bound in the grid, mode on, on each firmware.

    Either it answers correctly, or it does not answer -- and in both cases
    the register holds what it held. A probe that is right only where it was
    expected to be asked is not the claim; this is.
    """
    expected = MULTIPLIER if multiplies else 1
    for held, (minimum, maximum) in itertools.product(HELD, BOUNDS):
        if not minimum <= held <= maximum:
            continue
        inverter = Inverter(multiplies, held, minimum, maximum, wraps=wraps)
        result = await async_probe(inverter)

        where = (held, minimum, maximum)
        assert inverter.unchanged, where
        assert not result.left_changed, where
        assert result.write_units_per_count in (None, expected), where


def test_it_asks_at_the_settings_most_houses_have() -> None:
    """A limit at the maximum -- "no limit" -- is the common case, and askable."""
    for maximum in (5000, 8000, 10000, 15000, 24990):
        assert isinstance(choose(maximum, 0, maximum), Plan), maximum
