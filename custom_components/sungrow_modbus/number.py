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
from sungrow_modbus import FALLBACK_W, Capability
from sungrow_modbus.battery import ceiling as battery_ceiling

from .const import CONF_BATTERY_MAX_POWER
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
        # around, and it would have shipped as a regression.
        #
        # The debouncer is there to coalesce storms of *automatic* refresh
        # requests. An explicit user action is not a storm.
        await self.coordinator.async_refresh()
