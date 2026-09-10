"""Base entity for the Sungrow Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from sungrow_modbus import Capability, present

from .coordinator import SungrowDataUpdateCoordinator, SungrowRuntimeData


@dataclass(frozen=True, kw_only=True)
class SungrowEntityDescription(EntityDescription):
    """Describe a Sungrow entity."""

    component: str
    """Attribute name of the component on SungrowInverter, for example readings."""

    field: str
    """Attribute name of the field on that component."""

    requires: Capability | None = None
    """A capability this entity needs, or None if every device has it.

    An entity is not created at all when its capability is absent, rather
    than created and left permanently unavailable. That is the difference
    between an integration that fits the hardware and the pile of dead
    entities legacy/doc/cleanup_entities.md exists to help people delete.
    """

    depends_on: tuple[str, ...] = ()
    """Register fields a derived value reads.

    A derived value is computed on read, so it is never stale in itself — but
    something has to decide when Home Assistant writes the new state. That is
    the **fastest** tier among these fields: attached to a slower one, the
    derived entity would visibly lag the raw sensors it is computed from,
    which is the one thing the template sensors it replaces never did.

    It also decides availability: a derived value is unavailable when any
    component it reads is.
    """

    legacy_name: str | None = None
    """The name the YAML package used for this entity.

    Legacy mode sets it as the entity's name, which is what makes the
    entity_id come out byte for byte the same — Home Assistant derives the
    object id from the name, and `_attr_name` short-circuits translation, so
    it holds in every interface language.
    """

    legacy_unique_id: str | None = None
    """The `unique_id` the YAML package registered this entity under.

    This, with `legacy_platform`, is what actually identifies a YAML entity.
    The entity_id cannot: 69 of the 127 carry nothing Sungrow-specific —
    `sensor.battery_level`, `sensor.grid_frequency`, `binary_sensor.
    battery_charging` — and matching on those would mistake another
    integration's entity for one of ours, then delete its registry entry to
    take the id.
    """

    legacy_platform: str | None = None
    """Which platform registered it: `modbus`, `template` or `filter`."""


@dataclass(frozen=True, kw_only=True)
class SungrowSensorDescription(SungrowEntityDescription, SensorEntityDescription):
    """Describe a Sungrow sensor."""

    legacy_only: bool = False
    """Create this only when the entry keeps the YAML package's entity ids.

    Seventeen sensors are a second copy of something the user already has --
    nine duplicating a `number` of the same name, eight raw codes whose
    decoded counterpart exists -- and they are here because the YAML package
    had them, not because anybody wants them. Legacy mode has to create them
    or history keyed to `sensor.battery_max_soc` stops; modern mode is the
    clean cut, and does not. `scripts/naming.py` holds the list and the
    reasoning.
    """

    smoothed_over: float | None = None
    """Report a moving average over this many seconds, not the raw reading.

    Home Assistant's `time_simple_moving_average`, which is what the YAML
    package's one `filter` entity asks for. Weighted by how long each value
    held rather than by how many samples arrived, so an inverter answering
    irregularly does not skew it -- see `sungrow_modbus.smoothing`.
    """


@dataclass(frozen=True, kw_only=True)
class SungrowExternalSensorDescription(SungrowSensorDescription):
    """Describe a Sungrow reading corrected for a generator it cannot see.

    `component` and `field` name the Sungrow value as they do everywhere
    else, so the uncorrected reading comes from `native_value_source`
    unchanged; the entity adds the foreign production to it. `depends_on`
    then places the entity on the tier that reads that value, which matters
    here: the corrected load must not visibly lag `sensor.load_power`, the
    number it exists to replace on a dashboard.
    """

    behind_meter_only: bool = False
    """Create this only where the foreign inverter is behind the same meter.

    True for the corrected load, because separately metered production never
    passed through the Sungrow's meter and its load figure is already right
    -- so the entity would be a knowing duplicate of `load_power`. False for
    site production, which is the sum of what the site makes however it is
    metered.
    """


@dataclass(frozen=True, kw_only=True)
class SungrowNumberDescription(SungrowEntityDescription, NumberEntityDescription):
    """Describe a Sungrow setting the user can change.

    The same register is read and written, so there is no separate state to
    keep in step — which is the whole reason the YAML package needed a
    `template number` plus a `modbus.write_register` action plus a
    `homeassistant.update_entity` call to see the result.
    """

    minimum_field: str | None = None
    """Read the lower bound from this register rather than the static one."""

    maximum_field: str | None = None
    """Read the upper bound from this register rather than the static one."""

    maximum_from_battery: bool = False
    """Cap at whichever is lower: the inverter's BDC rating or the pack's."""


@dataclass(frozen=True, kw_only=True)
class SungrowSwitchDescription(SungrowEntityDescription, SwitchEntityDescription):
    """Describe a Sungrow mode flag.

    The two codes travel with the description rather than being assumed. They
    are 0xAA and 0x55 for all three switches, which is exactly the kind of
    coincidence that becomes a bug the day a fourth one is not.
    """

    on_value: int
    off_value: int


@dataclass(frozen=True, kw_only=True)
class SungrowSelectDescription(SungrowEntityDescription, SelectEntityDescription):
    """Describe a Sungrow enumeration the user can change.

    The mapping goes both ways and is one table, so the label shown and the
    value written cannot disagree — which two separate maps, one for reading
    and one for writing, eventually would.
    """

    values: dict[str, int]
    """Option key to the value that goes in the register."""


@dataclass(frozen=True, kw_only=True)
class SungrowBinarySensorDescription(
    SungrowEntityDescription, BinarySensorEntityDescription
):
    """Describe a Sungrow binary sensor."""

    delay_on: float | None = None
    """Seconds the bit must stay set before this reports on.

    The YAML package pairs each power-flow bit with a `(delay)` twin so a
    dashboard card does not flicker every time the house crosses between
    importing and exporting. Going off is immediate, which is what
    `delay_on` means and why these are useful.
    """


class SungrowEntity(CoordinatorEntity[SungrowDataUpdateCoordinator]):
    """Base entity backed by one field of one component."""

    _attr_has_entity_name = True
    entity_description: SungrowEntityDescription

    def __init__(
        self,
        runtime_data: SungrowRuntimeData,
        entity_description: SungrowEntityDescription,
    ) -> None:
        """Initialize the entity."""
        # A derived value has no component of its own, so it is written by
        # the fastest tier it reads — otherwise it would visibly lag the raw
        # sensors it is computed from.
        if entity_description.depends_on:
            polled = runtime_data.fastest_component(entity_description.depends_on)
        else:
            polled = entity_description.component
        super().__init__(runtime_data.coordinator_for(polled))
        self._runtime_data = runtime_data
        self.entity_description = entity_description
        serial = self.coordinator.device.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{entity_description.key}"
        self._attr_device_info = self.coordinator.device_info

    @property
    def native_value_source(self) -> object:
        """Return the decoded field value, or None if it was never read."""
        device = self.coordinator.device
        component = (
            device.derived
            if self.entity_description.component == "derived"
            else device.component(self.entity_description.component)
        )
        return present(getattr(component, self.entity_description.field))

    @property
    def available(self) -> bool:
        """Whether every component this entity reads answered its last poll."""
        if not super().available:
            return False
        for component in self._sources:
            coordinator = self._runtime_data.coordinator_for(component)
            if coordinator.data is None or component in coordinator.data.failed:
                return False
        return True

    @property
    def _sources(self) -> set[str]:
        """Components this entity's value depends on."""
        description = self.entity_description
        if not description.depends_on:
            return {description.component}
        return {
            self._runtime_data.component_of(field) for field in description.depends_on
        }


