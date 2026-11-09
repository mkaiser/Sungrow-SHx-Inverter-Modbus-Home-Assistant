"""Sensor platform for the Sungrow Modbus integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import CONF_HOST, CONF_PORT, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from sungrow_modbus.capability_test import ledger
from sungrow_modbus.energy_integral import EnergyIntegral
from sungrow_modbus.hybrid_inverter.faults import active
from sungrow_modbus.hybrid_inverter.smoothing import TimeWeightedAverage

from .battery_descriptions import (
    CELL_DESCRIPTIONS,
    MODULE_DESCRIPTIONS,
    PACK_DESCRIPTIONS,
)
from .const import CONF_MODE, MODE_DEVICES, MODE_DIAGNOSTICS
from .coordinator import SungrowConfigEntry, SungrowRuntimeData
from .derived_descriptions import DERIVED_SENSORS
from .diagnosis_entities import (
    CapabilityTestCountSensor,
    CapabilityTestStatusSensor,
    DiagnosisNextStartSensor,
    DiagnosisProgressSensor,
    DiagnosisResultSensor,
    DiagnosisStepSensor,
    DiagnosisTestRunsSensor,
)
from .entity import (
    EnglishEntityId,
    SungrowBatteryEntity,
    SungrowDeviceEntity,
    SungrowEntity,
    SungrowExternalSensorDescription,
    SungrowSensorDescription,
    SungrowStringInverterEntity,
    as_reading,
)
from .external import combined, external_power
from .external_descriptions import EXTERNAL_SENSORS
from .route import ROUTE_LABELS, address
from .sensor_descriptions import SENSOR_DESCRIPTIONS
from .string_inverter_descriptions import STRING_INVERTER_DESCRIPTIONS
from .wallbox_descriptions import WALLBOX_DESCRIPTIONS

# The coordinator does the polling; entities never talk to the inverter.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Sungrow sensors."""
    runtime_data = entry.runtime_data

    # An iHomeManager or Logger entry is its diagnosis and nothing else.
    if runtime_data.is_device_only:
        async_add_entities(
            [
                DiagnosisProgressSensor(runtime_data),
                DiagnosisStepSensor(runtime_data),
                DiagnosisResultSensor(runtime_data),
            ]
        )
        return

    # A wallbox entry has the wallbox's readings and nothing else: no
    # inverter to say how it is reached, no diagnosis.
    if runtime_data.is_wallbox_only:
        assert runtime_data.wallbox is not None
        async_add_entities(
            SungrowWallboxSensor(runtime_data.wallbox, description)
            for description in WALLBOX_DESCRIPTIONS
        )
        # And the read-only diagnosis's three, so its owner can report it.
        async_add_entities(
            [
                DiagnosisProgressSensor(runtime_data),
                DiagnosisStepSensor(runtime_data),
                DiagnosisResultSensor(runtime_data),
            ]
        )
        return

    # Every entry, whatever its mode or kind: how this endpoint is reached.
    async_add_entities([SungrowConnectionSensor(entry)])

    # A diagnostics-only entry is made of the diagnosis and nothing else: three
    # sensors here and two buttons beside them, which between them give the
    # entry a device page -- a device reaches the registry only when an
    # entity carrying its `device_info` is added.
    #
    # An ordinary entry gets none of them. It has readings to show and an
    # owner who asked for those; the diagnosis is an action for them, leaving no
    # entity, no history and nothing to tidy up.
    if entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
        async_add_entities(
            [
                DiagnosisProgressSensor(runtime_data),
                DiagnosisStepSensor(runtime_data),
                DiagnosisResultSensor(runtime_data),
            ]
        )
        if not runtime_data.is_string_inverter:
            async_add_entities(
                [
                    DiagnosisNextStartSensor(runtime_data),
                    DiagnosisTestRunsSensor(runtime_data),
                    CapabilityTestStatusSensor(runtime_data),
                    *(
                        CapabilityTestCountSensor(runtime_data, bucket)
                        for bucket in ledger.BUCKETS
                    ),
                ]
            )
        return

    # An SG: its own map, and nothing else on this entry. An entity only for
    # a field the machine serves, because tracker and phase counts differ by
    # model and nothing ever removes an entity once made.
    if runtime_data.is_string_inverter:
        async_add_entities(
            (
                SungrowStringInverterEnergySensor
                if description.integrated
                else SungrowStringInverterSensor
            )(runtime_data.string_inverter[description.component], description)
            for description in STRING_INVERTER_DESCRIPTIONS
            if description.component in runtime_data.string_inverter
            and runtime_data.inverter_coordinator.device.serves(description.field)
        )
        return

    async_add_entities(
        _sensor_class(description)(runtime_data, description)
        for description in (*SENSOR_DESCRIPTIONS, *DERIVED_SENSORS)
        if runtime_data.serves(description)
    )

    # The corrections, when the owner has said another inverter shares the
    # supply. Gated on an option rather than on a capability -- nothing the
    # inverter answers reveals a generator it cannot see, which is the whole
    # problem -- so `corrects` asks the runtime data and not the hardware.
    async_add_entities(
        SungrowExternalSensor(runtime_data, description)
        for description in EXTERNAL_SENSORS
        if runtime_data.serves(description) and runtime_data.corrects(description)
    )

    # The pack's own entities, when this endpoint reaches one. Two gates
    # rather than one, because the pack's two blocks fail separately: a
    # WiNet-S can forward the summary and refuse the cell detail, and at
    # another house a different dongle firmware answered the cell block with
    # **zeros** -- which decode to values, so a successful read is not
    # evidence and a non-zero reading is what is required. Nothing ever
    # removes an entity, so ten of them reporting 0 V and module 0 forever
    # would have no recovery at all.
    battery = runtime_data.battery
    if battery is not None:
        descriptions = PACK_DESCRIPTIONS
        if runtime_data.battery_has_cells:
            descriptions += CELL_DESCRIPTIONS
        for module in runtime_data.battery_modules:
            descriptions += MODULE_DESCRIPTIONS[module]
        async_add_entities(
            SungrowBatterySensor(battery, description) for description in descriptions
        )

    # The wallbox, when one answered behind this endpoint. One gate, unlike
    # the battery's two: a wallbox either answers or it does not, and all
    # four of its blocks came back on the one unit ever measured. The `_raw`
    # codes and register 21313 have no descriptions, so there is nothing to
    # filter out here.
    wallbox = runtime_data.wallbox
    if wallbox is not None:
        async_add_entities(
            SungrowWallboxSensor(wallbox, description)
            for description in WALLBOX_DESCRIPTIONS
        )


