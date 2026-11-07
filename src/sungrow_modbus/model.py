"""Shared result types for a device update."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from modbus_connection import (
    ModbusError,
    ServerDeviceBusyError,
    ServerDeviceFailureError,
)
from modbus_connection.model import StringField

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
    """

    def decode(self, words: list[int], scale_exponent: int | None = None) -> str:
        """Return the text before the first NUL, as ASCII, dropping odd bytes."""
        raw = b"".join((word & 0xFFFF).to_bytes(2, "big") for word in words)
        text = raw.lstrip(b"\x00").split(b"\x00", 1)[0]
        return text.decode("ascii", errors="ignore")


def string(address: int, length: int, *, writable: bool = False) -> TextField:
    """Declare a fixed-length, NUL-terminated ASCII string over `length` words."""
    return TextField(address, count=length, writable=writable)


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
