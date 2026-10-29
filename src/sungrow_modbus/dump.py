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

The standalone survey imports these bands, and the wallbox's, from here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
import time

from modbus_connection import ModbusError, ModbusExceptionError

from .model import SETTLES_NOTHING, Silent

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

#: A wallbox's own register space, on the unit that answered for it. Sungrow
#: publishes nothing for its AC wallboxes, so a document that said only "a
#: wallbox answered" would throw away the one chance to record what it holds.
#:
#: Measured on an AC22E-01 through a WiNet-S (`doc/wallbox_registers.md`):
#: input 21201-21280 and 21297-21340 answer, 21281-21296 refuse, and holding
#: answers 21201-21248 and scattered addresses up to 21328. Another model may
#: differ; a band that reads nothing costs one refused block and says so.
#:
#: The first band is cut at the firmware string (input 21226, ten registers)
#: so that it is read whole, in a request of its own. The wallbox answers a
#: read that starts inside a string with zeros for the rest of it: a 32-word
#: block ending at 21231 cut `LE-01.1E1.001.901.25` to `LE-01.1E1.001.`,
#: while the integration's own read of the field got all of it.
#: `tests/test_wallbox_registers.py` holds every string field to one block.
WALLBOX_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("input", 21200, 25, "identity, model, type code, phases"),
    ("input", 21225, 10, "the firmware string, read whole"),
    ("input", 21235, 45, "ratings"),
    ("input", 21296, 44, "the live measurements: state, power, energy"),
    ("holding", 21200, 50, "settings, as far as they answer"),
    ("holding", 21297, 32, "the scattered upper settings"),
)

#: The same wallbox read at its **own address**, over TLS (port 516, unit
#: 248), where a read must **start on a data point's first register** or it
#: times out -- a WiNet-S answers any start, so `WALLBOX_BANDS` cannot be used
#: there. Each band is one read (none is longer than `BLOCK`), starting on a
#: start measured on an AC22E-01 and spanning whole data points up to 32
#: registers; all twelve answered on that unit. Holding 21249-21312 answers
#: here where no read through the dongle reached it.
WALLBOX_TLS_BANDS: tuple[tuple[str, int, int, str], ...] = (
    ("input", 21200, 25, "identity, model, type code, phases"),
    ("input", 21225, 18, "the firmware string, read whole, and a second version"),
    ("input", 21243, 32, "ratings and phase mode"),
    ("input", 21275, 32, "the live measurements, first half"),
    ("input", 21307, 32, "the live measurements, second half"),
    ("input", 21339, 30, "above the live block"),
    ("input", 21369, 9, "the last answering data points"),
    ("holding", 21200, 32, "settings"),
    ("holding", 21232, 17, "settings, and the clock"),
    ("holding", 21249, 32, "the upper settings, first half"),
    ("holding", 21281, 32, "the upper settings, second half"),
    ("holding", 21313, 8, "the last answering settings"),
)

#: The wallbox's serial, input 21201-21206, first -- `wallbox.SERIAL_*` reads
#: its position from that entry. A serial like any other, and as easily
#: published by accident as raw words.
#:
#: Then input 21211-21214: a short code the wallbox answers only at its own
#: address (a WiNet-S answers 0 there). One unit has been read, so whether it
#: is the same on every AC22E-01 or tells one apart is unknown -- and until a
#: second wallbox says which, it is treated as the serial is.
#:
#: Then holding 21250-21259: twenty ASCII digits, constant across readings a
#: fortnight apart, only at the wallbox's own address. Undecoded, and shaped
#: like an identifier -- a charge point or card number -- so it is treated
#: as one until something says otherwise.
WALLBOX_MASKED: tuple[tuple[str, int, int], ...] = (
    ("input", 21200, 6),
    ("input", 21210, 4),
    ("holding", 21249, 10),
)

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

#: Called before each single-address read of a failed block, with (the
#: address, which of the block's addresses it is, the block's size). A
#: fallback can wait out a timeout per address, so a caller drawing progress
#: needs to say which register it is waiting on, or the run looks hung.
Narrowing = Callable[[int, int, int], None]


def block_count(
    bands: tuple[tuple[str, int, int, str], ...] = DUMP_BANDS, block: int = BLOCK
) -> int:
    """How many requests a dump of these bands will make, before failures.

    Needed *before* the dump runs: a progress bar whose denominator grows
    halfway through is worse than none, and the caller has to add this to its
    own total.
    """
    return sum(len(range(0, count, block)) for _space, _start, count, _why in bands)