class SungrowDeviceEntity(CoordinatorEntity):
    """Base for a value some device other than the inverter reports.

    Shared by the SBR pack and the wallbox, because their needs are the same
    and neither is the inverter's: one coordinator rather than four, so no
    tier to choose and no `depends_on`; a device of their own; and a value
    that may come from a property rather than a register, which is how a
    packed position word becomes a module and a cell, and how a status code
    becomes a word.

    The unique id is `{inverter serial}_{key}`, the shape the inverter's own
    entities use. Neither device's serial is used: an SBR reports none at all
    -- the whole 10740-10789 band was read and there is none in it -- and a
    wallbox reports one this project deliberately never reads, two registers
    below the model name it probes instead.

    No extra prefix on top of the key, although both first had one. Every key
    already begins with `battery_` or `wallbox_`, so a prefix produced
    `..._battery_battery_pack_voltage`; worse, it made these ids
    indistinguishable by prefix from the inverter's own `battery_charging`.
    What keeps them apart is that the keys are unique across the whole
    integration, asserted per device where a device page is what a user sees.
    """

    _attr_has_entity_name = True
    entity_description: SungrowEntityDescription

    def __init__(
        self,
        coordinator: CoordinatorEntity,
        entity_description: SungrowEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        serial = coordinator._inverter.serial_number
        assert serial is not None
        self._attr_unique_id = f"{serial}_{entity_description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value_source(self) -> object:
        """Return the value, whether it is a register or a decoded property."""
        return self.coordinator.device.field(self.entity_description.field)

    @property
    def available(self) -> bool:
        """Whether the block this entity reads answered its last poll.

        Per component, because these devices' blocks fail independently: a
        WiNet-S can refuse an SBR's cell block while its pack block answers,
        and a wallbox's slow components are only read every thirtieth poll.
        Without this, one refused block would take every entity on the device
        unavailable, which is a report that is wrong rather than incomplete.
        """
        if not super().available:
            return False
        report = self.coordinator.data
        if report is None:
            return False
        return self.entity_description.component not in report.failed


class SungrowBatteryEntity(SungrowDeviceEntity):
    """Base entity for a value the SBR pack reports about itself.

    Everything is inherited from `SungrowDeviceEntity`, which the wallbox
    shares. Kept as a name of its own because the platforms read better for
    it and because a pack has one thing worth saying that a wallbox does not:
    its two blocks are the case `available` was written for, a WiNet-S
    refusing the cell block while the pack block answers with identical
    values.
    """
