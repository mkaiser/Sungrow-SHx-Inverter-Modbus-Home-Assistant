"""Putting back what an interrupted capability test left behind.

The capability test writes to every control it can, checks it, and puts it back,
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

from homeassistant.components.repairs import (
    ConfirmRepairFlow,
    RepairsFlow,
    RepairsFlowResult,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from sungrow_modbus.capability_test import Snapshot
from sungrow_modbus.hybrid_inverter import ev_charger as ev
from sungrow_modbus.wallbox import capability_test as wct

from .const import DOMAIN
from .texts import Texts, async_texts

_LOGGER = logging.getLogger(__name__)

#: One issue per config entry, because one entry is one endpoint and a house
#: may have two of them with two different things left behind.
ISSUE_PREFIX = "capability_test_unfinished"


def issue_id(entry: ConfigEntry) -> str:
    """Return the issue id for one entry's unfinished run."""
    return f"{ISSUE_PREFIX}_{entry.entry_id}"


def async_raise(hass: HomeAssistant, entry: ConfigEntry, snapshot: Snapshot) -> None:
    """Tell the owner that a capability test did not finish putting things back.

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
            "capability_test_left_stopped" if stopped else "capability_test_unfinished"
        ),
        translation_placeholders={"name": entry.title, "registers": registers},
        data={"entry_id": entry.entry_id},
    )


#: A wallbox entry's unfinished capability test, its own issue beside the
#: inverter's: a different device, and settings a person may have to set back
#: in the app, because a disabled wallbox answers no write.
WALLBOX_ISSUE_PREFIX = "wallbox_capability_test_unfinished"


def wallbox_issue_id(entry: ConfigEntry) -> str:
    """Return the issue id for one wallbox entry's unfinished run."""
    return f"{WALLBOX_ISSUE_PREFIX}_{entry.entry_id}"


async def async_wallbox_settings(
    hass: HomeAssistant, leftover: dict[str, object]
) -> str:
    """Return the settings a wallbox run left changed, one line each, in words.

    Each line names the setting, the value it should have, and where the app
    sets it, in Home Assistant's language: a register number alone tells an
    owner nothing they can act on.
    """
    texts = await async_texts(hass)
    raw: dict[int, int] = leftover["raw"]  # type: ignore[assignment]
    touched: list[int] = leftover["touched"]  # type: ignore[assignment]
    lines = []
    for address in touched:
        word = raw.get(address)
        if word is None:
            continue
        lines.append("- " + _wallbox_line(texts, address, word))
    return "\n".join(lines)


#: The managed wallbox's modes, each its own sentence.
_MODE_LINES: dict[int, str] = {
    ev.FAST: "wallbox_left_mode_fast",
    ev.PV_SURPLUS: "wallbox_left_mode_pv_surplus",
    ev.QUANTITY_AND_TIME: "wallbox_left_mode_quantity_and_time",
    ev.USER_DEFINED: "wallbox_left_mode_user_defined",
}


def _wallbox_line(say: Texts, address: int, word: int) -> str:
    """Return one setting's sentence."""
    if address == wct.OUTPUT_CURRENT:
        return say("wallbox_left_output_current", amps=f"{word / 10:g}")
    if address == wct.PHASE_SETPOINT:
        return say(
            "wallbox_left_phase_single" if word == 1 else "wallbox_left_phase_three"
        )
    if address == wct.ENABLED:
        return say("wallbox_left_enabled" if word == 1 else "wallbox_left_disabled")
    if address == wct.START_STOP:
        return say("wallbox_left_stopped" if word == 1 else "wallbox_left_started")
    if address == ev.CHARGING:
        return say(
            "wallbox_left_charging_on" if word == ev.ON else "wallbox_left_charging_off"
        )
    if address == ev.MODE and word in _MODE_LINES:
        return say(_MODE_LINES[word])
    if address == ev.USER_CURRENT:
        return say("wallbox_left_user_current", amps=f"{word / 10:g}")
    return say("wallbox_left_register", register=address + 1, word=word)


