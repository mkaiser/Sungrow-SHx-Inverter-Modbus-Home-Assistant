"""Which way this inverter's firmware writes register 13074, asked without changing it.

Register 13074, the export power limit, reads in watts everywhere it has been
measured. Its **write** side differs between firmwares:

* three houses (`.95.12` to `.95.14`) multiply the word they are handed by ten
  before storing it -- write 60, hold 600;
* fwitten's pair (`.95.03`) stores the word as handed -- write 60, hold 60.

`registers.AsymmetricNumberField` divides every write by ten, which is right at
the first three and sets a tenth of what was asked at the fourth. Nothing any
register reports tells the two apart. This asks the inverter instead.

**The probe changes nothing, on either firmware, by construction.** Two facts
make that possible: the multiply happens *before* the range check, and a
refused write leaves the register as it was. So write a word that is a no-op
under one reading and out of range under the other:

* **Probe A** writes the word the register already holds, `held`. Stored as
  handed it is a no-op. Multiplied it becomes `10 * held`, which this chooses
  only when that is above the maximum (and still out of range if the firmware
  wraps it to 16 bits), so the write is refused and nothing moves.
  Accepted means 1:1; refused means times ten.
* **Probe B** writes `held / 10`, when `held` is a multiple of ten. Multiplied
  it is `held` again, a no-op. Stored as handed it is `held / 10`, which this
  chooses only when that is below the minimum, so it is refused.
  Accepted means times ten; refused means 1:1.

At most one write is made. The answer comes from **whether the write was
refused**, not from a readback -- which matters, because a WiNet-S answers a
readback from a stale cache, while the refusal is the inverter's own reply.
Measured at bar12: a write the firmware multiplied out of range came back as
exception 0x04 through the dongle.

Where neither probe is safe, nothing is written and the answer is
`None`, with the reason. That is not rare. A zero-export house holds 0 with a
minimum of 0, where no word is refused under either reading. And while feed-in
limitation is **off** the register ignores every write without an exception,
so a refusal cannot happen and an acceptance means nothing; the probe needs
the mode on. Lifting it is a separate permission (`lift_mode`), granted only
where the limit already held is at least the inverter's maximum -- a cap that
high caps nothing, so switching it on curtails nobody.

The register is read once more afterwards, and if it moved -- which the
construction says it cannot -- it is put back by the raw word and the result
says so. A probe that a wrong model could leave a house changed by is the
thing the control test's restore rules exist to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from modbus_connection import (
    IllegalDataValueError,
    ModbusError,
    ServerDeviceFailureError,
)

from .addresses import Address, field_address

#: What a multiplying firmware does to a written word.
MULTIPLIER = 10

#: Feed-in limitation on, as register 13087 holds it. Off is 0x55, but the
#: probe never writes "off": it puts back whatever word it found.
MODE_ON = 0xAA

#: The refusals that mean "out of range". Measured as 0x04 at three houses;
#: 0x03 is what the specification says an illegal value should be, so both
#: are accepted. Any other exception -- 0x06 busy, above all -- settles
#: nothing.
OUT_OF_RANGE = (IllegalDataValueError, ServerDeviceFailureError)

LIMIT = field_address("export_power_limit")
MODE = field_address("export_power_limit_mode_raw")
MINIMUM = field_address("export_power_limit_min")
MAXIMUM = field_address("export_power_limit_max")

#: The bounds registers count in tens of watts; 13074 itself in watts.
BOUNDS_UNITS_PER_COUNT = 10


class Device(Protocol):
    """What the probe needs: `SungrowInverter` has both."""

    async def async_read(self, where: Address) -> list[int]:
        """Read one named block, raising on failure."""

    async def async_write_word(self, address: int, word: int) -> None:
        """Write one raw holding word, raising on failure."""


@dataclass(frozen=True)
class Plan:
    """The one word to write, and what each answer to it would mean."""

    word: int
    if_accepted: int
    """`write_units_per_count` if the write is accepted: 1 or 10."""
    if_refused: int
    """`write_units_per_count` if it is refused out of range."""
    why: str


@dataclass(frozen=True)
class Result:
    """What the probe found, and what it did to find it."""

    write_units_per_count: int | None
    """10 for a multiplying firmware, 1 for one that stores the word, None
    when the probe could not safely ask."""
    reason: str
    held: int | None = None
    wrote: int | None = None
    response: str | None = None
    mode_lifted: bool = False
    left_changed: bool = False
    """True only if the register moved and could not be put back. The one
    outcome that leaves a house different from how it was found."""


def choose(held: int, minimum: int, maximum: int) -> Plan | str:
    """Return the word that asks safely, or why there is none.

    Pure, so every case can be asserted without a device. Bounds are in
    watts, as `held` is.
    """
    if not minimum <= held <= maximum:
        return (
            f"the register holds {held} W, outside its own bounds "
            f"{minimum}-{maximum} W, so neither reading of a write can be trusted"
        )

    multiplied = held * MULTIPLIER
    wrapped = multiplied % 0x10000
    if not minimum <= multiplied <= maximum and not minimum <= wrapped <= maximum:
        return Plan(
            word=held,
            if_accepted=1,
            if_refused=MULTIPLIER,
            why=(
                f"writing the held {held} back is a no-op if stored as handed, "
                f"and {multiplied} W -- above the {maximum} W maximum -- if "
                "multiplied, which is refused"
            ),
        )

    if held % MULTIPLIER == 0 and held // MULTIPLIER < minimum:
        tenth = held // MULTIPLIER
        return Plan(
            word=tenth,
            if_accepted=MULTIPLIER,
            if_refused=1,
            why=(
                f"writing {tenth} is {held} again if multiplied, a no-op, and "
                f"{tenth} W -- below the {minimum} W minimum -- if stored as "
                "handed, which is refused"
            ),
        )

    return (
        f"at {held} W with bounds {minimum}-{maximum} W, every word that "
        "would tell the two firmwares apart is accepted by one of them as a "
        "new limit, so asking would change it"
    )


async def _word(device: Device, where: Address) -> int:
    """Read one register's raw word."""
    return (await device.async_read(where))[0]


