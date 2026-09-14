"""Reading whole address bands raw, including the addresses nothing maps.

The rest of this library reads *fields*: an address it can name, decoded into
a value with a unit. A dump is the opposite and exists for the opposite
reason -- it reads neighbourhoods, keeps whatever comes back as a raw word,
and is most interesting exactly where no field is declared. Every register
this project knows about that Sungrow never documented was found this way.

Bands rather than the whole space. A blind sweep of 0-40000 is tens of
thousands of reads, almost all of them "Reserved", and each one is a chance
to drop a link on a device that grants very few sessions. `DUMP_BANDS` is the
set of neighbourhoods the specification and the YAML package actually use,
plus the ones that turned out to hold real values anyway.

**The cost is the whole design problem here.** An unmapped address on a
Sungrow does not refuse in milliseconds -- it goes quiet, and the read waits
out its full timeout. A measured SH10RT takes about 300 seconds to read these
1510 addresses for that reason, not because the bytes are slow. So this is
bounded by a budget, reports which bands it never reached rather than
pretending it covered them, and belongs behind a switch that is off.

`scripts/sungrow_scan/probe.py` carries the same bands for the standalone
survey, which has to run from a zip with this library absent.
`tests/test_dump_bands.py` asserts the two have not drifted.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import time

from modbus_connection import ModbusError

#: Address bands worth dumping raw, with why each is here. Protocol
#: addresses, so one below the register number in Sungrow's document.
DUMP_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("input", 2580, 80, "the 26xx firmware strings"),
    ("input", 4949, 210, "identity, firmware, AC and DC basics"),
    ("input", 5600, 160, "meter and battery"),
    ("input", 6099, 100, "the block a WiNet-S does not forward"),
    ("input", 10740, 60, "an SBR's own registers, when it answers here"),
    ("input", 12999, 110, "the 13xxx measurements"),
    ("input", 13199, 160, "meter channel 2 and the firmware block"),
    ("holding", 4999, 60, "holding-side identity"),
    ("holding", 12999, 110, "the 13xxx settings"),
    ("holding", 31200, 60, "the active-power-limit block"),
    ("input", 33000, 200, "undocumented, and known to hold real values"),
    ("holding", 33000, 200, "battery power limits and start thresholds"),
)

#: Never published raw, whatever band covers it: the serial number's ten
#: registers. A document carries a stand-in precisely so the real serial
#: stays out of it, and a raw dump would hand it over in words instead of
#: characters. Applied by `masked`, which every caller runs before publishing.
DUMP_MASKED: tuple[tuple[str, int, int], ...] = (("input", 4989, 10),)

#: Reads per request. Small, because the point is coverage: a band that fails
#: as a whole tells nobody anything, where a band with eight addresses missing
#: from the middle is a map of what this firmware answers.
BLOCK = 32

#: Seconds the whole dump may take before it starts marking bands unreached.
#: Twice the 300 seconds a reference SH10RT measured, so an ordinary run
#: finishes and a pathological one still ends.
BUDGET = 600.0

#: `async_read_words(space, address, count)` -- the seam `SungrowInverter`
#: offers, and the only thing this module needs from a device.
Read = Callable[[str, int, int], Awaitable[list[int]]]

#: Called after each block with (blocks done, blocks total, what it is on).
#: The count is blocks and not addresses, because a block that falls back to
#: single reads does not change how far through the bands we are.
Progress = Callable[[int, int, str], None]


def block_count(bands: tuple = DUMP_BANDS, block: int = BLOCK) -> int:
    """How many requests a dump of these bands will make, before failures.

    Needed *before* the dump runs: a progress bar whose denominator grows
    halfway through is worse than none, and the caller has to add this to its
    own total.
    """
    return sum(len(range(0, count, block)) for _space, _start, count, _why in bands)


async def async_dump(
    read: Read,
    *,
    on_progress: Progress | None = None,
    budget: float = BUDGET,
    block: int = BLOCK,
    bands: tuple = DUMP_BANDS,
) -> dict[str, dict[str, int | None] | list[str]]:
    """Read every band raw, one small block at a time.

    Returns `{"input": {address: word or None}, "holding": {...}}` keyed by
    address as a string, which is the shape every published document already
    uses, plus `bands_not_reached` when the budget ran out.

    **A refused address is not retried.** Refusal is the expected answer over
    most of these bands, and the first version of this retried each one with a
    pause between attempts, which turned a few hundred reserved addresses into
    a run long enough to be killed. A dropped *block* is still retried,
    because that is the case where the address might have answered.
    """
    dump: dict[str, dict[str, int | None] | list[str]] = {}
    skipped: list[str] = []
    started = time.perf_counter()
    total = block_count(bands, block)
    done = 0

    def step(note: str) -> None:
        nonlocal done
        done += 1
        if on_progress is not None:
            on_progress(done, total, note)

    for space, start, count, why in bands:
        into: dict[str, int | None] = dump.setdefault(space, {})  # type: ignore[assignment]
        for offset in range(0, count, block):
            # Checked per block and not only per band: on the reference
            # SH10RT one 80-address band spent minutes alone, because that
            # inverter goes quiet rather than refusing and every read waits
            # out its own timeout. A per-band check cannot interrupt the band
            # it is already inside, which is the opposite of what a budget is
            # for.
            if time.perf_counter() - started > budget:
                label = f"{space} {start}+{count} ({why})"
                if label not in skipped:
                    skipped.append(label if not offset else f"{label}, part read")
                for _ in range(offset, count, block):
                    step("out of budget")
                break
            size = min(block, count - offset)
            address = start + offset
            step(why)
            try:
                words = await _async_read_retrying(read, space, address, size)
            except (ModbusError, TimeoutError, OSError):
                # Down to single reads, one attempt each: one refused address
                # in a block of 32 would otherwise hide the 31 that answer.
                for single in range(address, address + size):
                    try:
                        value = await read(space, single, 1)
                    except (ModbusError, TimeoutError, OSError):
                        into[str(single)] = None
                    else:
                        into[str(single)] = value[0]
                continue
            for index, word in enumerate(words):
                into[str(address + index)] = word
    if skipped:
        dump["bands_not_reached"] = skipped
    return dump


def masked(
    dump: dict[str, dict[str, int | None] | list[str]],
    mask: tuple = DUMP_MASKED,
) -> dict[str, dict[str, int | None] | list[str]]:
    """Return the dump with the masked addresses blanked rather than removed.

    Blanked, because *absent* and *refused* are different claims and a reader
    cannot tell them apart once an address is gone. The mask is a parameter
    because there is more than one serial in a house: the inverter's at input
    4990, and a wallbox's at input 21201 on its own unit.
    """
    out: dict[str, dict[str, int | None] | list[str]] = {
        space: (dict(values) if isinstance(values, dict) else list(values))
        for space, values in dump.items()
    }
    for space, start, count in mask:
        values = out.get(space)
        if not isinstance(values, dict):
            continue
        for address in range(start, start + count):
            if str(address) in values:
                values[str(address)] = None
    return out


async def _async_read_retrying(
    read: Read, space: str, address: int, count: int, attempts: int = 2
) -> list[int]:
    """Read one block, retrying a dropped link before giving up.

    A dropped block is not evidence about the registers in it: on a device
    that accepts very few Modbus sessions, another client polling at the same
    moment produces exactly the same failure as a register that is not there.
    """
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return list(await read(space, address, count))
        except (ModbusError, TimeoutError, OSError):
            if attempt >= attempts:
                raise
            await asyncio.sleep(1.5)
    raise AssertionError("unreachable")
