"""The Sungrow Modbus integration.

Built on the modernized Home Assistant Modbus architecture: this integration
collects its own connection details in its config flow and asks the modbus
integration for a unit, so several integrations pointed at the same inverter
share one serialized connection instead of competing for its few sessions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import timedelta
from functools import partial
import logging
from typing import Any

from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusTcpParams,
    ModbusUnit,
)

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.helpers.typing import ConfigType
from sungrow_modbus import (
    DEFAULT_INTERVALS,
    TIER_COMPONENTS,
    Capability,
    Inverter,
    SungrowInverter,
    SungrowStringInverter,
)
from sungrow_modbus.addresses import DIRECT_ONLY_PROBE
from sungrow_modbus.battery import probe_units
from sungrow_modbus.battery.device import SungrowBattery
from sungrow_modbus.hybrid_inverter.capabilities import with_sungrow_battery
from sungrow_modbus.string_inverter import TIER_COMPONENTS as STRING_INVERTER_TIERS
from sungrow_modbus.wallbox import (
    UNITS as WALLBOX_UNITS,
    probe_units as wallbox_probe_units,
)
from sungrow_modbus.wallbox.device import SungrowWallbox

from .battery_descriptions import MODULE_DESCRIPTIONS
from .const import (
    CONF_ENTITY_IDS,
    CONF_EXPORT_WRITE_SCALE,
    CONF_EXPORT_WRITE_SCALE_FIRMWARE,
    CONF_EXPORT_WRITE_SCALE_PROBE,
    CONF_EXTERNAL_PLACEMENT,
    CONF_EXTERNAL_SOURCES,
    CONF_INTERVALS,
    CONF_KIND,
    CONF_MODE,
    CONF_TLS,
    CONF_UNIT_ID,
    CONF_WALLBOX_HOST,
    DEFAULT_EXTERNAL_PLACEMENT,
    DOMAIN,
    ENTITY_IDS_MIGRATE,
    INTERVAL_NEVER,
    KIND_IHOMEMANAGER,
    KIND_STRING_INVERTER,
    KIND_WALLBOX,
    MODE_DEVICES,
    MODE_DIAGNOSTICS,
    UNIT_247_KINDS,
    WALLBOX_TLS_PORT,
    WALLBOX_TLS_UNIT,
)
from .coordinator import (
    InverterCoordinator,
    SungrowBatteryCoordinator,
    SungrowConfigEntry,
    SungrowDataUpdateCoordinator,
    SungrowRuntimeData,
    SungrowStringInverterCoordinator,
    SungrowWallboxCoordinator,
)
from .diagnosis import DiagnosisRunner
from .download import async_register as async_register_download
from .external_descriptions import EXTERNAL_SENSORS
from .links import wallbox_tls_params
from .migration import (
    async_claim_legacy_ids,
    async_legacy_ids_with_history,
    keys_for,
    stored_legacy_slot,
)
from .route import async_direct, connection_text, route_key, web_interface
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TIME,
]

#: What a diagnostics-only entry sets up: the diagnosis, capability test and
#: history buttons, the continuous switch and the four sensors that watch the
#: runs, and nothing else.
#:
#: Not nothing, because the diagnosis lives on the device page, and a device
#: reaches the registry only when an entity carrying its `device_info` is
#: added -- an entry with no entities has no page to put a button on. The
#: platforms themselves decide what to build in this mode -- `sensor.py` adds
#: the diagnosis's three and returns.
#:
#: And **only** this mode. An ordinary entry gets no diagnosis entities: its
#: owner installed this for solar readings and should not carry diagnostic
#: tooling they never asked for, in their registry, their history or their
#: entity pickers. They help through the `run_diagnosis` action instead, which
#: leaves nothing behind at all. Deleting an entry removes its entities
#: either way -- asserted in `test_diagnosis_device_page.py` -- but the cleanest
#: cleanup is still the one that was never needed.
DIAGNOSTIC_PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

#: What an ordinary SG entry sets up: its readings, and nothing that writes.
#: Read only by decision, until a write has been watched on one.
STRING_INVERTER_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

#: What an iHomeManager or Logger entry sets up: its diagnosis's buttons and
#: sensors, which are also what gives it a device page.
UNIT_247_PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

#: What a wallbox entry sets up: the readings its device carries, and its
#: diagnosis and capability test. Nothing writes outside that test, which
#: writes only with the owner's leave.
WALLBOX_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _platforms(entry: SungrowConfigEntry) -> list[Platform]:
    """Return what this entry forwards, so setup and unload cannot disagree."""
    if entry.data.get(CONF_KIND) in UNIT_247_KINDS:
        return UNIT_247_PLATFORMS
    if (
        entry.data.get(CONF_KIND) != KIND_WALLBOX
        and entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS
    ):
        return DIAGNOSTIC_PLATFORMS
    if entry.data.get(CONF_KIND) == KIND_STRING_INVERTER:
        return STRING_INVERTER_PLATFORMS
    if entry.data.get(CONF_KIND) == KIND_WALLBOX:
        return WALLBOX_PLATFORMS
    return PLATFORMS


#: This integration is not configurable from YAML, and says so.
#:
#: Required because `async_setup` exists -- it registers the four actions --
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
    # The download view too, and for the same reason: one registration per
    # Home Assistant, not one per entry. Doing it here is what lets
    # `download.async_register` keep no state at all.
    async_register_download(hass)
    return True


@callback
def _unit_factory(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> Callable[[int], ModbusUnit]:
    """Return "give me this endpoint's unit N", for the probes that sweep ids.

    Both probes need it because **which unit id answers depends on the
    transport**: an SBR answers 200 on an inverter's own LAN port and 2 through
    a WiNet-S, and a wallbox answers 3 only through the dongle. So neither
    device can be asked for at a fixed address; each has to try the ids its
    library knows, and each needs a way to get a unit for an id it has not
    tried yet.

    Every unit it hands back is on the same host and port, which is the point:
    one config entry is one inverter reached through one endpoint, and
    everything pointed at it shares one serialized connection rather than
    competing for a Sungrow's few sessions.
    """
    params = ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    return lambda unit_id: async_get_unit(hass, entry, params, unit_id)


async def _async_connect(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> tuple[ModbusUnit, SungrowInverter, str]:
    """Open the shared unit and read the identity, or say why setup cannot go on.

    The two failures are deliberately different kinds. A link that will not
    answer is `ConfigEntryNotReady`, because it is about this moment and the
    next attempt may work; a device that answers without a serial number is
    `ConfigEntryError`, because every unique id downstream is built from that
    serial and retrying every thirty seconds forever would only fill the log.
    """
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    inverter = SungrowInverter(unit)
    serial = await _async_read_identity(entry, inverter)
    return unit, inverter, serial


async def _async_read_identity(entry: SungrowConfigEntry, inverter: Inverter) -> str:
    """Read the identity block, hybrid or SG, and return the serial, or raise.

    The two failures are the ones `_async_connect` describes.
    """
    # Identity is read once and never polled: it cannot change while the
    # entry is loaded, and entities need the serial number to exist first.
    try:
        await inverter.async_update_identity()
    except ModbusConnectionError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_unreachable",
            translation_placeholders={"title": entry.title, "error": str(err)},
        ) from err
    except ModbusError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="identity_unread",
            translation_placeholders={"title": entry.title, "error": str(err)},
        ) from err

    # The config flow refuses the same case at setup; this covers a device
    # that changed its mind, or an entry restored from a backup.
    serial = inverter.serial_number
    if serial is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="no_serial",
            translation_placeholders={"title": entry.title},
        )
    return serial


async def _async_read_firmware(
    entry: SungrowConfigEntry, inverter: SungrowInverter
) -> tuple[str | None, str | None]:
    """Read both firmware strings, before the first poll and before capabilities.

    Firmware decides what is read at all -- one measured version closes the
    connection on blocks the first poll would otherwise ask for -- and what
    some entities may do. Knowing it after the first poll is too late for the
    first and a guess for the second.

    A string that does not answer is None, and setup carries on: an inverter
    that withholds its firmware is gated by nothing in either direction. A
    lost link is `ConfigEntryNotReady`, as for the identity just before.
    """
    try:
        report = await inverter.async_update_firmware()
    except ModbusConnectionError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="firmware_unread",
            translation_placeholders={"title": entry.title, "error": str(err)},
        ) from err
    for name, failure in report.failed.items():
        _LOGGER.debug("%s: %s did not answer at setup: %s", entry.title, name, failure)
    _LOGGER.debug(
        "%s runs firmware %s",
        entry.title,
        " / ".join(v or "unknown" for v in inverter.firmware_strings),
    )
    return inverter.firmware_strings


async def _async_tier_coordinators(
    hass: HomeAssistant, entry: SungrowConfigEntry, inverter: SungrowInverter
) -> tuple[dict[str, int], dict[str, SungrowDataUpdateCoordinator]]:
    """Build one coordinator per poll tier, and refresh each once.

    The intervals default to the YAML package's own 5, 10, 60 and 600 seconds,
    so somebody who changes nothing sees the freshness they are used to.

    A tier set to never gets no coordinator, and its entities are therefore not
    created. That is the point of the setting: a Sungrow accepts very few
    Modbus connections, and the cheapest way to stop competing for one is to
    stop asking for data nobody looks at. Setting *every* tier to never is the
    one case that cannot be honoured, because an entry that reads nothing has
    nothing to offer -- so it is refused with the sentence that says how to
    undo it.
    """
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
            translation_domain=DOMAIN,
            translation_key="nothing_to_poll",
            translation_placeholders={"title": entry.title},
        )
    return intervals, coordinators


async def _async_take_over_legacy_ids(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    serial: str,
    capabilities: frozenset[Capability],
    legacy_ids: bool,
) -> None:
    """Claim the YAML package's entity ids, where the owner asked for that.

    Called **before the platforms**, and that ordering is the whole mechanism:
    an entity registered on the YAML package's id continues its history,
    whereas renaming into that id afterwards is refused outright with nothing
    but a log line.

    Never for a diagnostics entry. Claiming an id is a change to somebody's
    registry made on behalf of entities that are not going to exist.
    `_async_create` stores `ENTITY_IDS_NEW` for those, so `legacy_ids` is
    already false -- the mode is checked as well because the two must not be
    able to disagree.
    """
    if not legacy_ids or entry.data.get(CONF_MODE, MODE_DEVICES) != MODE_DEVICES:
        return
    # Entities whose registry entry is gone but whose recorder rows are not;
    # claiming falls back to the un-renamed id for those.
    #
    # Asked of **this inverter's slot**, and both halves must use the same one.
    # Querying the unsuffixed history and then claiming suffixed ids from it
    # would let a second inverter take its own ids on the strength of the first
    # one's recorder rows -- a claim that looks justified and is supported by
    # nothing.
    slot = stored_legacy_slot(entry)
    if slot is None:
        # A numbered YAML slot existed and nothing tied this inverter to one,
        # so any legacy id here may be another inverter's history.
        _LOGGER.info(
            "%s claims no YAML package ids: which of its inverter slots this "
            "device was could not be determined",
            entry.title,
        )
        return
    with_history = keys_for(await async_legacy_ids_with_history(hass, slot), slot)
    claimed = async_claim_legacy_ids(hass, entry, serial, capabilities, with_history)
    _LOGGER.info(
        "%s took over %d entity ids from the YAML package",
        entry.title,
        len(claimed),
    )


async def _async_setup_string_inverter(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> bool:
    """Set up an SG: its own map, read only, and none of the hybrid's machinery.

    No firmware gate, no capability table, no battery or wallbox probe, no
    YAML package ids and no capability test: each is built on the hybrid's map
    and means nothing here. What it shares with a hybrid entry is the link,
    the device page, the tiers' intervals and the diagnosis.
    """
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    inverter = SungrowStringInverter(unit, entry.data[CONF_UNIT_ID])
    await _async_read_identity(entry, inverter)

    intervals = {**DEFAULT_INTERVALS, **entry.options.get(CONF_INTERVALS, {})}
    coordinators: dict[str, SungrowStringInverterCoordinator] = {}
    for tier, components in STRING_INVERTER_TIERS.items():
        interval = intervals.get(tier, DEFAULT_INTERVALS[tier])
        if interval == INTERVAL_NEVER:
            continue
        coordinator = SungrowStringInverterCoordinator(
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
            translation_domain=DOMAIN,
            translation_key="nothing_to_poll",
            translation_placeholders={"title": entry.title},
        )

    entry.runtime_data = SungrowRuntimeData(
        {},
        intervals=intervals,
        inverter_device_id=_async_register_inverter(
            hass, entry, coordinators, await _async_route(inverter)
        ),
        string_inverter=coordinators,
    )
    entry.runtime_data.diagnosis = DiagnosisRunner(hass, entry)
    entry.async_on_unload(entry.runtime_data.diagnosis.async_shutdown)
    _async_preview_notice(hass)
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))
    entry.runtime_data.built_from = _built_from(entry)
    await hass.config_entries.async_forward_entry_setups(entry, _platforms(entry))
    return True


async def _async_setup_wallbox(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up a wallbox that is an entry of its own, at its own address.

    Modbus inside TLS on port 516, unit 248, read only. There is no inverter
    here: no tiers, no capabilities, no YAML package ids. The
    device is identified by the wallbox's **own** serial, which is read before
    anything else and without which nothing can be named.
    """
    host = entry.data[CONF_HOST]
    unit = async_get_unit(hass, entry, wallbox_tls_params(host), WALLBOX_TLS_UNIT)
    intervals = {**DEFAULT_INTERVALS, **entry.options.get(CONF_INTERVALS, {})}
    coordinator = SungrowWallboxCoordinator(
        hass,
        entry,
        SungrowWallbox(unit, WALLBOX_TLS_UNIT),
        None,
        timedelta(seconds=intervals.get("fast", DEFAULT_INTERVALS["fast"])),
    )
    await coordinator.async_config_entry_first_refresh()
    if coordinator.own_serial is None:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="identity_unread",
            translation_placeholders={
                "title": entry.title,
                "error": "the wallbox serial did not read",
            },
        )
    entry.runtime_data = SungrowRuntimeData(
        {}, intervals=intervals, wallbox=coordinator
    )
    # A diagnosis and a capability test of its own, so a wallbox owner can
    # report from here and its controls can be measured.
    from .wallbox_diagnosis import WallboxDiagnosisRunner

    runner = WallboxDiagnosisRunner(hass, entry)
    entry.runtime_data.diagnosis = runner
    entry.async_on_unload(runner.async_shutdown)
    await runner.async_load_ledger()
    _async_preview_notice(hass)
    await hass.config_entries.async_forward_entry_setups(entry, WALLBOX_PLATFORMS)
    return True


