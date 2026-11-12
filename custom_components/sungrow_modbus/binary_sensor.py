"""Binary sensor platform: power flow bits, mode flags, fault flags, wallbox.

Most of these are the power flow status. The inverter reports what is flowing
where as bits of one register, which the YAML package split into seven binary
sensors. They are all computed from the same reading, so they share a
coordinator and go unavailable together. Each has a `(delay)` twin that
repeats it only once the bit has held for a minute -- fourteen entities from
one register.

Beside them: the decoded `0xAA`/`0x55` limitation modes, `Fault reported` and
`Alarm reported` from the fault and alarm words, and the wallbox's two.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from sungrow_modbus.hybrid_inverter.smoothing import DelayOn

from .coordinator import SungrowConfigEntry, SungrowRuntimeData
from .derived_descriptions import DERIVED_BINARY_SENSORS
from .entity import (
    SungrowBinarySensorDescription,
    SungrowDeviceEntity,
    SungrowEntity,
    SungrowStringInverterEntity,
)
from .string_inverter_descriptions import STRING_INVERTER_BINARY_DESCRIPTIONS
from .wallbox_descriptions import WALLBOX_BINARY_DESCRIPTIONS

# The coordinator does the polling; entities never talk to the inverter.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sungrow binary sensors."""
    runtime_data = entry.runtime_data
    if runtime_data.is_wallbox_only:
        assert runtime_data.wallbox is not None
        async_add_entities(
            SungrowWallboxBinarySensor(runtime_data.wallbox, description)
            for description in WALLBOX_BINARY_DESCRIPTIONS
        )
        return

    # An SG: its own two, and nothing of the hybrid's.
    if runtime_data.is_string_inverter:
        async_add_entities(
            SungrowStringInverterBinarySensor(
                runtime_data.string_inverter[description.component], description
            )
            for description in STRING_INVERTER_BINARY_DESCRIPTIONS
            if description.component in runtime_data.string_inverter
            and runtime_data.inverter_coordinator.device.serves(description.field)
        )
        return

    async_add_entities(
        SungrowBinarySensor(runtime_data, description)
        for description in DERIVED_BINARY_SENSORS
        if runtime_data.serves(description)
    )

    # The wallbox's two: whether it is charging, and whether it is enabled.
    # `Charging` is derived from the status code rather than from the power,
    # because a vehicle that has stopped drawing mid-session reads 0 W and is
    # still charging as far as the charge point is concerned.
    wallbox = runtime_data.wallbox
    if wallbox is not None:
        async_add_entities(
            SungrowWallboxBinarySensor(wallbox, description)
            for description in WALLBOX_BINARY_DESCRIPTIONS
        )


class SungrowWallboxBinarySensor(SungrowDeviceEntity, BinarySensorEntity):
    """A state a wallbox reports about itself."""

    entity_description: SungrowBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state, or None where the block did not answer.

        None rather than False for an absent reading: "we did not read it"
        and "it is not charging" are different claims, and a False here would
        be the second one invented out of the first.
        """
        value = self.native_value_source
        return value if isinstance(value, bool) else None


class SungrowStringInverterBinarySensor(
    SungrowStringInverterEntity, BinarySensorEntity
):
    """A state an SG reports about itself."""

    entity_description: SungrowBinarySensorDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state, or None where it did not read."""
        value = self.coordinator.device.field(self.entity_description.field)
        return value if isinstance(value, bool) else None


class SungrowBinarySensor(SungrowEntity, BinarySensorEntity):
    """One derived on/off state of the inverter, optionally delayed."""

    entity_description: SungrowBinarySensorDescription

    def __init__(
        self,
        runtime_data: SungrowRuntimeData,
        entity_description: SungrowBinarySensorDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(runtime_data, entity_description)
        self._delay: DelayOn | None = None
        if entity_description.delay_on is not None:
            self._delay = DelayOn(entity_description.delay_on)
        self._cancel_wake: CALLBACK_TYPE | None = None
        self._delayed: bool | None = None

    @property
    def _bit(self) -> bool | None:
        """Return the bit as read, or None if there is no current reading.

        None while unavailable as well as while unread, which restarts the
        delay -- "set for sixty seconds" has to mean sixty seconds of knowing
        it was set, and a component that failed a poll keeps its previous
        values rather than reporting the current one.
        """
        if not self.available:
            return None
        value = self.native_value_source
        return None if value is None else bool(value)

    @property
    def is_on(self) -> bool | None:
        """Return whether the bit is set, delay applied if there is one."""
        if self._delay is None:
            return self._bit
        return self._delayed

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; nothing here is keyed on the id.

        Defining it opts this class's add hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11).
        """
        super().async_entity_id_changed(old_entity_id)

    async def async_added_to_hass(self) -> None:
        """Start the delay from the reading already in hand.

        The coordinator has usually polled before the entity exists, and
        `CoordinatorEntity` does not replay that first update -- so without
        this a delayed entity would report None until the next poll, and its
        minute would start from there rather than from now.
        """
        await super().async_added_to_hass()
        if self._delay is not None:
            self._advance()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Apply the delay to the new reading, then write state."""
        if self._delay is not None:
            self._advance()
        super()._handle_coordinator_update()

    @callback
    def _advance(self) -> None:
        """Feed the current reading to the delay and arm the next wake-up."""
        assert self._delay is not None
        self._unschedule()
        self._delayed = self._delay.update(self.hass.loop.time(), self._bit)

        remaining = self._delay.remaining(self.hass.loop.time())
        if remaining is None:
            return
        # Write state the moment the delay runs out rather than at the next
        # poll. A minute-long delay reported up to a poll interval late is
        # close enough for a dashboard and not close enough for an automation,
        # and the entity this replaces was exact.
        self._cancel_wake = async_call_later(self.hass, remaining, self._async_elapsed)

    @callback
    def _async_elapsed(self, _now: object) -> None:
        """Report on without waiting for a poll, now the delay has run out.

        True by construction rather than by asking the clock again: this
        wake-up is only ever armed while the bit is set and counting, and it
        is cancelled the moment either stops being so.
        """
        self._cancel_wake = None
        self._delayed = True
        self.async_write_ha_state()

    @callback
    def _unschedule(self) -> None:
        """Cancel a pending wake-up, if there is one."""
        if self._cancel_wake is not None:
            self._cancel_wake()
            self._cancel_wake = None

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the pending wake-up, so a removed entity writes no state."""
        self._unschedule()
        await super().async_will_remove_from_hass()
