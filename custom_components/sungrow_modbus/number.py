"""Settings the user can change, over the same register that reads them.

The YAML package needed three pieces for one setting: a `template number` to
hold the value, a `modbus.write_register` action to send it, and a
`homeassistant.update_entity` call afterwards to see the result — because YAML
Modbus has no write-then-read, so without that last step the user set a value
and the interface showed the old one until the next poll.

An integration does not need any of that. One entity reads and writes one
register, and asks its coordinator to refresh straight after the write. That
is the whole reason the YAML's readback automations are deleted rather than
ported.
"""

from __future__ import annotations

import logging

from modbus_connection import ModbusError

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from sungrow_modbus import FALLBACK_W, Capability
from sungrow_modbus.battery import ceiling as battery_ceiling
from sungrow_modbus.inverter import export_scale

from .const import (
    CONF_BATTERY_MAX_POWER,
    CONF_EXPORT_WRITE_SCALE,
    CONF_EXPORT_WRITE_SCALE_FIRMWARE,
)
from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowNumberDescription
from .number_descriptions import NUMBER_DESCRIPTIONS

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

_LOGGER = logging.getLogger(__name__)

#: The one setting whose write scale differs between firmwares.
EXPORT_LIMIT = "export_power_limit"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the settings this device actually has."""
    runtime_data = entry.runtime_data
    async_add_entities(
        (
            SungrowExportLimitNumber
            if description.field == EXPORT_LIMIT
            else SungrowNumber
        )(runtime_data, description)
        for description in NUMBER_DESCRIPTIONS
        if runtime_data.serves(description)
    )


class SungrowNumber(SungrowEntity, NumberEntity):
    """One writable register, read and written by the same entity."""

    entity_description: SungrowNumberDescription

    @property
    def native_min_value(self) -> float:
        """Return the lower bound, from the inverter where it states one."""
        field = self.entity_description.minimum_field
        if field is not None and (value := self._field(field)) is not None:
            return float(value)
        return self.entity_description.native_min_value

    @property
    def native_max_value(self) -> float:
        """Return the upper bound, from whichever source actually knows it.

        For a battery power this is the lower of two ceilings, because both
        are real: V1.1.11 says the range is "from 0 to BDC rated power
        (register 5628)", which is the inverter's converter, and the pack has
        its own limit which the inverter does not know.
        """
        description = self.entity_description
        field = description.maximum_field
        if field is not None and (value := self._field(field)) is not None:
            return float(value)
        if description.maximum_from_battery:
            return float(self._battery_maximum())
        return description.native_max_value

    def _battery_maximum(self) -> int:
        """Return the lower of the inverter's rating and the pack's limit.

        The ladder itself lives in the library, in `battery.ceiling`, because
        the control test needs the same answer and an entity that disagreed
        with it would refuse values the test had just written -- or accept ones
        it would not. One home for the arithmetic; this decides only what to
        feed it, which is the part that needs a config entry.
        """
        sungrow_capacity = None
        if Capability.SUNGROW_BATTERY in self._runtime_data.capabilities:
            sungrow_capacity = self._float("battery_capacity_high_precision")
        limit = battery_ceiling(
            configured_w=self.coordinator.config_entry.options.get(
                CONF_BATTERY_MAX_POWER
            ),
            sungrow_capacity_kwh=sungrow_capacity,
            bms_max_charging_current_a=self._float("bms_max_charging_current"),
            battery_voltage_v=self._float("battery_voltage"),
            bdc_rated_power_w=self._field("bdc_rated_power"),
        )
        return limit if limit is not None else FALLBACK_W

    def _field(self, name: str) -> float | int | None:
        """Return one register's value, wherever it lives, or None."""
        try:
            return self.coordinator.device.field(name)  # type: ignore[return-value]
        except (AttributeError, KeyError):
            return None

    def _float(self, name: str) -> float | None:
        """Return one register's value as a float, or None."""
        value = self._field(name)
        return None if value is None else float(value)

    @property
    def native_value(self) -> float | None:
        """Return what the register currently holds."""
        value = self.native_value_source
        return None if value is None else float(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write the register, then read it back.

        The refresh is not optimism about the write having worked — it is how
        the user finds out that it did. An inverter can clamp a value to
        something it prefers, and showing what was asked for rather than what
        was accepted is how the YAML package's own readback automations came
        to exist.

        The engineering value goes to the library, which applies the register's
        scale: 20.5 % becomes the raw 205 that a 0.1 %-per-count register
        expects. Doing that arithmetic here is how a template gets it wrong.
        """
        component = self.coordinator.device.component(self.entity_description.component)
        try:
            await component.write(self.entity_description.field, value)
        except ModbusError as err:
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: {err}"
            ) from err
        # `async_refresh`, not `async_request_refresh`. The latter goes
        # through the coordinator's debouncer, which has a **10 second
        # cooldown** -- so a second change inside that window is written to
        # the register and never read back, and the interface shows the
        # previous value for up to ten seconds. That is precisely the bug the
        # YAML package's `homeassistant.update_entity` calls existed to work
        # around, and debouncing here would bring it back.
        #
        # The debouncer is there to coalesce storms of *automatic* refresh
        # requests. An explicit user action is not a storm.
        await self.coordinator.async_refresh()


class SungrowExportLimitNumber(SungrowNumber):
    """The export power limit, written at this inverter's own scale.

    Register 13074 reads in watts everywhere, but its write side depends on
    the firmware: three houses multiply the word they are handed by ten, and
    fwitten's master/slave pair stores it as handed. The library's field
    divides every write by ten -- one constant, shared by every inverter in
    Home Assistant -- which sets a tenth of what was asked on the second kind.

    So this entity asks. The first write runs `export_scale.async_probe`,
    whose one write changes nothing on either firmware, keeps the answer in
    the entry's data, and from then on writes the raw word itself.
    """

    async def async_set_native_value(self, value: float) -> None:
        """Write the limit at the measured scale, probing for it first if need be."""
        factor = await self._async_write_scale()
        word = export_scale.word_for(value, factor)
        try:
            await self.coordinator.device.async_write_word(
                export_scale.LIMIT.address, word
            )
        except ModbusError as err:
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: {err}"
            ) from err
        # A direct refresh, for the reason `SungrowNumber` gives.
        await self.coordinator.async_refresh()

    async def _async_write_scale(self) -> int:
        """Return this inverter's write factor, measuring it if it is not known.

        A probe that cannot answer falls back to ten, the factor measured at
        three houses of four, and is **not** stored, so the next write asks
        again. It cannot answer while feed-in limitation is off and the held
        limit caps something -- and then the register ignores the write
        anyway, so nothing is lost.
        """
        entry = self.coordinator.config_entry
        stored = self._stored_write_scale()
        if stored is not None:
            return stored
        try:
            result = await export_scale.async_probe(
                self.coordinator.device, lift_mode=True
            )
        except ModbusError as err:
            # The reads that decide whether to write failed: nothing was
            # written, and guessing a factor here would be guessing at a
            # real house's export limit.
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: could not read the export "
                f"limit's bounds to work out this inverter's write scale: {err}"
            ) from err
        if result.left_changed:
            _LOGGER.error(
                "The export limit write-scale probe left %s changed: %s",
                self.entity_id,
                result.reason,
            )
            raise HomeAssistantError(
                f"Could not write {self.entity_id}: {result.reason}"
            )
        if result.write_units_per_count is None:
            _LOGGER.info(
                "Export limit write scale for %s not determined, dividing by %s: %s",
                self.entity_id,
                export_scale.MULTIPLIER,
                result.reason,
            )
            return export_scale.MULTIPLIER
        _LOGGER.info(
            "Export limit write scale for %s: %s per count, because %s",
            self.entity_id,
            result.write_units_per_count,
            result.reason,
        )
        self.hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_EXPORT_WRITE_SCALE: result.write_units_per_count,
                CONF_EXPORT_WRITE_SCALE_FIRMWARE: self.coordinator.device.firmware,
            },
        )
        return result.write_units_per_count

    def _stored_write_scale(self) -> int | None:
        """Return the stored factor, unless the firmware has changed since.

        A factor measured on other firmware is discarded rather than trusted:
        the YAML package's users saw this register change behaviour across a
        firmware update (#763), and the probe that replaces it changes
        nothing. One stored before the firmware was recorded is adopted for
        the firmware running now -- the most likely one it was measured on,
        and the alternative is re-probing every existing entry at once.
        While the firmware string is unread, nothing can be compared, so the
        stored factor stands.
        """
        entry = self.coordinator.config_entry
        stored = entry.data.get(CONF_EXPORT_WRITE_SCALE)
        if stored is None:
            return None
        current = self.coordinator.device.firmware
        measured_on = entry.data.get(CONF_EXPORT_WRITE_SCALE_FIRMWARE)
        if current is None or measured_on == current:
            return int(stored)
        if measured_on is None:
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_EXPORT_WRITE_SCALE_FIRMWARE: current}
            )
            return int(stored)
        _LOGGER.info(
            "Firmware of %s changed from %s to %s; measuring the export limit's "
            "write scale again",
            self.entity_id,
            measured_on,
            current,
        )
        data = {
            k: v
            for k, v in entry.data.items()
            if k not in (CONF_EXPORT_WRITE_SCALE, CONF_EXPORT_WRITE_SCALE_FIRMWARE)
        }
        self.hass.config_entries.async_update_entry(entry, data=data)
        return None