async def _async_read_ihomemanager(entry: SungrowConfigEntry, unit: Any) -> Any:
    """Bind an iHomeManager and read what it is, its software version included.

    Read once before its device is registered, so the device page carries the
    version from the start; `slowest` keeps it fresh afterwards.
    """
    from sungrow_modbus.ihomemanager import SungrowIHomeManager

    device = SungrowIHomeManager(unit)
    try:
        await device.async_update_tier("slowest")
    except ModbusError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_unreachable",
            translation_placeholders={"title": entry.title, "error": str(err)},
        ) from err
    return device


async def _async_ihomemanager_coordinators(
    hass: HomeAssistant, entry: SungrowConfigEntry, device: Any, info: dr.DeviceInfo
) -> dict[str, Any]:
    """Poll an iHomeManager by tier: its coordinators, by component."""
    from sungrow_modbus.ihomemanager import TIER_COMPONENTS

    from .ihomemanager import SungrowIHomeManagerCoordinator

    intervals = {**DEFAULT_INTERVALS, **entry.options.get(CONF_INTERVALS, {})}
    coordinators: dict[str, Any] = {}
    for tier, components in TIER_COMPONENTS.items():
        interval = intervals.get(tier, DEFAULT_INTERVALS[tier])
        if interval == INTERVAL_NEVER:
            continue
        coordinator = SungrowIHomeManagerCoordinator(
            hass, entry, device, tier, timedelta(seconds=interval), info
        )
        await coordinator.async_config_entry_first_refresh()
        for component in components:
            coordinators[component] = coordinator
    return coordinators