class SungrowConnectionSensor(EnglishEntityId, SensorEntity):
    """How this endpoint is reached: directly, or through a module.

    Measured once at setup by register 6100 (`route.py`), so it changes only
    with a reload. Unknown where 6100 neither answered nor refused. WiFi
    against cable behind a WiNet-S no register says, so it is not a state.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_translation_key = "connection"

    def __init__(self, entry: SungrowConfigEntry) -> None:
        """Take what setup measured from the inverter's coordinator."""
        coordinator = entry.runtime_data.inverter_coordinator
        serial = coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_connection"
        self._attr_options = list(ROUTE_LABELS)
        self._attr_device_info = coordinator.device_info
        self._attr_native_value = coordinator.route
        self._attr_extra_state_attributes: dict[str, Any] = {
            "address": address(entry),
            CONF_HOST: entry.data.get(CONF_HOST),
            CONF_PORT: entry.data.get(CONF_PORT),
            "web_interface": coordinator.web_interface,
        }


def _sensor_class(
    description: SungrowSensorDescription,
) -> type[SungrowSensor | SungrowFlagsSensor | SungrowEnergySensor]:
    """Return the entity class an inverter sensor description asks for."""
    if description.flags:
        return SungrowFlagsSensor
    if description.history:
        return SungrowHistorySensor
    if description.integrated:
        return SungrowEnergySensor
    return SungrowSensor


#: The shortest gap an energy integral bridges, in seconds, however fast the
#: polling: two or three missed polls at the default tiers.
_MIN_GAP = 60.0


