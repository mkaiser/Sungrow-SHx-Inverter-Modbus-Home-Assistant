"""Diagnostics for the Sungrow Modbus integration.

A Sungrow inverter answers a different subset of its register map depending on
model, firmware, wiring and whether a WiNet-S is in the path. Nearly every bug
report on this project therefore begins with a round of "which model, what is
connected, and which registers actually answer" — questions the integration
already knows the answers to. This puts them in one file the user can download
and attach.

What it deliberately includes, because it is what the questions turn out to
need:

* the **capability resolution**, and not just its result — which capabilities
  the model table vetoed and which the device's own registers confirmed, since
  a disagreement between the two is a bug in the table;
* **why an entity does not exist.** "MPPT3 is missing" is the single most
  common report, and the answer is almost always that the inverter reported
  the specification's 0xFFFF sentinel. That is now stated rather than inferred;
* **per-component poll health**, because a poll losing one block is normal
  operation here and the interesting part is *which* block and for how long;
* **which entity ids are in use**, so a migration that half-worked is visible.

Serial number and host are redacted: a diagnostics file is written to be
pasted into a public issue.

The raw register dump is **off by default** and enabled in the integration's
options. It performs a full extra read of every mapped address, which through
a WiNet-S is slow enough to disturb polling, so it is opt-in rather than free.
"""

from __future__ import annotations

from typing import Any

from modbus_connection import ModbusError

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry
from sungrow_modbus import Capability
from sungrow_modbus.capabilities import OUTPUT_TYPES, known_absent, probe

from .const import CONF_REGISTER_DUMP, CONF_UNIT_ID, DOMAIN
from .coordinator import COMPONENT_TIERS, SungrowConfigEntry
from .migration import DESCRIPTIONS, legacy_entity_id

#: Identifying details, redacted because this file is meant to be shared.
#: `sungrow_inverter_serial` is here as well as `serial_number` because the
#: serial is *also* a register reading — key-based redaction of the identity
#: block alone leaves it sitting in the readings, which is what
#: `test_the_serial_and_host_are_redacted` exists to catch.
TO_REDACT = {CONF_HOST, "serial_number", "sungrow_inverter_serial"}