async def _async_setup_unit_247(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up an iHomeManager or a Logger: its diagnosis, and its readings.

    Unit 247, on the port the search found it on, plain or inside TLS. Neither
    device documents a serial, so the entry's unique id (kind, host and port)
    names the device. Asked what it is once here, so an entry whose device no
    longer answers waits rather than offering a diagnosis of nothing; a link
    down is not a refusal, and is retried. An iHomeManager's readings are
    polled as well (`ihomemanager.py`); a Logger, which no unit has answered
    yet, shows its diagnosis only.
    """
    from sungrow_modbus import MANUFACTURER, ihomemanager, logger
    from sungrow_modbus.discovery import IHOMEMANAGER_UNIT, async_identify_unit_247_on

    from .device_diagnosis import (
        DeviceDiagnosisRunner,
        unit_247_builder,
        unit_247_summary,
    )
    from .links import unit_247_params

    kind = entry.data[CONF_KIND]
    unit = async_get_unit(
        hass,
        entry,
        unit_247_params(
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            tls=entry.data.get(CONF_TLS, False),
        ),
        IHOMEMANAGER_UNIT,
    )
    identity = await async_identify_unit_247_on(unit)
    if identity is None or identity.kind != kind:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="setup_unreachable",
            translation_placeholders={
                "title": entry.title,
                "error": f"no {kind} answered at unit {IHOMEMANAGER_UNIT}",
            },
        )
    assert entry.unique_id is not None
    polled_device = (
        await _async_read_ihomemanager(entry, unit)
        if kind == KIND_IHOMEMANAGER
        else None
    )
    version = None if polled_device is None else polled_device.software_version
    info = dr.DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer=MANUFACTURER,
        model=identity.model,
        name=entry.title,
        **({"sw_version": version} if version else {}),
    )
    entry.runtime_data = SungrowRuntimeData({}, device=(entry.unique_id, info))
    if polled_device is not None:
        entry.runtime_data.ihomemanager = await _async_ihomemanager_coordinators(
            hass, entry, polled_device, info
        )
    package = ihomemanager if kind == KIND_IHOMEMANAGER else logger
    runner = DeviceDiagnosisRunner(
        hass, entry, unit_247_builder(entry, unit, package), unit_247_summary
    )
    entry.runtime_data.diagnosis = runner
    entry.async_on_unload(runner.async_shutdown)
    _async_preview_notice(hass)
    await hass.config_entries.async_forward_entry_setups(entry, UNIT_247_PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Bring an entry an older version stored up to this version's names."""
    from .entry_migration import async_migrate_entry as migrate

    return await migrate(hass, entry)


async def async_setup_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Set up a Sungrow inverter from a config entry, hybrid or string."""
    if entry.data.get(CONF_KIND) == KIND_STRING_INVERTER:
        return await _async_setup_string_inverter(hass, entry)
    if entry.data.get(CONF_KIND) == KIND_WALLBOX:
        return await _async_setup_wallbox(hass, entry)
    if entry.data.get(CONF_KIND) in UNIT_247_KINDS:
        return await _async_setup_unit_247(hass, entry)
    _unit, inverter, serial = await _async_connect(hass, entry)
    firmware = await _async_read_firmware(entry, inverter)

    intervals, coordinators = await _async_tier_coordinators(hass, entry, inverter)

    # Probed after the first poll, not before: every optional block looks
    # absent until something has actually been read.
    capabilities = inverter.capabilities()
    _LOGGER.debug(
        "%s reports capabilities: %s",
        entry.title,
        ", ".join(sorted(c.value for c in capabilities)) or "none",
    )
    battery, battery_has_cells, battery_modules = await _async_battery(
        hass, entry, inverter, intervals
    )
    # Only now: the pack is on a unit of its own, which the inverter's
    # registers cannot see, and an SBR is what lets a battery's write bounds
    # come from its datasheet rather than from BMS current times voltage.
    capabilities = with_sungrow_battery(
        capabilities,
        pack_found=battery is not None,
        capacity_kwh=_capacity(inverter),
    )
    wallbox = await _async_wallbox(hass, entry, inverter, intervals)
    inverter_device_id = _async_register_inverter(
        hass, entry, coordinators, await _async_route(inverter)
    )

    legacy_ids = entry.data.get(CONF_ENTITY_IDS) == ENTITY_IDS_MIGRATE
    entry.runtime_data = SungrowRuntimeData(
        coordinators,
        capabilities,
        intervals,
        firmware=firmware,
        output_type=inverter.output_type,
        inverter_device_id=inverter_device_id,
        battery=battery,
        wallbox=wallbox,
        battery_has_cells=battery_has_cells,
        battery_modules=battery_modules,
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

    # The diagnosis's own state, and the view that hands the finished document
    # to whoever ran it. Both in every mode: a diagnostics entry is the one
    # that exists *for* this.
    entry.runtime_data.diagnosis = DiagnosisRunner(hass, entry)
    entry.async_on_unload(entry.runtime_data.diagnosis.async_shutdown)
    # Capability test runs kept from before a restart fold back in, so a
    # collection over a day survives one.
    await entry.runtime_data.diagnosis.async_load_ledger()

    _async_drop_unused_corrections(hass, entry, serial)

    await _async_take_over_legacy_ids(hass, entry, serial, capabilities, legacy_ids)

    _async_preview_notice(hass)

    # Every option changes something decided during setup -- which tiers get a
    # coordinator, how often each is polled, what a battery's maximum is -- so
    # there is nothing an option can change without rebuilding this.
    entry.async_on_unload(entry.add_update_listener(_async_options_changed))
    entry.runtime_data.built_from = _built_from(entry)

    # Did a capability test stop halfway through putting things back? Checked
    # here rather than fixed here: writing a register during setup is exactly
    # what this integration does not do, so this raises a repair and the owner
    # confirming it is the explicit action that does the writing.
    await _async_check_capability_test(hass, entry)

    # A diagnostics entry gets the diagnosis's buttons and sensors and no
    # readings. Everything above is what a diagnosis needs; the value platforms
    # are the part a contributor did not ask for. It is promoted from the
    # options flow, which is where the entity-ids question gets put.
    if entry.data.get(CONF_MODE, MODE_DEVICES) == MODE_DIAGNOSTICS:
        _LOGGER.info(
            "%s set up for diagnostics only: %d components polling, "
            "the diagnosis mode, start, stop and history controls, and no "
            "readings",
            entry.title,
            len(coordinators),
        )
        _async_remove_retired_diagnosis_entities(hass, entry)
        await hass.config_entries.async_forward_entry_setups(
            entry, DIAGNOSTIC_PLATFORMS
        )
        return True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


@callback
def _async_remove_retired_diagnosis_entities(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> None:
    """Drop the diagnosis buttons and switch the mode select replaced.

    Diagnostic entities with no history worth keeping; left in the registry
    they would sit on the device page as unavailable controls.
    """
    from .diagnosis_entities import RETIRED_ENTITIES

    serial = entry.runtime_data.inverter_coordinator.device.serial_number
    registry = er.async_get(hass)
    for domain, key in RETIRED_ENTITIES:
        entity_id = registry.async_get_entity_id(domain, DOMAIN, f"{serial}_{key}")
        if entity_id is not None:
            registry.async_remove(entity_id)


@callback
def _async_register_inverter(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    coordinators: Mapping[str, InverterCoordinator[Any]],
    route: str | None = None,
) -> str:
    """Put the inverter in the device registry before any entity, and return its id.

    Up front because a battery or a wallbox names the inverter it hangs off
    by **device id** (`via_device_id`), and that id exists only once the
    inverter is registered. Left to the platforms, a sub-device's entities
    could be added before the inverter's. Core's `sofar` does the same.
    """
    # The address, and the path 6100 measured, under the firmware on the
    # device page; every coordinator carries it, so every entity agrees.
    connection = connection_text(entry, route)
    link = web_interface(entry, route)
    for coordinator in coordinators.values():
        coordinator.connection = connection
        coordinator.route = route
        coordinator.web_interface = link
    device_info = next(iter(coordinators.values())).device_info
    return (
        dr.async_get(hass)
        .async_get_or_create(config_entry_id=entry.entry_id, **device_info)
        .id
    )


async def _async_route(inverter: Any) -> str | None:
    """Measure the path once, at setup (`route.route_key`)."""
    direct = await async_direct(inverter.async_read(DIRECT_ONLY_PROBE))
    try:
        module = inverter.field("communication_module_firmware_version")
    except (AttributeError, KeyError):
        module = None
    return route_key(direct, module if isinstance(module, str) else None)


async def _async_check_capability_test(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> None:
    """Raise a repair when a capability test left registers changed.

    A snapshot outlives the run that took it precisely so that this can happen:
    it is written before the first write and removed only once everything in it
    is back. Finding one here means the last run did not get to the end of its
    restore, and the registers it names may still hold a test's values rather
    than the owner's.

    Deliberately not repaired automatically. `doc/architecture.md` states
    the rule -- the integration never writes a register during setup or reload,
    only on an explicit user action -- and a setup that silently wrote to an
    inverter would be a worse thing to have built than the problem it fixed.
    """
    from .capability_test import async_leftover
    from .repairs import async_clear, async_raise

    snapshot = await async_leftover(hass, entry)
    if snapshot is None:
        async_clear(hass, entry)
        return
    _LOGGER.warning(
        "%s: a capability test did not finish putting things back. %d register(s) "
        "may still hold its values%s. See Settings -> Repairs.",
        entry.title,
        len(snapshot.values),
        ", and the inverter may still be stopped"
        if snapshot.stopped_at is not None
        else "",
    )
    async_raise(hass, entry, snapshot)


def _capacity(inverter: SungrowInverter) -> float | None:
    """Return register 5639's capacity in kWh, or None where it did not read."""
    try:
        value = inverter.field("battery_capacity_high_precision")
    except (AttributeError, KeyError):
        return None
    return None if value is None else float(value)


async def _async_battery(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    inverter: SungrowInverter,
    intervals: dict[str, int],
) -> tuple[SungrowBatteryCoordinator | None, bool, tuple[int, ...]]:
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
        pack_unit = await probe_units(_unit_factory(hass, entry))
    except (ModbusConnectionError, ModbusError) as err:
        # Not fatal, and not even worth a warning. The inverter is already
        # set up and working; this is an optional device that did not answer.
        _LOGGER.debug("%s: could not probe for a battery pack: %s", entry.title, err)
        return None, False, ()

    if pack_unit is None:
        _LOGGER.debug("%s: no Sungrow battery pack on this endpoint", entry.title)
        return None, False, ()

    battery = SungrowBattery(_unit_factory(hass, entry)(pack_unit), pack_unit)
    coordinator = SungrowBatteryCoordinator(
        hass,
        entry,
        battery,
        inverter,
        timedelta(seconds=intervals.get("medium", DEFAULT_INTERVALS["medium"])),
    )
    # The first read takes the module block too, to count the modules; the
    # poll keeps it only while one of their entities is enabled.
    battery.poll_modules = True
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
        return None, False, ()

    _LOGGER.debug(
        "%s: battery pack on unit %s, cell data %s",
        entry.title,
        pack_unit,
        "present" if battery.has_cell_data else "absent on this path",
    )
    modules = battery.modules.fitted_modules
    battery.poll_modules = _module_entity_enabled(hass, coordinator, modules)
    return coordinator, battery.has_cell_data, modules


def _module_entity_enabled(
    hass: HomeAssistant,
    coordinator: SungrowBatteryCoordinator,
    modules: tuple[int, ...],
) -> bool:
    """Whether any of these modules' entities is enabled in the registry.

    Asked at setup only, which is enough: enabling an entity reloads the
    entry. A first setup finds none, the entities being disabled by default.
    """
    registry = er.async_get(hass)
    for module in modules:
        for description in MODULE_DESCRIPTIONS[module]:
            entity_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"{coordinator.inverter_serial}_{description.key}"
            )
            entity = registry.async_get(entity_id) if entity_id else None
            if entity is not None and entity.disabled_by is None:
                return True
    return False


