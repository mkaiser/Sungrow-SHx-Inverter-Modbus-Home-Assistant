"""Mode flags, each one holding register carrying 0xAA or 0x55.

The YAML package used the Modbus platform's own `switches:` with
`verify: true`, which reads the register back after writing to confirm it
took. That instinct was right and is kept: the write is followed by a refresh,
so what the interface shows afterwards is what the inverter actually holds
rather than what it was asked for.

What is *not* kept is the YAML's assumption that any value other than the
`on` code means off. A register reporting the specification's 0xFFFF
"unavailable" sentinel is neither on nor off, and saying "off" to that is how
a user concludes a feature is disabled when in fact their model does not have
it.

One register reads back late: the wallbox's charging word (33540) reads on for
about 10 s after it took an off. Its switch holds the off it wrote for
`hold_off_seconds` against a read of on, so the read-back does not flip it
back for a poll (`SungrowSwitch.is_on`).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import CONF_MODE, MODE_DEVICES, MODE_DIAGNOSTICS
from .coordinator import SungrowConfigEntry
from .diagnosis_entities import SkipEstablishedCapabilityTestsSwitch
from .entity import SungrowEntity, SungrowSwitchDescription
from .switch_descriptions import SWITCH_DESCRIPTIONS

# One at a time, and not for the usual reason. A Sungrow accepts very few
# simultaneous Modbus sessions, and everything on this endpoint is already
# serialized behind one connection -- so two writes issued at once do not go
# faster, they queue, and the second one's timeout starts while it is still
# waiting. Worse, these registers interlock: `battery_min_soc` and
# `battery_max_soc` are rejected if they cross, so an automation that sets both
# in one call has an ordering that matters and must not be raced.
#
# `sensor` and `binary_sensor` set 0 instead because the coordinator does their
# polling and the entities never talk to the inverter at all.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mode flags this device actually has."""
    runtime_data = entry.runtime_data
    # What a single extended run leaves out, on every entry with a capability
    # test to skip tests of. Only a hybrid has one.
    if not runtime_data.is_string_inverter:
        async_add_entities([SkipEstablishedCapabilityTestsSwitch(runtime_data)])
    if (
        runtime_data.is_wallbox_only
        or entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS
    ):
        # Neither has controls to offer beside it.
        return
    async_add_entities(
        SungrowSwitch(runtime_data, description)
        for description in SWITCH_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowSwitch(SungrowEntity, SwitchEntity):
    """One mode flag, read and written by the same entity."""

    entity_description: SungrowSwitchDescription

    #: Cancels the timer that ends a hold on a written off, while one runs.
    _release_hold: Callable[[], None] | None = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the flag is set, or None if it is neither.

        Three states, not two. A register that answered with the codes the
        specification defines is on or off; one that answered 0xFFFF, or that
        has never been read, is unknown — and reporting that as "off" would
        tell a user a feature is disabled when their model simply does not
        have it.
        """
        raw = self.native_value_source
        if raw is None:
            return None
        value = int(raw)
        if value == self.entity_description.on_value:
            # The register catching up with an off this switch wrote, not
            # the state: the hold ends at its timer or at a read of off.
            return self._release_hold is None
        if self.entity_description.minute_field is not None:
            # A window's end: any hour but 24 is a time the `time` entity
            # beside this one holds, so the switch is simply off. There is no
            # third state to report, because an hour the inverter cannot mean
            # is already None above.
            return False
        if (
            value == self.entity_description.off_value
            or value in self.entity_description.also_off
        ):
            return False
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the flag, or a window's end to the end of the day."""
        description = self.entity_description
        self._end_hold()
        await self._async_write(
            *self._writes(description.on_value, description.on_minute)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the flag, or hand a window's end back to its time entity.

        Where the register reads on for a while after it took an off
        (`hold_off_seconds`), the off is held from the moment it is written,
        so the read-back that follows the write already shows it. A write
        that fails ends the hold: nothing was taken to wait for.
        """
        description = self.entity_description
        if description.hold_off_seconds > 0:
            self._end_hold()
            self._release_hold = async_call_later(
                self.hass, description.hold_off_seconds, self._hold_expired
            )
        try:
            await self._async_write(
                *self._writes(description.off_value, description.off_minute)
            )
        except BaseException:
            self._end_hold()
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        """End a hold once a read agrees with the off it held."""
        raw = self.native_value_source
        if raw is not None and int(raw) != self.entity_description.on_value:
            self._end_hold()
        super()._handle_coordinator_update()

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; a running hold is not keyed on the id.

        Defining it opts this class's remove hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11).
        """
        super().async_entity_id_changed(old_entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Cancel a running hold's timer with the entity."""
        self._end_hold()
        await super().async_will_remove_from_hass()

    @callback
    def _hold_expired(self, _now: datetime) -> None:
        """Show what the register reads once the hold is over."""
        self._release_hold = None
        self.async_write_ha_state()

    def _end_hold(self) -> None:
        if self._release_hold is not None:
            self._release_hold()
            self._release_hold = None

    def _writes(self, hour: int, minute: int) -> tuple[tuple[str, float], ...]:
        """Return the register writes for one side of this switch.

        A mode flag writes one word. A window's end writes two, hour then
        minute, in that order -- the same order `SungrowTime` uses, so a
        half-applied write leaves the same state either entity would.
        """
        description = self.entity_description
        if description.minute_field is None:
            return ((description.field, hour),)
        return ((description.field, hour), (description.minute_field, minute))
