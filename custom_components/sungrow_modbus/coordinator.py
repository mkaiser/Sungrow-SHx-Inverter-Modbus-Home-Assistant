"""Data update coordinator for the Sungrow Modbus integration."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from modbus_connection import ModbusConnectionError, ModbusError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from sungrow_modbus import (
    COMPONENTS,
    MANUFACTURER,
    TIER_COMPONENTS,
    Capability,
    SungrowInverter,
    UpdateReport,
)

from .const import DEFAULT_EXTERNAL_PLACEMENT, DOMAIN, PLACEMENT_BEHIND_METER

_LOGGER = logging.getLogger(__name__)

#: Register field name to the component holding it. Field names are unique
#: across components, which the library's tests assert.
FIELD_COMPONENTS: dict[str, str] = {
    name: attribute
    for attribute, component in COMPONENTS.items()
    for name in vars(component)
    if not name.startswith("_") and name not in {"register_space", "declared_fields"}
}

#: Component to the tier it belongs to. The interval is a setting now, so
#: what is fixed is which tier a component is in, not how often that is read.
COMPONENT_TIERS: dict[str, str] = {
    component: tier
    for tier, components in TIER_COMPONENTS.items()
    for component in components
}


class PausableCoordinator:
    """Lets a survey or control test have the link to itself for a while.

    A mixin rather than a base class because the three coordinators here are
    siblings, not a hierarchy: the inverter's tiers, the battery pack and the
    wallbox each subclass Home Assistant's `DataUpdateCoordinator` directly.
    What they do share is the endpoint -- one host, one port, one serialized
    connection -- so a pause that covered only one of them would not be a
    pause at all.
    """

    data: Any
    config_entry: ConfigEntry

    def _skip_while_paused(self) -> UpdateReport | None:
        """Return what to report while paused, or None to go ahead and poll.

        Returns the last report rather than raising `UpdateFailed`, so a paused
        entry looks like one whose values are a little old -- which is what it
        is -- and not like one that has lost its inverter.
        """
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None or not getattr(runtime, "polling_paused", False):
            return None
        return self.data if self.data is not None else UpdateReport()


class SungrowDataUpdateCoordinator(
    PausableCoordinator, DataUpdateCoordinator[UpdateReport]
):
    """Poll one group of the inverter's registers."""

    config_entry: SungrowConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        device: SungrowInverter,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=interval,
        )
        self.device = device
        self._poll = poll
        self._failing: set[str] = set()
        self._reload_scheduled = False

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Describe the inverter for the device registry."""
        serial = self.device.serial_number
        assert serial is not None
        identity = self.device.identity
        return dr.DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=MANUFACTURER,
            model=self.device.model,
            serial_number=serial,
            sw_version=identity.arm_software or None,
            # Only where the user chose one. Absent, Home Assistant falls
            # back to the entry title, which is the model -- and two SH10RTs
            # then produce one id and one `..._2`, the suffix recording click
            # order. The name step asks for something better, but only where
            # there is more than one inverter to tell apart, so most entries
            # carry no name here and behave exactly as they did before.
            **(
                {"name": name}
                if (name := self.config_entry.data.get(CONF_NAME))
                else {}
            ),
        )

    async def _async_update_data(self) -> UpdateReport:
        """Poll the inverter, unless a survey has asked for the link."""
        if (paused := self._skip_while_paused()) is not None:
            return paused
        try:
            report = await self._poll()
        except ModbusConnectionError as err:
            # Say what it usually is. A Sungrow accepts very few simultaneous
            # Modbus sessions, so by far the most common cause of a dropped
            # connection is a second client -- the YAML package still running,
            # another Home Assistant, EVCC, a logger -- rather than a fault.
            # The bare message ("Connection lost before response was
            # received") sends people looking at their network instead, which
            # is exactly what happened to the maintainer.
            raise UpdateFailed(
                f"Lost the connection to the inverter: {err}. A Sungrow "
                "inverter accepts very few Modbus connections at once, so "
                "check whether something else is polling it -- the "
                "modbus_sungrow.yaml package, another Home Assistant, or "
                "another tool."
            ) from err
        except ModbusError as err:
            # A timeout on the whole device lands here; a single block that
            # failed while the device is alive is reported per component
            # instead.
            raise UpdateFailed(f"Error communicating with the inverter: {err}") from err

        self._log_transitions(report)
        if not report.updated:
            raise UpdateFailed("No register block answered")
        self._async_recheck_capabilities()
        return report

    @callback
    def _async_recheck_capabilities(self) -> None:
        """Reload the entry if the device turns out to have more than we thought.

        Capabilities are probed once, after the first poll, because the entity
        list is built from them. A block that missed *that particular* poll
        therefore costs its entities until something probes again — and on a
        Sungrow a block missing a poll is ordinary rather than exceptional, so
        that is a real way to lose MPPT3 until the next restart.

        Failing setup instead would be worse: some measuring points are never
        forwarded over a WiNet-S, so an entry could then never finish setting
        up at all.

        Only **growth** reloads. A capability disappearing is far more likely
        to be one unlucky read than hardware being unplugged, and reloading on
        that would turn a blip into entity-registry churn.
        """
        if self._reload_scheduled:
            return
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            # Still inside the first refresh; capabilities are resolved just
            # after it, from exactly this data.
            return
        gained = self.device.capabilities() - runtime.capabilities
        if not gained:
            return
        self._reload_scheduled = True
        _LOGGER.info(
            "%s answered for %s after setup had decided it could not; "
            "reloading so those entities are created",
            self.name,
            ", ".join(sorted(c.value for c in gained)),
        )
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)

    def _log_transitions(self, report: UpdateReport) -> None:
        """Log a component going quiet, and coming back, exactly once."""
        for name, cause in report.failed.items():
            if name not in self._failing:
                self._failing.add(name)
                _LOGGER.warning(
                    "%s: %s did not answer and keeps its previous values: %s",
                    self.name,
                    name,
                    cause,
                )
        for name in report.updated & self._failing:
            self._failing.discard(name)
            _LOGGER.info("%s: %s is answering again", self.name, name)


class SungrowSubDeviceCoordinator(
    PausableCoordinator, DataUpdateCoordinator[UpdateReport]
):
    """Poll one device that lives behind the inverter's endpoint.

    The SBR pack and the wallbox are different hardware with different
    registers and different polling rhythms, and almost everything else about
    them is the same: both are reached through the inverter's connection, both
    hang off it in the interface, both are identified by **its** serial with a
    suffix because neither reports a usable one of its own, and both turn a
    `ModbusError` into an `UpdateFailed` that names which device failed.

    That was written twice, and the copies had drifted into storing the device
    under different attribute names -- `self.battery` and `self.wallbox` --
    behind a `device` property that existed only to paper over the difference.
    The inverter's own coordinator stores `self.device` directly, so this now
    does what that already did, and the two subclasses are left holding only
    what genuinely differs: how a model name is found, and how often each
    block is worth reading.
    """

    config_entry: SungrowConfigEntry

    kind: str
    """The suffix on the inverter's serial, the noun in this coordinator's
    name, and the word an error message uses. One string, three jobs, so they
    cannot disagree."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: SungrowConfigEntry,
        device: Any,
        inverter: SungrowInverter,
        interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.title} {self.kind}",
            update_interval=interval,
        )
        self.device = device
        self._inverter = inverter

    @property
    def inverter_serial(self) -> str:
        """Return the serial that identifies this device's entities.

        The **inverter's**, not this device's, and public because the entities
        need it: an SBR reports no serial anywhere in its seventeen registers,
        and a wallbox reports one two registers below the model name that this
        project deliberately never reads. So the only stable identity either
        device has is the inverter it is reached through.
        """
        serial = self._inverter.serial_number
        assert serial is not None
        return serial

    def _model(self) -> str | None:
        """Return this device's model name, or None if it cannot be read."""
        raise NotImplementedError

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Describe the device, hung off the inverter it is reached through.

        Its own device rather than more entities on the inverter's, because it
        is its own hardware with its own firmware and its own failure -- a
        dongle can lose the pack's cell block while the inverter answers
        everything. `via_device` is what puts it under the inverter in the
        interface, which is also where it sits physically.

        Identified by the **inverter's** serial with a suffix. An SBR reports
        no serial anywhere in its seventeen registers, which the survey checked
        by reading the whole 10740-10789 band. A wallbox does report one, at
        input 21200 -- and one reached a published fingerprint as
        `[16690, 13633]`, which decodes to `A25A`, before anybody thought about
        the second device in the house. Nothing here reads it.
        """
        serial = self.inverter_serial
        model = self._model()
        label = self.kind.capitalize()
        return dr.DeviceInfo(
            identifiers={(DOMAIN, f"{serial}-{self.kind}")},
            manufacturer=MANUFACTURER,
            model=model or label,
            name=model or label,
            via_device=(DOMAIN, serial),
        )

    @asynccontextmanager
    async def _reading(self) -> AsyncIterator[None]:
        """Turn a Modbus failure into an `UpdateFailed` that names the device.

        The two cases stay separate because they mean different things: a lost
        connection is about the link and will take the next poll with it, while
        an exception is about this device and this register.
        """
        try:
            yield
        except ModbusConnectionError as err:
            raise UpdateFailed(
                f"Lost the connection while reading the {self.kind}: {err}"
            ) from err
        except ModbusError as err:
            raise UpdateFailed(f"Error reading the {self.kind}: {err}") from err


class SungrowBatteryCoordinator(SungrowSubDeviceCoordinator):
    """Poll an SBR pack's own registers, on its own unit.

    One coordinator, not four. The pack has no tiers: seventeen registers in
    two reads, all of them things that move slowly -- a state of charge, a
    temperature, two lifetime counters. It follows the inverter's *medium*
    interval so that a house which has turned everything down does not get a
    battery polled faster than its inverter.

    It shares the inverter's connection, because one config entry is one
    endpoint and everything pointed at that host and port is serialized behind
    a single link. That is not a limitation to work around: a Sungrow accepts
    very few simultaneous sessions, and a second connection for the battery
    would compete with the inverter for one.
    """

    kind = "battery"

    def _model(self) -> str | None:
        """Name the pack from its capacity, which is all it tells anyone.

        The capacity comes from the *inverter*, not the pack, and only as a
        float -- anything else means the register did not answer, and a guess
        at the model from a missing capacity would be a label nobody could
        correct.
        """
        capacity = self._inverter.field("battery_capacity_high_precision")
        model: str | None = self.device.model(
            capacity if isinstance(capacity, float) else None
        )
        return model

    async def _async_update_data(self) -> UpdateReport:
        """Poll the pack, tolerating either block failing on its own."""
        if (paused := self._skip_while_paused()) is not None:
            return paused
        async with self._reading():
            report: UpdateReport = await self.device.async_update()
        return report


class SungrowWallboxCoordinator(SungrowSubDeviceCoordinator):
    """Poll a wallbox's own registers, on its own unit.

    **Two intervals, not one**, which is the difference from the battery and
    the reason this class exists at all rather than being a `kind` string. A
    pack's seventeen registers all move slowly; a wallbox has twenty-three
    that change while a car is charging and nine that change when somebody
    reconfigures it. So this coordinator fires on the inverter's *fast* tier
    and reads only `wallbox_live`, refreshing the rest every `SLOW_EVERY`
    firings -- reading the ratings every ten seconds would spend a Sungrow's
    scarce session time on a rated current that cannot change.

    It is reachable only as a unit behind the inverter's endpoint, never on an
    address of its own: measured at a site whose wallbox has its own LAN cable
    and still answered nowhere else.
    """

    kind = "wallbox"

    #: How many fast polls pass before the slow components are read again.
    #:
    #: 30 on the default 10-second tier is five minutes, which is about how
    #: quickly a person who has just changed a setting in Sungrow's app would
    #: like to see it. The identity and ratings are also read once at setup,
    #: so nothing waits five minutes to appear.
    SLOW_EVERY = 30

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the coordinator, and the counter the rhythm turns on."""
        super().__init__(*args, **kwargs)
        self._polls = 0

    def _model(self) -> str | None:
        """Name the wallbox from the model register it does answer."""
        model: str | None = self.device.model
        return model

    async def _async_update_data(self) -> UpdateReport:
        """Poll the live block, and the rest every `SLOW_EVERY` firings."""
        from sungrow_modbus.wallbox_device import FAST, SLOW

        if (paused := self._skip_while_paused()) is not None:
            # Deliberately before the counter moves. A paused firing is not a
            # poll, and letting it advance `_polls` would drift the slow block
            # out of its every-nth rhythm for the rest of the entry's life.
            return paused
        due = self._polls % self.SLOW_EVERY == 0
        self._polls += 1
        async with self._reading():
            report = await self.device.async_update(only=FAST)
            if due:
                report = report | await self.device.async_update(only=SLOW)
        # A slow component that was not read this time keeps the values it
        # had, so it must not be reported as failed -- an entity would go
        # unavailable for four minutes out of five.
        if not due and self.data is not None:
            report = UpdateReport(
                updated=report.updated | (self.data.updated - set(FAST)),
                failed={**self.data.failed, **report.failed},
            )
        return report