def _note_skipped(
    skipped: list[str],
    space: str,
    start: int,
    count: int,
    why: str,
    offset: int,
) -> None:
    """Record a band the budget cut short, distinguishing partly from not at all.

    The distinction is the point. A band that was never reached tells a reader
    nothing about the firmware; a band that was *part* read has real addresses
    in the dump and a boundary that is an artefact of the clock rather than of
    the device. Publishing the second as though it were complete is how an
    absent register gets inferred from a timeout, which `bands_not_reached`
    exists to stop.
    """
    label = f"{space} {start}+{count} ({why})"
    if label not in skipped:
        skipped.append(label if not offset else f"{label}, part read")


async def _async_narrow(
    read: Read,
    space: str,
    address: int,
    size: int,
    into: dict[str, int | None],
    on_narrow: Narrowing | None = None,
    silent: Silent | None = None,
) -> None:
    """Read a failed block one address at a time, recording what each one says.

    A block fails as a whole, and a whole block recorded as absent is a map
    with a hole in it: one refused address in a block of 32 would hide the 31
    that answer, and the point of a dump is exactly which addresses this
    firmware has.

    One attempt each, deliberately. The retry that the block read gets is there
    for a link that dropped; here, a refusal is the answer -- an inverter that
    does not have a register says so in milliseconds -- and retrying 32 of them
    on a slow link costs minutes to learn nothing. An address that fails is
    recorded as `None`, which is a reading of "asked, and it would not say",
    not a gap. An address `silent` already knows timed out is recorded so
    without asking again.
    """
    for number, single in enumerate(range(address, address + size), 1):
        if silent is not None and silent.covers(space, single, 1):
            into[str(single)] = None
            continue
        if on_narrow is not None:
            on_narrow(single, number, size)
        try:
            value = await read(space, single, 1)
        except TimeoutError:
            into[str(single)] = None
            if silent is not None:
                silent.note(space, single, 1)
        except (ModbusError, OSError):
            into[str(single)] = None
        else:
            into[str(single)] = value[0]


async def async_dump(
    read: Read,
    *,
    on_progress: Progress | None = None,
    on_narrow: Narrowing | None = None,
    budget: float = BUDGET,
    block: int = BLOCK,
    bands: tuple[tuple[str, int, int, str], ...] = DUMP_BANDS,
    silent: Silent | None = None,
) -> dict[str, dict[str, int | None] | list[str]]:
    """Read every band raw, one small block at a time.

    Returns `{"input": {address: word or None}, "holding": {...}}` keyed by
    address as a string, which is the shape every published document already
    uses, plus `bands_not_reached` when the budget ran out.

    **A refused address is not retried.** Refusal is the expected answer over
    most of these bands, and retrying each one with a pause between attempts
    turns a few hundred reserved addresses into a run long enough to be
    killed. A dropped *block* is retried, because that is the case where the
    address might have answered; a refused one goes straight to the
    single-address fallback. With
    `silent`, the single-address fallback waits on each quiet register once
    across the whole run, not once per read that touches it.
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
                _note_skipped(skipped, space, start, count, why, offset)
                for _ in range(offset, count, block):
                    step("out of budget")
                break
            size = min(block, count - offset)
            address = start + offset
            step(why)
            try:
                words = await _async_read_retrying(read, space, address, size)
            except (ModbusError, TimeoutError, OSError):
                await _async_narrow(read, space, address, size, into, on_narrow, silent)
                continue
            for index, word in enumerate(words):
                into[str(address + index)] = word
    if skipped:
        dump["bands_not_reached"] = skipped
    return dump


def masked(
    dump: dict[str, dict[str, int | None] | list[str]],
    mask: tuple[tuple[str, int, int], ...] = DUMP_MASKED,
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


def answered(dump: Mapping[str, object]) -> int:
    """Count the addresses in a dump that answered with a word.

    A masked address counts as unanswered, which is what a published dump
    says about it; `bands_not_reached` is a list and holds no words.
    """
    return sum(
        1
        for band in dump.values()
        if isinstance(band, dict)
        for word in band.values()
        if word is not None
    )


async def _async_read_retrying(
    read: Read, space: str, address: int, count: int, attempts: int = 2
) -> list[int]:
    """Read one block, retrying a dropped link before giving up.

    A dropped block is not evidence about the registers in it: on a device
    that accepts very few Modbus sessions, another client polling at the same
    moment produces exactly the same failure as a register that is not there.
    An exception *response* is the device answering, so it is raised at once
    -- except what `model.SETTLES_NOTHING` names, which settles nothing.
    """
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return list(await read(space, address, count))
        except ModbusExceptionError as err:
            if not isinstance(err, SETTLES_NOTHING) or attempt >= attempts:
                raise
            await asyncio.sleep(1.5)
        except (ModbusError, TimeoutError, OSError):
            if attempt >= attempts:
                raise
            await asyncio.sleep(1.5)
    raise AssertionError("unreachable")
