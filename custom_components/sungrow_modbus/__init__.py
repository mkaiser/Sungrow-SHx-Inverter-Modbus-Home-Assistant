"""The Sungrow Modbus integration.

Built on the modernized Home Assistant Modbus architecture: this integration
collects its own connection details in its config flow and asks the modbus
integration for a unit, so several integrations pointed at the same inverter
share one serialized connection instead of competing for its few sessions.
"""

from __future__ import annotations

from datetime import timedelta
from functools import partial
import logging

from modbus_connection import ModbusConnectionError, ModbusError, ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.typing import ConfigType
from sungrow_modbus import DEFAULT_INTERVALS, TIER_COMPONENTS, SungrowInverter
from sungrow_modbus.battery import probe_units
from sungrow_modbus.battery_device import SungrowBattery
from sungrow_modbus.wallbox import probe_units as wallbox_probe_units
from sungrow_modbus.wallbox_device import SungrowWallbox

from .const import (
    CONF_ENTITY_IDS,
    CONF_EXTERNAL_PLACEMENT,
    CONF_EXTERNAL_SOURCES,
    CONF_INTERVALS,
    CONF_MODE,
    CONF_UNIT_ID,
    DEFAULT_EXTERNAL_PLACEMENT,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    INTERVAL_NEVER,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
)
from .coordinator import (
    SungrowBatteryCoordinator,
    SungrowConfigEntry,
    SungrowDataUpdateCoordinator,
    SungrowRuntimeData,
    SungrowWallboxCoordinator,
)
from .external_descriptions import EXTERNAL_SENSORS
from .migration import async_claim_legacy_ids, async_legacy_ids_with_history, keys_for
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


