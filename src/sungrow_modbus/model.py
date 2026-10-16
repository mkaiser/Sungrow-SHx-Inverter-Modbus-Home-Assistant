"""Shared result types for a device update."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from modbus_connection import ModbusError


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
    """Decode raw register words as text, high byte first, without the padding.

    Sungrow pads a string field with 0x00, so the NULs are stripped; anything
    undecodable is replaced rather than raised, because a reading with one
    odd byte is still a reading. Whitespace is the caller's to strip: a
    serial's exact text is what its stand-in is hashed from.
    """
    raw = b"".join(int(word).to_bytes(2, "big") for word in words)
    return raw.decode(encoding, "replace").strip("\x00")


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
    13264 and 13279. The readings' field-by-field salvage then asked each of
    them three sweeps over, and the dump's single-address fallback asked them
    again -- a survey of about 39 minutes, most of it spent waiting on four
    registers whose answer was already known.

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