async def _async_wallbox(
    hass: HomeAssistant,
    entry: SungrowConfigEntry,
    inverter: SungrowInverter,
    intervals: dict[str, int],
) -> SungrowWallboxCoordinator | None:
    """Find this inverter's wallbox and start polling it, or not.

    Two places it can answer, both measured on an AC22E-01: as unit 3 behind
    a WiNet-S, which is asked here of the endpoint this entry already has,
    and as unit 248 at its **own address**, over TLS on port 516 -- never
    through the inverter's own LAN port. The second is an option
    (`CONF_WALLBOX_HOST`), because nothing on a network says which TLS host
    is whose wallbox. With it set, the endpoint is not asked as well.

    Either way the device, its entities and their unique ids are the same:
    they are built from the inverter's serial, so a wallbox moved from the
    dongle to its own address keeps its history.

    The probe reads the model *name*, not the serial below it (input
    registers 21201-21206) and not the device type code: a name is
    self-validating where a code has to be matched against a three-entry
    table, and reading the name keeps a serial out of the probe entirely.

    Finding nothing is the common case and never fails the entry.
    """
    unit_for: Callable[[int], ModbusUnit]
    if host := entry.options.get(CONF_WALLBOX_HOST):
        # Its own address, over TLS. The endpoint is not probed as well: a
        # dongle would find the same wallbox at unit 3 and make it twice.
        direct = async_get_unit(hass, entry, wallbox_tls_params(host), WALLBOX_TLS_UNIT)

        def unit_for(_unit_id: int) -> ModbusUnit:
            return direct

        units: tuple[int, ...] = (WALLBOX_TLS_UNIT,)
    else:
        unit_for = _unit_factory(hass, entry)
        units = WALLBOX_UNITS
    try:
        wallbox_unit = await wallbox_probe_units(unit_for, units)
    except (ModbusConnectionError, ModbusError) as err:
        _LOGGER.debug("%s: could not probe for a wallbox: %s", entry.title, err)
        return None

    if wallbox_unit is None:
        if host:
            _LOGGER.warning(
                "%s: no wallbox answered at its configured address over TLS "
                "(port %s, unit %s); polling it is skipped until it does",
                entry.title,
                WALLBOX_TLS_PORT,
                WALLBOX_TLS_UNIT,
            )
        else:
            _LOGGER.debug("%s: no Sungrow wallbox on this endpoint", entry.title)
        return None

    device = SungrowWallbox(unit_for(wallbox_unit), wallbox_unit)
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
            "/blob/proper-ha-integration/doc/entity_names.md"
        ),
    )