@dataclass
class SungrowRuntimeData:
    """Everything a platform needs to build its entities.

    One coordinator per poll interval, so a 5-second reading is not dragged
    along by 38 slow-moving totals. Entities look theirs up by the component
    they read, which is the only thing an entity description knows.
    """

    coordinators: dict[str, SungrowDataUpdateCoordinator]
    """Component attribute name to the coordinator that polls it."""

    capabilities: frozenset[Capability] = frozenset()
    """What this device turned out to have, probed once after the first poll."""

    intervals: dict[str, int] = field(default_factory=dict)
    """Seconds per tier, as configured. A tier missing here is not polled."""

    battery: SungrowBatteryCoordinator | None = None
    """The pack's coordinator, when this endpoint has one.

    `None` is the common case and not an error: most installations have no
    Sungrow pack, and a house on a WiNet-S may have one the dongle does not
    forward on this path.
    """

    wallbox: SungrowWallboxCoordinator | None = None
    """The wallbox's coordinator, when this endpoint has one.

    `None` is the common case: most installations have no Sungrow wallbox,
    and one that exists is reachable only through the endpoint the inverter
    is on -- never by sweeping for it.
    """

    battery_has_cells: bool = False
    """Whether the pack's cell block gave a reading worth building on.

    Separate from `battery` because the two fail separately. Measured both
    ways a dongle loses the cell data -- a refusal at one house, zeros at
    another -- and zeros are the dangerous one: they decode to values, so
    granting on them would create eight entities reporting 0 V and module 0
    forever, with nothing that ever removes an entity.
    """

    external_sources: tuple[str, ...] = ()
    """Entities reporting generation this inverter cannot see.

    Empty is the common case, and then the two entities in
    `external_descriptions.py` are not created at all -- there is nothing to
    correct for and a correction of zero is a duplicate reading.
    """

    external_placement: str = DEFAULT_EXTERNAL_PLACEMENT
    """Where that generation sits relative to the grid meter."""

    legacy_ids: bool = False
    """Whether this entry took over the YAML package's entity ids.

    Read by `serves`, because the answer decides which entities exist and not
    only what they are called: the seventeen `legacy_only` sensors are
    created for an entry carrying that history and for nothing else.
    """

    survey: Any = None
    """The `SurveyRunner` for this entry, or None before setup finishes.

    **Last, and it has to be.** Every caller in the tests builds this
    positionally -- `SungrowRuntimeData(coordinators, capabilities,
    intervals, ...)` -- so a field inserted anywhere above shifts all of
    them silently: `intervals` lands in `capabilities`, and ninety tests
    fail with a `KeyError` naming a component, a long way from the cause.
    Measured, by doing exactly that.

    Typed loosely on purpose: `survey.py` imports this module for the entry
    type, so naming the class here would close the circle. The platforms
    that use it import the real type.
    """

    @property
    def served_components(self) -> frozenset[str]:
        """Component names this entry polls, answered or not."""
        return frozenset(self.coordinators)

    def coordinator_for(self, component: str) -> SungrowDataUpdateCoordinator:
        """Return the coordinator that owns a component's data."""
        return self.coordinators[component]

    polling_paused: bool = False
    """True while a survey or control test wants the link to itself.

    **Declared last on purpose.** The first three fields of this dataclass are
    passed positionally where the entry is set up, so a field inserted among
    them shifts every argument after it -- which is exactly what happened on
    the first attempt at this, and surfaced as `KeyError: 'realtime'` from a
    lookup three files away.

    Read by every coordinator on this entry before it polls. Everything here
    shares one serialized connection to one endpoint, so a survey taken while
    the tiers keep firing is a survey taken under contention -- which is why
    every document published from a device page before 2026-09-18 carried
    `coordinators_paused: false`, honestly, and why it was worth fixing rather
    than explaining.

    Paused at the *poll* rather than by clearing `update_interval`, which would
    have needed a private Home Assistant call to cancel the timer already
    scheduled. A coordinator that wakes while this is set returns what it last
    had and touches no register, so entities hold their values instead of going
    unavailable for the length of a run.
    """

    @asynccontextmanager
    async def async_paused(self) -> AsyncIterator[None]:
        """Hold every coordinator on this entry off the link for the duration.

        Restored in a `finally`, so a survey that raises, times out or is
        cancelled cannot leave an entry that has silently stopped polling --
        which would look exactly like the integration having died.

        What it does **not** do is interrupt a poll already in flight. There is
        no safe way to, and it does not matter: one more read has already been
        paid for, and everything after it waits.
        """
        self.polling_paused = True
        _LOGGER.debug("Polling paused: a survey or control test has the link")
        try:
            yield
        finally:
            self.polling_paused = False
            _LOGGER.debug("Polling resumed")

    def serves(self, description: object) -> bool:
        """Whether this description should exist on this entry.

        Two separate questions, and both are answered here because a platform
        should not have to know either: is the component it reads being
        polled, and does this entity exist in this *mode* at all.
        """
        if getattr(description, "legacy_only", False) and not self.legacy_ids:
            return False
        required = getattr(description, "requires", None)
        if required is not None and required not in self.capabilities:
            return False
        depends = getattr(description, "depends_on", ())
        if depends:
            return all(self.component_of(f) in self.coordinators for f in depends)
        return getattr(description, "component", None) in self.coordinators

    def corrects(self, description: object) -> bool:
        """Whether a correction entity applies to how this house is wired.

        Separate from `serves`, which answers what the hardware and the mode
        allow. This answers something only the owner knows and only an option
        records, and it is the difference between an entity that says
        something new and one that copies `load_power` under a second name.
        """
        if not self.external_sources:
            return False
        if getattr(description, "behind_meter_only", False):
            return self.external_placement == PLACEMENT_BEHIND_METER
        return True

    def component_of(self, field: str) -> str:
        """Return the component a register field lives in."""
        return FIELD_COMPONENTS[field]

    def fastest_component(self, fields: tuple[str, ...]) -> str:
        """Return the component polled most often among these fields.

        A derived value is written when its coordinator fires, so it follows
        the quickest thing it reads — otherwise it would lag the raw sensors
        it is computed from.
        """
        components = {self.component_of(f) for f in fields}
        return min(components, key=self.interval_of)

    def interval_of(self, component: str) -> int:
        """Return how often a component is polled, as configured."""
        return self.intervals[COMPONENT_TIERS[component]]


type SungrowConfigEntry = ConfigEntry[SungrowRuntimeData]
