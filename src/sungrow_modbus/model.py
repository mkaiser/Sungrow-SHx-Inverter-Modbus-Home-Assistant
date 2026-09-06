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
