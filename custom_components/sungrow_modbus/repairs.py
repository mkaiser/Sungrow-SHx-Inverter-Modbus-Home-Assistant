"""Putting back what an interrupted control test left behind.

The control test writes to every control it can, checks it, and puts it back,
and the restore is the one part of it that is never budgeted, never deadlined
and never skipped. That covers everything except the cases where the code
itself stops running: Home Assistant restarted, the entry was reloaded, the
machine lost power, the link went away and stayed away.

For those there is a snapshot, written to Home Assistant's store *before the
first write* and removed only once every register in it has been put back and
read back. Anything left in it on the next setup is a house still carrying a
test's values, and this turns that into something a person can click.

Two things it says, in this order, and the order is the point:

* **whether the inverter may still be stopped.** Only a run given leave to
  restart can leave it that way, and it is the only consequence here that
  costs generation rather than accuracy. So it goes first, even though it is
  the rarer case.
* **which registers are still holding a test value**, with what they should be.

The fix flow is the only path by which this integration writes a register
outside an explicit user action -- and it stays inside that rule, because
confirming the repair *is* the action.
"""

from __future__ import annotations

import logging

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir
from sungrow_modbus.control_test import Snapshot

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

#: One issue per config entry, because one entry is one endpoint and a house
#: may have two of them with two different things left behind.
ISSUE_PREFIX = "control_test_unfinished"


def issue_id(entry: ConfigEntry) -> str:
    """Return the issue id for one entry's unfinished run."""
    return f"{ISSUE_PREFIX}_{entry.entry_id}"


def async_raise(hass: HomeAssistant, entry: ConfigEntry, snapshot: Snapshot) -> None:
    """Tell the owner that a control test did not finish putting things back.

    Not fixable by ignoring: the placeholders name real registers on a real
    inverter that are holding a test's values, and an issue somebody dismisses
    is an inverter left with a 3 % minimum state of charge.
    """
    registers = ", ".join(
        f"{name} (should be {value:g})" for name, value in snapshot.values.items()
    )
    # A stopped inverter is not the same problem as a changed setting, and the
    # severity should not say it is. `stopped_at` is set the moment 0xCE goes
    # out and cleared only once the inverter reports running again, so finding
    # it here means the machine may still be down: no production, no battery,
    # and nothing on the backup circuit. That outranks a minimum state of
    # charge left at 3 %, which costs nothing until the battery reaches it.
    stopped = snapshot.stopped_at is not None
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(entry),
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR if stopped else ir.IssueSeverity.WARNING,
        translation_key=(
            "control_test_left_stopped" if stopped else "control_test_unfinished"
        ),
        translation_placeholders={"name": entry.title, "registers": registers},
        data={"entry_id": entry.entry_id},
    )


def async_clear(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take the issue down, once there is nothing left to put back."""
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry))


class ControlTestRepairFlow(RepairsFlow):
    """Show what is still changed, and put it back on confirmation."""

    def __init__(self, entry: ConfigEntry, snapshot: Snapshot) -> None:
        """Hold the entry and the values to restore."""
        self.entry = entry
        self.snapshot = snapshot

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Offer to restore, listing exactly what would change."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Write every register back, then check the writes took.

        A failure here is reported rather than swallowed, and the issue stays
        up. The commonest reason is the same one that caused the leftovers --
        something else is polling the inverter, or it is not reachable -- and
        both are things the owner can act on and this cannot.
        """
        if user_input is None:
            return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "registers": "\n".join(
                        f"- {name}: {value:g}"
                        for name, value in self.snapshot.values.items()
                    )
                },
            )

        from .control_test import ControlTestRunner

        runner = ControlTestRunner(self.hass, self.entry)
        try:
            restored = await runner.async_restore(self.snapshot)
        except Exception as err:  # a failed restore must not also crash the flow
            # `exception`, and of all the places in this integration this is
            # the one that most needs a traceback: getting here means a repair
            # somebody clicked did **not** put their inverter back, so the
            # house is still carrying a test's values and the only record of
            # why is this line. The dialog gets the short form.
            _LOGGER.exception("Could not restore %s", self.entry.title)
            return self.async_abort(
                reason="restore_failed", description_placeholders={"error": str(err)}
            )
        if not restored:
            return self.async_abort(
                reason="restore_failed",
                description_placeholders={
                    "error": (
                        "some registers would not take the write. Check that "
                        "nothing else is polling the inverter, then try again."
                    )
                },
            )
        async_clear(self.hass, self.entry)
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id_: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Return the flow that fixes one of this integration's issues."""
    from .control_test import async_leftover

    entry_id = str((data or {}).get("entry_id", ""))
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return ConfirmRepairFlow()
    snapshot = await async_leftover(hass, entry)
    if snapshot is None:
        # Already put back, by a later run or by hand. Confirming is then just
        # a way of taking the issue down, which is exactly what it should do.
        return ConfirmRepairFlow()
    return ControlTestRepairFlow(entry, snapshot)