#: This integration is not configurable from YAML, and says so.
#:
#: Required because `async_setup` exists -- it registers the two actions --
#: and hassfest asks any integration with one to declare what it accepts from
#: `configuration.yaml`. The honest declaration is nothing: a Sungrow endpoint
#: is set up through the config flow, which is the only path that can probe
#: for what answers. `cv.config_entry_only_config_schema` is the helper for
#: exactly that, and it turns a `sungrow_modbus:` block in YAML into a clear
#: error rather than a silent no-op.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the actions, which belong to the integration not an entry.

    Registered once here rather than per entry: an action that targets a
    device does not need one registration per device, and re-registering
    on every reload would be a way to lose one.
    """
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up a Sungrow SHx inverter from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    inverter = SungrowInverter(unit)

    # Identity is read once and never polled: it cannot change while the
    # entry is loaded, and entities need the serial number to exist first.
    try:
        await inverter.async_update_identity()
    except ModbusConnectionError as err:
        raise ConfigEntryNotReady(
            f"Could not reach {entry.title}: {err}. A Sungrow inverter accepts "
            "very few Modbus connections at once, so check whether something "
            "else is polling it -- the modbus_sungrow.yaml package, another "
            "Home Assistant, or another tool."
        ) from err
    except ModbusError as err:
        raise ConfigEntryNotReady(
            f"Could not read the identity of {entry.title}: {err}"
        ) from err

    # Everything downstream builds unique ids out of the serial, so a device
    # that answered without one cannot be set up at all. That is a property of
    # the device rather than of this moment, so it is a permanent error --
    # retrying every 30 seconds forever would only fill the log. The config
    # flow refuses the same case at setup; this covers a device that changed
    # its mind, or an entry restored from a backup.
    if inverter.serial_number is None:
        raise ConfigEntryError(
            f"{entry.title} answered but reported no serial number, so its "
            "entities cannot be identified. Please open an issue with the "
            "model and firmware version."
        )

    # One coordinator per tier, at whatever interval the user has chosen --
    # defaulting to the YAML package's own 5, 10, 60 and 600 seconds, so
    # somebody who changes nothing sees the freshness they are used to.
    #
    # A tier set to never gets no coordinator, and its entities are therefore
    # not created. That is the point of the setting: a Sungrow accepts very
    # few Modbus connections, and the cheapest way to stop competing for one
    # is to stop asking for data nobody looks at.
    intervals = {**DEFAULT_INTERVALS, **entry.options.get(CONF_INTERVALS, {})}
    coordinators: dict[str, SungrowDataUpdateCoordinator] = {}
    for tier, components in TIER_COMPONENTS.items():
        interval = intervals.get(tier, DEFAULT_INTERVALS[tier])
        if interval == INTERVAL_NEVER:
            _LOGGER.debug(
                "%s: tier %s is set to never, not polling it", entry.title, tier
            )
            continue
        coordinator = SungrowDataUpdateCoordinator(
            hass,
            entry,
            inverter,
            partial(inverter.async_update_tier, tier),
            timedelta(seconds=interval),
        )
        await coordinator.async_config_entry_first_refresh()
        for component in components:
            coordinators[component] = coordinator

    if not coordinators:
        raise ConfigEntryError(
            f"Every poll tier of {entry.title} is set to never, so there is "
            "nothing to read. Set at least one interval in the integration's "
            "options."
        )

    # Probed after the first poll, not before: every optional block looks
    # absent until something has actually been read.
    capabilities = inverter.capabilities()
    _LOGGER.debug(
        "%s reports capabilities: %s",
        entry.title,
        ", ".join(sorted(c.value for c in capabilities)) or "none",
    )
    battery, battery_has_cells = await _async_battery(
        hass, entry, unit, inverter, intervals
    )
    wallbox = await _async_wallbox(hass, entry, inverter, intervals)

    legacy_ids = entry.data.get(CONF_ENTITY_IDS) == ENTITY_IDS_MIGRATE
    entry.runtime_data = SungrowRuntimeData(
        coordinators,
        capabilities,
        intervals,
        battery=battery,
        wallbox=wallbox,
        battery_has_cells=battery_has_cells,
        legacy_ids=legacy_ids,
        # Options rather than probed facts, and the only entities in this
        # integration whose existence an owner decides. Read here so a
        # platform sees a tuple and never the raw options dict; the entry
        # reloads when they change, which is what creates or removes the two
        # corrected entities.
        external_sources=tuple(entry.options.get(CONF_EXTERNAL_SOURCES, ())),
        external_placement=entry.options.get(
            CONF_EXTERNAL_PLACEMENT, DEFAULT_EXTERNAL_PLACEMENT
        ),
    )

    _async_drop_unused_corrections(hass, entry, inverter.serial_number)

    # Before the platforms, not after: an entity registered on the YAML
    # package's id continues its history, whereas renaming into that id
    # afterwards is refused outright. The user chose this at setup.
    #
    # And never for a diagnostics entry: claiming an id is a change to
    # somebody's registry made on behalf of entities that are not going to
    # exist. `_async_create` stores ENTITY_IDS_NEW for those, so this is
    # already false -- the mode is checked as well because the two must not
    # be able to disagree.
    if legacy_ids and entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DEVICES:
        serial = inverter.serial_number
        # Entities whose registry entry is gone but whose recorder rows are
        # not; claiming falls back to the un-renamed id for those.
        with_history = keys_for(await async_legacy_ids_with_history(hass))
        claimed = async_claim_legacy_ids(
            hass, entry, serial, capabilities, with_history
        )
        _LOGGER.info(
            "%s took over %d entity ids from the YAML package",
            entry.title,
            len(claimed),
        )

    _async_preview_notice(hass)

    # Every option changes something decided during setup -- which tiers get a
    # coordinator, how often each is polled, what a battery's maximum is -- so
    # there is nothing an option can change without rebuilding this.
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))

    # A diagnostics entry stops here: connected, identified, polling, and
    # with no entities anywhere. Everything above it is what a survey needs
    # -- the readings, the capability resolution, the device in the registry
    # so the diagnostics download has somewhere to hang -- and the platforms
    # are the part a contributor did not ask for. It is promoted from the
    # options flow, which is where the entity-ids question finally gets put.
    if entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
        _LOGGER.info(
            "%s set up for diagnostics only: %d components polling, no entities",
            entry.title,
            len(coordinators),
        )
        return True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_battery(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    unit: object,
    inverter: SungrowInverter,
    intervals: dict[str, int],
) -> tuple[SungrowBatteryCoordinator | None, bool]:
    """Find a Sungrow pack on this endpoint and start polling it, or not.

    Which unit id it answers on is **not** a setting and is never asked. It
    moves with the transport rather than with the hardware -- 200 over the
    inverter's own LAN port, 2 through a WiNet-S, measured at three houses --
    so `battery.probe_units` looks for it, discriminating against a slave
    inverter, which also lives at unit 2 on a direct connection and answers a
    device type code where a pack does not.

    Finding nothing is the common case and not a failure. Most installations
    have no Sungrow pack, and a house on a dongle may have one this path does
    not reach. Either way the inverter's own battery entities are unaffected:
    they read the inverter's view of the pack, which is a different set of
    registers on a different unit.
    """
    try:
        pack_unit = await probe_units(
            lambda unit_id: async_get_unit(
                hass,
                entry,
                ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
                unit_id,
            )
        )
    except (ModbusConnectionError, ModbusError) as err:
        # Not fatal, and not even worth a warning. The inverter is already
        # set up and working; this is an optional device that did not answer.
        _LOGGER.debug("%s: could not probe for a battery pack: %s", entry.title, err)
        return None, False

    if pack_unit is None:
        _LOGGER.debug("%s: no Sungrow battery pack on this endpoint", entry.title)
        return None, False

    battery = SungrowBattery(
        async_get_unit(
            hass,
            entry,
            ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
            pack_unit,
        ),
        pack_unit,
    )
    coordinator = SungrowBatteryCoordinator(
        hass,
        entry,
        battery,
        inverter,
        timedelta(seconds=intervals.get("medium", DEFAULT_INTERVALS["medium"])),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        # The pack answered its probe and then did not answer a full read.
        # That is a reason to skip the pack, not to fail an entry whose
        # inverter is polling fine -- so this is caught rather than raised.
        _LOGGER.debug(
            "%s: a battery answered at unit %s but its first read failed",
            entry.title,
            pack_unit,
        )
        return None, False

    _LOGGER.debug(
        "%s: battery pack on unit %s, cell data %s",
        entry.title,
        pack_unit,
        "present" if battery.has_cell_data else "absent on this path",
    )
    return coordinator, battery.has_cell_data


async def _async_wallbox(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    inverter: SungrowInverter,
    intervals: dict[str, int],
) -> SungrowWallboxCoordinator | None:
    """Find a wallbox behind this endpoint and start polling it, or not.

    Asked, never swept for. Measured at the one site with a wallbox: a full
    /24 found Modbus TCP on two addresses, the inverter and its dongle, and
    the wallbox answered **only** as unit 3 behind the dongle -- never at 248
    and never on an address of its own, despite having its own LAN cable. So
    a config flow cannot discover a wallbox by looking for one; it has to ask
    the endpoint it already has.

    The probe reads the model *name*, not the serial two registers below it,
    and not the device type code: a name is self-validating where a code has
    to be matched against a three-entry table, and reading the name keeps a
    serial out of the probe entirely.

    Finding nothing is the common case and never fails the entry.
    """
    try:
        wallbox_unit = await wallbox_probe_units(
            lambda unit_id: async_get_unit(
                hass,
                entry,
                ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
                unit_id,
            )
        )
    except (ModbusConnectionError, ModbusError) as err:
        _LOGGER.debug("%s: could not probe for a wallbox: %s", entry.title, err)
        return None

    if wallbox_unit is None:
        _LOGGER.debug("%s: no Sungrow wallbox on this endpoint", entry.title)
        return None

    device = SungrowWallbox(
        async_get_unit(
            hass,
            entry,
            ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
            wallbox_unit,
        ),
        wallbox_unit,
    )
    coordinator = SungrowWallboxCoordinator(
        hass,
        entry,
        device,
        inverter,
        timedelta(seconds=intervals.get("fast", DEFAULT_INTERVALS["fast"])),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        # Answered its probe and then failed a full read. A reason to skip the
        # wallbox, not to fail an entry whose inverter is polling fine.
        _LOGGER.debug(
            "%s: a wallbox answered at unit %s but its first read failed",
            entry.title,
            wallbox_unit,
        )
        return None

    _LOGGER.debug(
        "%s: wallbox on unit %s, model %s",
        entry.title,
        wallbox_unit,
        device.model or "not named",
    )
    return coordinator


#: Raised while this is a preview, and taken out when it is not.
#:
#: The version number says the same thing to a machine -- a PEP 440
#: pre-release is one `pip` will not install without `--pre` -- and the
#: integration's name says it in the Add integration dialog. Neither is read
#: by somebody who already has it running, and this is: one line in Settings >
#: Repairs, which is where a tester looks when they wonder what is going on.
#:
#: Not fixable, because there is nothing to fix; it is a statement, and it
#: goes away when the preview does.
PREVIEW_ISSUE = "preview_release"


def _async_preview_notice(hass: HomeAssistant) -> None:
    """Say once, where a tester will see it, that names may still change."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        PREVIEW_ISSUE,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=PREVIEW_ISSUE,
        learn_more_url=(
            "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant"
            "/blob/proper-ha-integration/doc/entity_name_review.md"
        ),
    )


