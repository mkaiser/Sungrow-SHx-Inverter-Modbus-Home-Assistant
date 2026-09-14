"""What the band sweep does when a read fails, which is most of the time.

Over these bands a refusal is the *normal* answer -- they are mostly
"Reserved" -- so the failure paths are not edge cases here, they are the bulk
of the work. Driven through a fake read function rather than a mock inverter
because what is under test is the loop: how a failed block is retried, when it
falls back to reading singly, and what the budget does when it runs out.
"""

from collections.abc import Generator
from unittest.mock import patch

from modbus_connection import ModbusError
import pytest

from sungrow_modbus.dump import async_dump, block_count, masked

#: One band of 40 addresses, two blocks of 32 and 8. Small enough to read in
#: the head, which the real twelve are not.
BANDS = (("input", 100, 40, "a band to test with"),)


@pytest.fixture(autouse=True)
def no_waiting() -> Generator[None]:
    """Skip the retry pause, which is 1.5s and correct but slow in a test."""
    with patch("sungrow_modbus.dump.asyncio.sleep"):
        yield


async def test_a_band_that_answers_is_recorded_address_by_address() -> None:
    """Keyed by protocol address as a string, which is the document's shape."""

    async def read(space: str, address: int, count: int) -> list[int]:
        return [address + offset for offset in range(count)]

    dump = await async_dump(read, bands=BANDS)

    assert list(dump) == ["input"]
    assert len(dump["input"]) == 40
    assert dump["input"]["100"] == 100
    assert dump["input"]["139"] == 139


async def test_one_bad_address_does_not_lose_the_block_around_it() -> None:
    """The whole reason the blocks are small and the fallback exists.

    A block of 32 containing one address the inverter will not answer would
    otherwise be recorded as 32 unknowns, which says nothing about the 31 that
    do answer. That is the difference between a dump and a map.
    """
    refused = 117

    async def read(space: str, address: int, count: int) -> list[int]:
        if address <= refused < address + count:
            raise ModbusError("illegal data address")
        return [address + offset for offset in range(count)]

    dump = await async_dump(read, bands=BANDS)

    assert dump["input"][str(refused)] is None
    assert dump["input"]["116"] == 116
    assert dump["input"]["118"] == 118
    assert sum(1 for value in dump["input"].values() if value is None) == 1


async def test_a_dropped_block_is_retried_before_it_is_believed() -> None:
    """A drop is not evidence about the registers in it.

    On a device that grants very few sessions, another client polling at the
    same moment produces exactly the failure an absent register does. So a
    block gets a second attempt, and a block that answers on it is not
    degraded to single reads.
    """
    attempts: list[tuple[int, int]] = []

    async def read(space: str, address: int, count: int) -> list[int]:
        attempts.append((address, count))
        if len(attempts) == 1:
            raise TimeoutError("the link dropped")
        return [0] * count

    dump = await async_dump(read, bands=BANDS)

    # First block: failed, retried, answered as a block -- so the second call
    # asks for the same 32 rather than for one register.
    assert attempts[0] == (100, 32)
    assert attempts[1] == (100, 32)
    assert len(dump["input"]) == 40


async def test_the_budget_says_which_bands_it_never_reached() -> None:
    """Rather than leaving a short dump that looks complete.

    A document whose dump quietly stops at band four is worse than one that
    says it stopped: the missing addresses read as refusals, and refusals are
    what this project changes `scripts/layout.py` from.
    """

    async def read(space: str, address: int, count: int) -> list[int]:
        return [0] * count

    with patch("sungrow_modbus.dump.time.perf_counter", side_effect=range(1000)):
        dump = await async_dump(read, bands=BANDS, budget=0)

    assert dump["bands_not_reached"] == ["input 100+40 (a band to test with)"]


async def test_progress_is_reported_once_per_block_including_skipped_ones() -> None:
    """So a bar cannot stall on a band the budget cut, or overrun its total."""
    seen: list[tuple[int, int, str]] = []

    async def read(space: str, address: int, count: int) -> list[int]:
        return [0] * count

    await async_dump(read, bands=BANDS, on_progress=lambda *args: seen.append(args))

    assert len(seen) == block_count(BANDS) == 2
    assert [done for done, _total, _why in seen] == [1, 2]
    assert {total for _done, total, _why in seen} == {2}


def test_masking_blanks_rather_than_removes() -> None:
    """Absent and refused are different claims about a register."""
    dump = {"input": {"4989": 0x4131, "4990": 0x3233, "5000": 7}}

    out = masked(dump, mask=(("input", 4989, 2),))

    assert out["input"] == {"4989": None, "4990": None, "5000": 7}
    # And the original is untouched, so a caller can still use what it read.
    assert dump["input"]["4989"] == 0x4131
