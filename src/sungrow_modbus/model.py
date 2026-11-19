"""Shared result types for a device update."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import logging
from typing import Any, Literal

from modbus_connection import (
    ModbusError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)
from modbus_connection.model import NumberField, StringField

_LOGGER = logging.getLogger(__name__)

#: Exception responses that are answers but settle nothing about a register.
#: 0x06 says "ask me later". 0x04 does too through a busy WiNet-S: gerd's
#: answered three holding blocks 18 times of 18 to one client and refused
#: about half of the same reads with 0x04 while three clients asked at once,
#: twice over (2026-10-29), and firetribe's did the same with two other
#: pollers on it. So a probe retries these and never records them as "not
#: there"; a write refused with one is still a refusal of that write.
SETTLES_NOTHING: tuple[type[ModbusError], ...] = (
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)


@dataclass(frozen=True)
class UpdateReport:
    """Which components refreshed in one poll, and why the rest did not.

    A Sungrow inverter answers a different subset of its register map
    depending on model, firmware and what is wired up: a SH10RT returns
    0xFFFF for MPPT3/4, and the battery blocks are absent entirely without
    storage. A poll that loses one block is therefore normal operation, not a
    failure of the whole device, so each component reports separately and
    callers decide what an unanswered component means.
    """

    updated: frozenset[str] = frozenset()
    failed: dict[str, ModbusError] = field(default_factory=dict)

    def __or__(self, other: UpdateReport) -> UpdateReport:
        """Merge two reports, so a device can poll in several passes."""
        return UpdateReport(
            updated=(self.updated | other.updated) - other.failed.keys(),
            failed={**self.failed, **other.failed},
        )


#: What a decoded register can actually be.
#:
#: Stated once so that `field()` and `present()` do not have to say `object`
#: and leave every caller to launder it. No field in this map declares an
#: `enum_type` or a `convert`, so these four are the whole set; an IntEnum
#: would be covered by `int` anyway.
RegisterValue = float | int | str | None


def words_text(words: Iterable[int], encoding: str = "ascii") -> str:
    """Decode raw register words as text, high byte first, up to the first NUL.

    Sungrow pads a string field with 0x00, and the first NUL ends the text:
    an SH6.0RS on SUNSTONE-H answers its battery firmware as
    `SBRBCU-S_22011.01.30`, a NUL, and then `44` left over from a longer
    string, which stripping only the ends kept. Anything undecodable is
    replaced rather than raised, because a reading with one odd byte is still
    a reading. Whitespace is the caller's to strip: a serial's exact text is
    what its stand-in is hashed from.
    """
    raw = b"".join(int(word).to_bytes(2, "big") for word in words)
    return raw.lstrip(b"\x00").split(b"\x00", 1)[0].decode(encoding, "replace")


class TextField(StringField):
    """A Sungrow string register: the text before the first NUL.

    `modbus_connection`'s own string strips only trailing NULs, which keeps
    whatever a firmware left after its terminator -- invisible in a log, and
    enough to make a firmware string match nothing it is compared against.

    `word_order="little"` reads the words last first, as a U32 is read low
    word first: an iHomeManager sends its protocol number "AW0" as
    `0x3000 0x4157` (SV930.001.00.P020, 2026-11-10).
    """

    def __init__(
        self,
        address: int,
        *,
        word_order: Literal["big", "little"] = "big",
        **kwargs: Any,
    ) -> None:
        """Declare the field; `kwargs` go to `RegisterField`."""
        super().__init__(address, **kwargs)
        self.word_order = word_order

    def decode(self, words: list[int], scale_exponent: int | None = None) -> str:
        """Return the text before the first NUL, as ASCII, dropping odd bytes."""
        if self.word_order == "little":
            words = list(reversed(words))
        raw = b"".join((word & 0xFFFF).to_bytes(2, "big") for word in words)
        text = raw.lstrip(b"\x00").split(b"\x00", 1)[0]
        return text.decode("ascii", errors="ignore")


#: What a lifetime energy counter cannot honestly reach, in kWh.
#:
#: A house does not generate, import, export or store a million kilowatt-hours:
#: the largest reading in the whole diagnosis corpus is
#: `total_pv_generation_battery_discharge` at 79,459.6 kWh, and that machine has
#: been running for years. So a counter above this is not a measurement; it is a
#: register word that is not what it claims to be, and the sensor is better
#: unavailable than wrong.
#:
#: What made it necessary: all three SH-RS read on SUNSTONE-H_B000.V002.P067
#: have a broken high word at 13042, and at one of them it reads 0xFFFF -- the
#: specification's *unavailable* -- while 13041, the low word, counts on. The
#: double word is therefore not 0xFFFFFFFF, so a `nan=` sentinel cannot catch
#: it, and `total_battery_charge` published 429,494,295.3 kWh and then rose
#: plausibly from there, into the recorder's long-term statistics.
#: `.wiki/wiki/concepts/a-million-kwh-is-not-a-reading.md` has the
#: measurement, what else was weighed, and what the ceiling cannot see.
ENERGY_CEILING_KWH = 1_000_000.0

#: The same ceiling for a counter that holds watt-hours (the wallbox's).
ENERGY_CEILING_WH = ENERGY_CEILING_KWH * 1000


class CeilingField(NumberField[float]):
    """A number a device cannot honestly report above, decoded as absent.

    `nan=` catches the sentinels the specification declares, which are exact
    raw patterns. This catches the other half: a word that is broken rather
    than declared absent, where the reading is still a number and only its
    size says so.

    The ceiling belongs to the **field**, not to the sensor platform, because
    everything that reads this map has to agree about it: Home Assistant's
    sensors, the diagnosis's published readings, the capability test's
    plausibility checks and anything else that polls the library. A rule in
    one of them would leave the others publishing a number the first has
    already refused.

    It is deliberately far from anything real -- see `ENERGY_CEILING_KWH` --
    so that it decides nothing a measurement could decide. It is not a
    plausibility check: a counter that is *merely* wrong reads below it and is
    for `capability_test.plausibility` to find.
    """

    def __init__(self, address: int, *, ceiling: float, **kwargs: Any) -> None:
        """Declare the field; `ceiling` is in the field's own unit."""
        super().__init__(address, **kwargs)
        self.ceiling = ceiling
        self._refused: float | None = None

    def decode(self, words: list[int], scale_exponent: int | None = None) -> Any:
        """Decode as usual, and return None above the ceiling.

        Logged when the refused value changes rather than every poll: a broken
        high word reads the same from one poll to the next while the word below
        it still counts, so this is a few lines a day where a line per poll
        would be a thousand. The field is one object shared by every device on
        this map, so the memory is only about the log, never about what a
        device reads.
        """
        value = super().decode(words, scale_exponent)
        if not isinstance(value, (int, float)) or value <= self.ceiling:
            return value
        if value != self._refused:
            self._refused = value
            _LOGGER.warning(
                "Field %r read %s %s, past the %s it could honestly reach,"
                " so it is reported as unavailable: a register this far out"
                " is holding a broken word, not a measurement",
                self.name,
                f"{value:,.1f}",
                self.unit or "",
                f"{self.ceiling:,.0f}",
            )
        return None


