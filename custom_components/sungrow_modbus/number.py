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

from modbus_connection import ModbusError

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from sungrow_modbus import FALLBACK_W, Capability, model_for_capacity, power_from_bms

from .const import CONF_BATTERY_MAX_POWER
from .coordinator import SungrowConfigEntry
from .entity import SungrowEntity, SungrowNumberDescription
from .number_descriptions import NUMBER_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the settings this device actually has."""
    runtime_data = entry.runtime_data
    async_add_entities(
        SungrowNumber(runtime_data, description)
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
        """Return the lower of the inverter's rating and the pack's limit."""
        limits = [
            limit
            for limit in (self._inverter_rating(), self._pack_limit())
            if limit is not None
        ]
        return min(limits) if limits else FALLBACK_W

    def _inverter_rating(self) -> int | None:
        """Return the BDC rated power, which the specification names as the cap."""
        value = self._field("bdc_rated_power")
        return None if value is None else int(value)

    def _pack_limit(self) -> int | None:
        """Return what the battery will take, from the best available source.

        In order: what the user told us, which always wins because they may
        know something the hardware does not; a Sungrow pack's datasheet
        figure, looked up from the capacity it reports; and what the BMS says
        it will take right now.
        """
        configured = self.coordinator.config_entry.options.get(CONF_BATTERY_MAX_POWER)
        if configured:
            return int(configured)

        if Capability.SUNGROW_BATTERY in self._runtime_data.capabilities:
            model = model_for_capacity(self._float("battery_capacity_high_precision"))
            if model is not None:
                return model.conservative_w

        return power_from_bms(
            self._float("bms_max_charging_current"), self._float("battery_voltage")
        )

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
        # around, and it would have shipped as a regression.
        #
        # The debouncer is there to coalesce storms of *automatic* refresh
        # requests. An explicit user action is not a storm.
        await self.coordinator.async_refresh()