@callback
def _async_drop_unused_corrections(
    hass: HomeAssistant, entry: SungrowConfigEntry, serial: str
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
    """Reload, because the options decide how the entry is built.

    Except when nothing setup reads has changed. The export limit's write
    scale is stored in `data` by the entity, in the middle of a write, and a
    reload there would tear the entity down under its own service call.
    """
    built_from = entry.runtime_data.built_from
    if built_from is not None and built_from == _built_from(entry):
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _built_from(entry: SungrowConfigEntry) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return what setup builds an entry from: everything but what it never reads."""
    measured = {
        CONF_EXPORT_WRITE_SCALE,
        CONF_EXPORT_WRITE_SCALE_FIRMWARE,
        CONF_EXPORT_WRITE_SCALE_PROBE,
    }
    data = {k: v for k, v in entry.data.items() if k not in measured}
    return data, dict(entry.options)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: SungrowConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Let an owner delete a battery or wallbox this entry no longer finds.

    Never removed automatically: a pack or wallbox that did not answer at this
    setup may answer at the next, and its device carries the history. Only
    the owner knows it is gone for good. The inverter and every device this
    setup found refuse, because the next poll would recreate them.
    """
    runtime = entry.runtime_data
    if runtime.is_device_only:
        # An iHomeManager or Logger entry has its own device, and nothing else.
        _prefix, info = runtime.device
        return not device_entry.identifiers & info["identifiers"]
    infos = (
        [] if runtime.is_wallbox_only else [runtime.inverter_coordinator.device_info]
    )
    infos += [
        c.device_info for c in (runtime.battery, runtime.wallbox) if c is not None
    ]
    in_use = set().union(*(info["identifiers"] for info in infos))
    return not device_entry.identifiers & in_use


async def async_remove_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> None:
    """Clean up what outlives the entry, which is the capability test's snapshot.

    Everything else this integration owns is either in the entry or in the
    registries, and Home Assistant removes those itself. The snapshot is not:
    it is a `Store`, so it is a file in `.storage/` keyed by entry id, and
    deleting the entry would otherwise leave it there for good.

    Worth being clear about what this does **not** mean. A snapshot present at
    this moment is a house still carrying a run's values, and removing the
    entry throws away the only record of which ones. There is nothing to be
    done about that from here -- the entry is already going -- but it is the
    reason `repairs.py` raises the issue at *setup*, where somebody can still
    act on it.
    """
    # Imported here rather than at module level, matching
    # `_async_check_capability_test` above: `check_pinned_library.py` reads this
    # module's `sungrow_modbus` imports, and `capability_test` pulls in the
    # library's own `capability_test`, which only a released wheel provides.
    from .capability_test import async_forget

    await async_forget(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: SungrowConfigEntry) -> bool:
    """Unload a config entry.

    The shared connection closes itself once the last entry holding a unit on
    it unloads, so there is nothing to tear down here.
    """
    # Whatever was forwarded, and only that: unloading a platform that was
    # never set up is harmless, but the pair must match or the next reload
    # forwards onto entities that were left behind.
    return await hass.config_entries.async_unload_platforms(entry, _platforms(entry))
