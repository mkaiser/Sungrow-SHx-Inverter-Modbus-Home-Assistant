"""Shared result types for a device update."""

from __future__ import annotations

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


def present(value: object) -> object:
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