@callback
def _async_drop_unused_corrections(
    hass: HomeAssistant, entry: SungrowConfigEntry, serial: str | None
) -> None:
    """Delete the registry entries of corrections this house no longer wants.

    The one place this integration removes an entity, and the exception is
    principled. Everywhere else an absent entity means absent *hardware*,
    which can come back -- a third tracker at sunrise, a dongle that starts
    forwarding a block -- so nothing is ever removed and capabilities only
    grow. These two are different: they exist because an owner named another
    inverter, and they stop existing because the same owner unnamed it. There
    is no reading that could bring them back on its own.

    Left alone, Home Assistant restores the registry entry as `unavailable`
    forever, so a page that was turned off keeps a dead sensor on every
    dashboard card it reached. That is worse than untidy: `restored` entities
    look like a broken integration rather than a setting somebody changed.
    """
    if serial is None:
        return
    registry = er.async_get(hass)
    runtime = entry.runtime_data
    for description in EXTERNAL_SENSORS:
        if runtime.serves(description) and runtime.corrects(description):
            continue
        entity_id = registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{serial}_{description.key}"
        )
        if entity_id is not None:
            _LOGGER.debug(
                "%s: removing %s, no longer corrected", entry.title, entity_id
            )
            registry.async_remove(entity_id)


async def _async_options_changed(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> None:
    """Reload, because the options decide how the entry is built."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Unload a config entry.

    The shared connection closes itself once the last entry holding a unit on
    it unloads, so there is nothing to tear down here.
    """
    if entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
        # Nothing was forwarded, so there is nothing to unload. Asking Home
        # Assistant to unload platforms that were never set up is harmless
        # but reads as though this entry had entities.
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