async def async_raise_wallbox(
    hass: HomeAssistant, entry: ConfigEntry, leftover: dict[str, object]
) -> None:
    """Tell the owner that a wallbox test did not put everything back.

    An error, not a warning, where the wallbox may be left disabled or the
    charging switched: a car that does not charge overnight is noticed in the
    morning, too late.
    """
    raw: dict[int, int] = leftover["raw"]  # type: ignore[assignment]
    touched: list[int] = leftover["touched"]  # type: ignore[assignment]
    serious = bool(leftover.get("managed")) or (
        wct.ENABLED in touched and raw.get(wct.ENABLED) == 1
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        wallbox_issue_id(entry),
        is_fixable=True,
        severity=ir.IssueSeverity.ERROR if serious else ir.IssueSeverity.WARNING,
        translation_key=WALLBOX_ISSUE_PREFIX,
        translation_placeholders={
            "name": entry.title,
            "settings": await async_wallbox_settings(hass, leftover),
        },
        data={"entry_id": entry.entry_id, "wallbox": True},
    )


def async_clear_wallbox(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take the wallbox issue down, once the house is as it was."""
    ir.async_delete_issue(hass, DOMAIN, wallbox_issue_id(entry))


class WallboxTestRepairFlow(RepairsFlow):
    """Show what a wallbox test left changed, and put it back on confirmation."""

    def __init__(self, entry: ConfigEntry, leftover: dict[str, object]) -> None:
        """Hold the entry and what it left."""
        self.entry = entry
        self.leftover = leftover

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Offer to put it back."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Write it back and check the house; on failure say what to do by hand."""
        if user_input is None:
            return self.async_show_form(
                step_id="confirm",
                description_placeholders={
                    "settings": await async_wallbox_settings(self.hass, self.leftover)
                },
            )
        from .wallbox_capability_test import async_restore_leftover

        texts = await async_texts(self.hass)
        try:
            done = await async_restore_leftover(self.hass, self.entry)
        except Exception as err:  # a failed restore must not also crash the flow
            # As for the inverter: a repair somebody clicked did not put their
            # wallbox back, and this line is the only record of why.
            _LOGGER.exception("Could not restore the wallbox of %s", self.entry.title)
            return self.async_abort(
                reason="restore_failed",
                description_placeholders={
                    "error": f"{err}. {texts('wallbox_restore_by_hand')}"
                },
            )
        if not done:
            return self.async_abort(
                reason="restore_failed",
                description_placeholders={"error": texts("wallbox_restore_by_hand")},
            )
        return self.async_create_entry(data={})


def async_clear(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Take the issue down, once there is nothing left to put back."""
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry))


class CapabilityTestRepairFlow(RepairsFlow):
    """Show what is still changed, and put it back on confirmation."""

    def __init__(self, entry: ConfigEntry, snapshot: Snapshot) -> None:
        """Hold the entry and the values to restore."""
        self.entry = entry
        self.snapshot = snapshot

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Offer to restore, listing exactly what would change."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
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

        from .capability_test import CapabilityTestRunner

        runner = CapabilityTestRunner(self.hass, self.entry)
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
                    "error": (await async_texts(self.hass))("restore_some_refused")
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
    from .capability_test import async_leftover

    entry_id = str((data or {}).get("entry_id", ""))
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return ConfirmRepairFlow()
    if issue_id_.startswith(WALLBOX_ISSUE_PREFIX):
        from .wallbox_capability_test import async_leftover as wallbox_leftover

        leftover = await wallbox_leftover(hass, entry)
        if leftover is None:
            return ConfirmRepairFlow()
        return WallboxTestRepairFlow(entry, leftover)
    snapshot = await async_leftover(hass, entry)
    if snapshot is None:
        # Already put back, by a later run or by hand. Confirming is then just
        # a way of taking the issue down, which is exactly what it should do.
        return ConfirmRepairFlow()
    return CapabilityTestRepairFlow(entry, snapshot)