class _IntegratesPower(RestoreSensor):
    """A power reading's running integral, in kWh, kept across restarts.

    Shared by the hybrid's and the SG's tracker energy. Sampled on every
    update of the coordinator that reads the power, never between them; the
    arithmetic, and what it does across a gap, is
    `sungrow_modbus.energy_integral`.

    A gap is longer than three polls of that coordinator, or a minute,
    whichever is longer: a missed poll or two is bridged, an hour offline is
    not. Restarting Home Assistant is always a gap, since the clock is the
    event loop's.
    """

    _integral: EnergyIntegral | None = None

    def _power(self) -> float | None:
        """Return the power to integrate now, in W, or None."""
        raise NotImplementedError

    def _update_interval(self) -> timedelta | None:
        raise NotImplementedError

    @property
    def native_value(self) -> float | None:
        """Return the total, or None until the entity has been added."""
        return None if self._integral is None else round(self._integral.total_kwh, 4)

    async def _async_start_integral(self) -> None:
        """Pick up where the last run left off, then take the first sample."""
        total = 0.0
        last = await self.async_get_last_sensor_data()
        if last is not None and isinstance(last.native_value, (int, float)):
            total = max(float(last.native_value), 0.0)
        elif last is not None and last.native_value is not None:
            try:
                total = max(float(str(last.native_value)), 0.0)
            except ValueError:
                total = 0.0
        interval = self._update_interval()
        polls = 3 * interval.total_seconds() if interval else 0.0
        self._integral = EnergyIntegral(total, max_gap=max(polls, _MIN_GAP))
        self._sample()

    @callback
    def _sample(self) -> None:
        """Feed the current power into the integral."""
        if self._integral is not None:
            self._integral.update(self.hass.loop.time(), self._power())


class SungrowEnergySensor(SungrowEntity, _IntegratesPower):
    """Energy through one of the hybrid's trackers, from its derived power."""

    entity_description: SungrowSensorDescription

    def _power(self) -> float | None:
        """Return the tracker's power, or None while the entity is unavailable."""
        value = as_reading(self.native_value_source) if self.available else None
        return float(value) if isinstance(value, (int, float)) else None

    def _update_interval(self) -> timedelta | None:
        return self.coordinator.update_interval

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; nothing here is keyed on the id.

        Defining it opts this class's add hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11). Before 2026.11 the
        base class has no such method and nothing calls it.
        """
        parent = getattr(super(), "async_entity_id_changed", None)
        if parent is not None:
            parent(old_entity_id)

    async def async_added_to_hass(self) -> None:
        """Restore the total, then start sampling."""
        await super().async_added_to_hass()
        await self._async_start_integral()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Add this poll to the total, then write state."""
        self._sample()
        super()._handle_coordinator_update()


class SungrowWallboxSensor(SungrowDeviceEntity, SensorEntity):
    """A sensor reading one value a wallbox reports about itself."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the block did not answer."""
        return as_reading(self.native_value_source)


class SungrowStringInverterSensor(SungrowStringInverterEntity, SensorEntity):
    """A sensor reading one value off an SG."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the device has none."""
        return as_reading(self.coordinator.device.field(self.entity_description.field))


class SungrowStringInverterEnergySensor(SungrowStringInverterEntity, _IntegratesPower):
    """Energy through one of an SG's trackers, from voltage times current."""

    entity_description: SungrowSensorDescription

    def _power(self) -> float | None:
        """Return the tracker's power, or None while the entity is unavailable."""
        if not self.available:
            return None
        value = as_reading(self.coordinator.device.field(self.entity_description.field))
        return float(value) if isinstance(value, (int, float)) else None

    def _update_interval(self) -> timedelta | None:
        return self.coordinator.update_interval

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; nothing here is keyed on the id.

        Defining it opts this class's add hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11). Before 2026.11 the
        base class has no such method and nothing calls it.
        """
        parent = getattr(super(), "async_entity_id_changed", None)
        if parent is not None:
            parent(old_entity_id)

    async def async_added_to_hass(self) -> None:
        """Restore the total, then start sampling."""
        await super().async_added_to_hass()
        await self._async_start_integral()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Add this poll to the total, then write state."""
        self._sample()
        super()._handle_coordinator_update()


class SungrowBatterySensor(SungrowBatteryEntity, SensorEntity):
    """A sensor reading one value the pack reports about itself."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the block did not answer."""
        return as_reading(self.native_value_source)