#: Register addresses holding the serial number, excluded from the raw dump.
#: A dump is words, not strings, so no amount of key redaction reaches it —
#: the range has to be dropped by address.
SERIAL_ADDRESSES = range(4989, 4999)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> dict[str, Any]:
    """Return everything worth knowing about this entry."""
    runtime = entry.runtime_data
    device = next(iter(runtime.coordinators.values())).device

    report: dict[str, Any] = {
        "entry": async_redact_data(
            {
                CONF_HOST: entry.data.get(CONF_HOST),
                CONF_PORT: entry.data.get(CONF_PORT),
                CONF_UNIT_ID: entry.data.get(CONF_UNIT_ID),
                "entity_ids": entry.data.get("entity_ids"),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "device": async_redact_data(_device(device), TO_REDACT),
        "capabilities": _capabilities(device, runtime.capabilities),
        "polling": _polling(runtime),
        "entities": _entities(hass, entry, runtime),
        "readings": async_redact_data(_readings(device), TO_REDACT),
    }

    if entry.options.get(CONF_REGISTER_DUMP, False):
        report["register_dump"] = await _async_register_dump(device)

    return report


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: SungrowConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return the same report from the device page.

    One config entry is one inverter today, so there is nothing to narrow
    down; when a wallbox or a battery becomes its own device this is where
    that split belongs.
    """
    return await async_get_config_entry_diagnostics(hass, entry)


def _device(device: Any) -> dict[str, Any]:
    """Identify the hardware, in the terms a register document uses."""
    code = device.device_type_code
    identity = device.identity
    return {
        "model": device.model,
        "device_type_code": None if code is None else f"0x{code:04X}",
        "output_type": OUTPUT_TYPES.get(device.output_type, device.output_type),
        "serial_number": device.serial_number,
        "firmware": {
            "arm": identity.arm_software or None,
            "dsp": identity.dsp_software or None,
        },
    }


def _capabilities(device: Any, resolved: frozenset[Capability]) -> dict[str, Any]:
    """Show how each capability was decided, not only what was decided.

    The three sources disagree sometimes, and that disagreement is the useful
    part: a capability the family table calls absent but the device answered
    for means the table is wrong, which is a bug worth a report.
    """
    probed = probe(device._read_or_none)
    absent = known_absent(device.device_type_code)
    return {
        "resolved": sorted(c.value for c in resolved),
        "answered_when_probed": sorted(c.value for c in probed),
        "absent_for_this_model": sorted(c.value for c in absent),
        "table_contradicted_by_device": sorted(c.value for c in (probed & absent)),
    }


def _polling(runtime: Any) -> list[dict[str, Any]]:
    """Report each poll tier, and which of its blocks answered."""
    rows: list[dict[str, Any]] = []
    for component, coordinator in sorted(runtime.coordinators.items()):
        data = coordinator.data
        rows.append(
            {
                "component": component,
                "tier": COMPONENT_TIERS.get(component),
                "interval_seconds": runtime.interval_of(component),
                "last_poll_succeeded": coordinator.last_update_success,
                "answered_last_poll": data is not None and component in data.updated,
                "error": (
                    str(data.failed[component])
                    if data is not None and component in data.failed
                    else None
                ),
            }
        )
    return rows


def _entities(
    hass: HomeAssistant, entry: SungrowConfigEntry, runtime: Any
) -> dict[str, Any]:
    """Say what exists, what does not, and why not.

    "Sensor X is missing" is the most common report this project gets, and the
    answer is nearly always a capability gate rather than a fault. Stating the
    gate turns a support round-trip into a one-line answer.
    """
    registry = er.async_get(hass)
    serial = next(iter(runtime.coordinators.values())).device.serial_number

    created: list[str] = []
    legacy_ids = 0
    skipped: list[dict[str, str]] = []

    for platform, description in DESCRIPTIONS:
        if not runtime.serves(description):
            skipped.append(
                {
                    "key": description.key,
                    "reason": (
                        f"requires {description.requires.value}"
                        if description.requires is not None
                        else "component not polled"
                    ),
                }
            )
            continue
        entity_id = registry.async_get_entity_id(
            platform, DOMAIN, f"{serial}_{description.key}"
        )
        if entity_id is None:
            continue
        created.append(entity_id)
        if entity_id == legacy_entity_id(platform, description):
            legacy_ids += 1

    return {
        "created": len(created),
        "on_legacy_entity_ids": legacy_ids,
        "on_device_scoped_entity_ids": len(created) - legacy_ids,
        "not_created": skipped,
    }


def _readings(device: Any) -> dict[str, Any]:
    """Every decoded register value, and the ones that came back unavailable.

    A field decoding to None is the device reporting the specification's
    0xFFFF sentinel, which is how it says a measuring point is not there. That
    is a different thing from a block that failed to answer, and separating
    the two is most of diagnosing "my sensor is unavailable".
    """
    values: dict[str, Any] = {}
    unavailable: list[str] = []
    for name in sorted(device._fields):
        try:
            value = device.field(name)
        except (AttributeError, KeyError):
            continue
        if value is None:
            unavailable.append(name)
        else:
            values[name] = value
    return {"values": values, "reported_unavailable": unavailable}


async def _async_register_dump(device: Any) -> dict[str, Any]:
    """Read every mapped address raw, one component at a time.

    Opt-in, because this is a second full read of the register map on top of
    the ordinary polling. Failures are recorded per component rather than
    aborting: a block that does not answer is exactly what somebody
    downloading this is trying to find out about.
    """
    dump: dict[str, Any] = {}
    for name in sorted(vars(device)):
        component = getattr(device, name)
        if not hasattr(component, "async_read_raw"):
            continue
        try:
            raw = await component.async_read_raw(notify=False)
        except ModbusError as err:
            dump[name] = {"error": str(err)}
            continue
        dump[name] = {
            space: {
                str(address): value
                for address, value in sorted(targets.items())
                if address not in SERIAL_ADDRESSES
            }
            for space, targets in raw.items()
        }
    return dump