async def async_probe(
    device: Device, *, lift_mode: bool = False, dry_run: bool = False
) -> Result:
    """Ask the inverter how it writes 13074, changing nothing.

    `lift_mode` permits switching feed-in limitation on for the one write, and
    only where the held limit is at least the maximum -- see the module
    docstring. It is put back to the word it held immediately afterwards.
    `dry_run` reads everything, chooses, and writes nothing.

    Raises only when the reads that decide whether to write fail: then nothing
    has been written, and the caller is owed the real error rather than a
    `None` that looks like a considered answer.
    """
    held = await _word(device, LIMIT)
    mode = await _word(device, MODE)
    minimum = await _word(device, MINIMUM) * BOUNDS_UNITS_PER_COUNT
    maximum = await _word(device, MAXIMUM) * BOUNDS_UNITS_PER_COUNT

    plan = choose(held, minimum, maximum)
    if isinstance(plan, str):
        return Result(None, plan, held=held)

    lift = False
    if mode != MODE_ON:
        if not lift_mode:
            return Result(
                None,
                f"feed-in limitation is off (13087 holds 0x{mode:02X}), and "
                "while it is off the register ignores every write without an "
                "exception, so no answer would mean anything",
                held=held,
            )
        if held < maximum:
            return Result(
                None,
                f"feed-in limitation is off, and switching it on would cap "
                f"export at the {held} W the register holds, below the "
                f"{maximum} W maximum -- that curtails a real house",
                held=held,
            )
        lift = True

    if dry_run:
        return Result(
            None,
            f"dry run: would write {plan.word}"
            + (" with feed-in limitation lifted" if lift else "")
            + f", because {plan.why}",
            held=held,
            wrote=None,
            mode_lifted=False,
        )

    if lift:
        await device.async_write_word(MODE.address, MODE_ON)
    try:
        response: str
        answer: int | None
        try:
            await device.async_write_word(LIMIT.address, plan.word)
        except OUT_OF_RANGE as err:
            response = f"refused, exception 0x{err.exception_code or 0:02X}"
            answer = plan.if_refused
        except ModbusError as err:
            response = f"{type(err).__name__}: {err}"
            answer = None
        else:
            response = "accepted"
            answer = plan.if_accepted
    finally:
        mode_back = not lift or await _restore_mode(device, mode)

    after = await _word(device, LIMIT)
    left_changed = not mode_back
    if after != held:
        left_changed = not await _put_back(device, held, after, plan.word)
        answer = None
        reason = (
            f"the register moved from {held} to {after}, which the construction "
            "says cannot happen, so this firmware is neither of the two known; "
            + ("it could not be put back" if left_changed else "it was put back")
        )
    elif not mode_back:
        answer = None
        reason = (
            f"feed-in limitation was switched on for the probe and could not be "
            f"put back to 0x{mode:02X}: the house is still capped at {held} W"
        )
    elif answer is None:
        reason = f"the write was answered with {response}, which settles nothing"
    else:
        kind = (
            "multiplies a written word by ten"
            if answer == MULTIPLIER
            else ("stores a written word as handed")
        )
        reason = f"this firmware {kind}: {response}, because {plan.why}"

    return Result(
        answer,
        reason,
        held=held,
        wrote=plan.word,
        response=response,
        mode_lifted=lift,
        left_changed=left_changed,
    )


async def _restore_mode(device: Device, mode: int) -> bool:
    """Put 13087 back to the word it held, and check it by reading.

    Twice, because while it is wrong the house is capped -- the one state of
    this probe that changes what a real installation does.
    """
    for _ in range(2):
        try:
            await device.async_write_word(MODE.address, mode)
            if await _word(device, MODE) == mode:
                return True
        except ModbusError:
            continue
    return False


async def _put_back(device: Device, held: int, now: int, wrote: int) -> bool:
    """Restore the held word, reading first, and say whether it is back.

    The factor is inferred from what the register did with the probe word --
    the one observation available -- and the write that would undo it under
    that factor is tried, then the raw word as a fallback. Checked by reading.
    """
    factor = now // wrote if wrote and now % wrote == 0 else 1
    candidates = [held // factor] if factor > 1 and held % factor == 0 else []
    candidates.append(held)
    for word in candidates:
        try:
            await device.async_write_word(LIMIT.address, word)
        except ModbusError:
            continue
        if await _word(device, LIMIT) == held:
            return True
    return False