class SungrowSensor(SungrowEntity, SensorEntity):
    """A sensor reading one field off the inverter."""

    entity_description: SungrowSensorDescription

    def __init__(
        self,
        runtime_data: SungrowRuntimeData,
        entity_description: SungrowSensorDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(runtime_data, entity_description)
        self._average: TimeWeightedAverage | None = None
        if entity_description.smoothed_over is not None:
            self._average = TimeWeightedAverage(entity_description.smoothed_over)

    @property
    def _reading(self) -> float | int | str | None:
        """Return the decoded register value."""
        return as_reading(self.native_value_source)

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or its moving average where one is asked for."""
        if self._average is None:
            return self._reading
        # Asked for the average as of now, not as of the last sample: a poll
        # that was missed must not make the value drift while the source sits
        # still. Samples are collected on the coordinator update.
        return self._average.value(self.hass.loop.time())

    @callback
    def async_entity_id_changed(self, old_entity_id: str) -> None:
        """Take a new entity id in place; nothing here is keyed on the id.

        Defining it opts this class's add hook out of Home Assistant's
        remove-and-re-add on a rename (2026.11 to 2027.11). Before 2026.11 the
        base class has no such method and nothing calls it.
        """
        parent = getattr(super(), "async_entity_id_changed", None)
        if parent is not None:
            parent(old_entity_id)

    async def async_added_to_hass(self) -> None:
        """Take the first sample from the reading already in hand."""
        await super().async_added_to_hass()
        if self._average is not None:
            self._sample()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Add this poll to the average, then write state."""
        if self._average is not None:
            self._sample()
        super()._handle_coordinator_update()

    @callback
    def _sample(self) -> None:
        """Feed the current reading into the average.

        Nothing is fed while the entity is unavailable. A component that fails
        a poll keeps its previous values, so the reading is still *there* --
        it is just a minute old and about to be a minute older, and averaging
        it in would report a moving average of a value nobody measured.
        Home Assistant's own filter ignores an unavailable source too.
        """
        assert self._average is not None
        value = self._reading if self.available else None
        self._average.update(
            self.hass.loop.time(),
            float(value) if isinstance(value, (int, float)) else None,
        )


class SungrowFlagsSensor(SungrowEntity, SensorEntity):
    """One fault or alarm word: how many named flags are set, and which.

    A count rather than the flags as text, so `> 0` is the automation and a
    history graph shows when something was set. The names go in `active`,
    which is always present -- an empty list on a good day -- so the recorder
    sees one shape.
    """

    entity_description: SungrowSensorDescription

    @property
    def _active(self) -> tuple[str, ...] | None:
        value = self.native_value_source
        return active(
            self.entity_description.field,
            int(value) if isinstance(value, (int, float)) else None,
        )

    @property
    def native_value(self) -> int | None:
        """Return how many named flags are set, or None where unread."""
        flags = self._active
        return None if flags is None else len(flags)

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Name the flags that are set."""
        return {"active": list(self._active or ())}


class SungrowHistorySensor(SungrowSensor):
    """Energy so far this month or this year, with the periods behind it.

    The state is the running total, so long-term statistics keep every month
    from now on. The `history` attribute is what the inverter itself still
    holds -- this year's months, or every year since the installation --
    which is the only record of the time before Home Assistant polled it.
    """

    @property
    def extra_state_attributes(self) -> dict[str, dict[str, float]]:
        """Return the months or years the inverter holds, by period."""
        return {
            "history": self.coordinator.device.derived.history(
                self.entity_description.field
            )
        }


class SungrowExternalSensor(SungrowEntity, SensorEntity):
    """A Sungrow reading plus the generation this inverter cannot see.

    The only entity here whose value is not entirely a Modbus read: the
    Sungrow half comes from the coordinator as usual, and the other half from
    entities another integration owns. `external.py` carries the arithmetic,
    the sign convention and why a missing source makes this unknown rather
    than unchanged.

    **Updated on the poll, not on the sources.** Home Assistant could push a
    new state the moment a foreign inverter reports, and does not, because
    the sum would then advance on the strength of its foreign half while the
    Sungrow half sat at whatever the last poll returned, advertising a
    freshness the number does not have. Written on the coordinator update
    instead, the entity is exactly as current as the reading it corrects --
    which is also what makes it safe to put beside `sensor.load_power` on a
    dashboard.
    """

    entity_description: SungrowExternalSensorDescription

    @property
    def _external(self) -> tuple[float | None, tuple[str, ...]]:
        """Return the foreign total, and any source that did not answer."""
        return external_power(self.hass, self._runtime_data.external_sources)

    @property
    def native_value(self) -> float | None:
        """Return the corrected reading, or None if any input is missing."""
        base = self.native_value_source
        if not isinstance(base, (int, float)) or isinstance(base, bool):
            return None
        external, _ = self._external
        return combined(float(base), external)

    @property
    def extra_state_attributes(self) -> dict[str, list[str]]:
        """Name the sources, and any of them that is why this is unknown.

        Both keys are always present, so the recorder sees one shape rather
        than an attribute that appears only on a bad day. `not_reporting` is
        the answer to the only question this entity provokes -- it went
        unknown, and nothing else on the device did.
        """
        _, missing = self._external
        return {
            "external_sources": list(self._runtime_data.external_sources),
            "external_sources_not_reporting": list(missing),
        }