def energy_counter(
    address: int,
    *,
    scale: float,
    word_order: Literal["big", "little"] = "little",
    nan: int | Iterable[int] | None = None,
    unit: str = "kWh",
    count: int = 2,
) -> CeilingField:
    """Declare a multi-word energy value, refused above its ceiling.

    Every energy register wider than one word in this library's maps is
    declared with this rather than `uint32` or `uint64`, so that none is left
    to publish a broken word; `tests/test_energy_ceiling.py` holds the maps to
    it, with no exceptions to remember. Counters are what this was written
    for, but a rating is covered too -- the ceiling is a statement about
    kilowatt-hours, not about accumulation, and an iHomeManager's rated
    battery capacity is no likelier to reach a million than a house is.

    A one-word field does not need it: at 0.1 kWh a word cannot reach 6,553.6
    kWh, which is a plausible lifetime, and its sentinel is 0xFFFF.

    **`scale` is required and the ceiling comes from `unit`**, neither of them
    guessed. A default scale would have quietly re-scaled the four counters
    that hold whole units rather than tenths, which is the one mistake this
    map's tests exist to catch; and a ceiling in the wrong unit would be a
    thousand times too low, which on a wallbox's watt-hours would refuse any
    car that has ever charged a megawatt-hour.
    """
    ceilings = {"kWh": ENERGY_CEILING_KWH, "Wh": ENERGY_CEILING_WH}
    if unit not in ceilings:
        raise ValueError(f"no energy ceiling for {unit!r}: add one, do not guess")
    return CeilingField(
        address,
        count=count,
        signed=False,
        scale=scale,
        word_order=word_order,
        nan=nan,
        unit=unit,
        ceiling=ceilings[unit],
    )


def string(
    address: int,
    length: int,
    *,
    writable: bool = False,
    word_order: Literal["big", "little"] = "big",
) -> TextField:
    """Declare a fixed-length, NUL-terminated ASCII string over `length` words."""
    if writable and word_order != "big":
        # Encoding is the library's, high word first; nothing writes such text.
        raise ValueError("a writable string is high word first")
    return TextField(address, count=length, writable=writable, word_order=word_order)


def present(value: RegisterValue) -> RegisterValue:
    """Return the value, or None where the device said it has none.

    The library already maps the numeric "unavailable" codes to None -- 0xFFFF
    for a U16, 0x7FFFFFFF for an S32 -- because those are declared per field
    as `nan=`. Strings have no such declaration: Sungrow's protocol says a
    UTF-8 field it cannot fill is **all 0x00**, which decodes to the empty
    string and would otherwise reach Home Assistant as a sensor reading of
    "".

    That matters beyond tidiness. Capabilities are probed by asking whether a
    field came back with a value, so an empty firmware string would count as
    a battery firmware being present on every inverter without a Sungrow
    battery -- and create an entity to report nothing.
    """
    if isinstance(value, str) and not value.strip("\x00").strip():
        return None
    return value


class Silent:
    """Registers that timed out once in a run, so narrowing waits on each once.

    Narrowing exists to find which register a failed read was refusing, and a
    refusal costs milliseconds. A register that goes **quiet** instead costs
    the whole timeout on every read that touches it. fwitten's master, on its
    own LAN port, has four: 13199 and the three firmware strings at 13249,
    13264 and 13279. Without a memory of them, the readings' field-by-field
    salvage and the dump's single-address fallback would each wait on them
    again, and a diagnosis would spend most of its time on four registers whose
    answer is already known.

    So a narrowing read that times out is noted here, and a later narrowing
    read that overlaps it is not sent: it is recorded as unread, the same
    `None` a timeout would have produced. Block reads are not capped. Their
    repetition is how contention is told from a fault, and the block read test
    is that measurement.
    """

    def __init__(self) -> None:
        """Start with nothing known to be silent."""
        self._ranges: set[tuple[str, int, int]] = set()

    def note(self, space: str, address: int, count: int) -> None:
        """Record that a read of these registers timed out."""
        self._ranges.add((space, address, address + count))

    def covers(self, space: str, address: int, count: int) -> bool:
        """Whether a read of these registers overlaps one that timed out."""
        end = address + count
        return any(
            known == space and start < end and address < stop
            for known, start, stop in self._ranges
        )
