"""Sensor platform for the Sungrow Modbus integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from sungrow_modbus.smoothing import TimeWeightedAverage

from .battery_descriptions import CELL_DESCRIPTIONS, PACK_DESCRIPTIONS
from .coordinator import SungrowConfigEntry, SungrowRuntimeData
from .derived_descriptions import DERIVED_SENSORS
from .entity import (
    SungrowBatteryEntity,
    SungrowDeviceEntity,
    SungrowEntity,
    SungrowExternalSensorDescription,
    SungrowSensorDescription,
)
from .external import combined, external_power
from .external_descriptions import EXTERNAL_SENSORS
from .sensor_descriptions import SENSOR_DESCRIPTIONS
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
    async_add_entities(
        SungrowSensor(runtime_data, description)
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
    # removes an entity, so eight of them reporting 0 V and module 0 forever
    # would have no recovery at all.
    battery = runtime_data.battery
    if battery is not None:
        descriptions = PACK_DESCRIPTIONS
        if runtime_data.battery_has_cells:
            descriptions += CELL_DESCRIPTIONS
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


class SungrowWallboxSensor(SungrowDeviceEntity, SensorEntity):
    """A sensor reading one value a wallbox reports about itself."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the block did not answer."""
        value = self.native_value_source
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float, str)):
            return value
        return None


class SungrowBatterySensor(SungrowBatteryEntity, SensorEntity):
    """A sensor reading one value the pack reports about itself."""

    entity_description: SungrowSensorDescription

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or None where the block did not answer."""
        value = self.native_value_source
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float, str)):
            return value
        return None


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
        value = self.native_value_source
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float, str)):
            return value
        return None

    @property
    def native_value(self) -> float | int | str | None:
        """Return the reading, or its moving average where one is asked for."""
        if self._average is None:
            return self._reading
        # Asked for the average as of now, not as of the last sample: a poll
        # that was missed must not make the value drift while the source sits
        # still. Samples are collected on the coordinator update.
        return self._average.value(self.hass.loop.time())

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


class SungrowExternalSensor(SungrowEntity, SensorEntity):
    """A Sungrow reading plus the generation this inverter cannot see.

    The only entity here whose value is not entirely a Modbus read: the
    Sungrow half comes from the coordinator as usual, and the other half from
    entities another integration owns. `external.py` carries the arithmetic,
    the sign convention and why a missing source makes this unknown rather
    than unchanged.

    **Updated on the poll, not on the sources.** Home Assistant could push a
    new state the moment a foreign inverter reports, and that was rejected:
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
