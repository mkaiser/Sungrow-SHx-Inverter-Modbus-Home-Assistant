"""Diagnostics support for the Sungrow SHx integration.

Surfaces the first-refresh register probe (which addresses the slave
answered, which it rejected as illegal, which it errored on) alongside
the latest decoded values and the per-key "unsupported" set. This is
the table used to reverse-engineer which registers a given inverter
firmware/model actually exposes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import SungrowConfigEntry


TO_REDACT_CONFIG = {CONF_HOST, CONF_UNIQUE_ID, "serial"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SungrowConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Sungrow config entry."""
    coordinator = entry.runtime_data

    probe = [
        {
            "input_type": input_type,
            "address": address,
            "count": info["count"],
            "status": info["status"],
            "exception_code": info["exception_code"],
            "keys": info["keys"],
            "registers": info["registers"],
        }
        for (input_type, address), info in sorted(coordinator.register_probe.items())
    ]

    return {
        "config_entry": async_redact_data(entry.as_dict(), TO_REDACT_CONFIG),
        "device": {
            "model": coordinator.model,
            "firmware": coordinator.firmware,
            "device_code": coordinator.device_code,
            "family": coordinator.family,
            "inverter_slave": coordinator.inverter_slave,
            "sbr_slave": coordinator.sbr_slave,
            "sbr_reachable": coordinator._sbr_reachable,  # noqa: SLF001
        },
        "register_probe": probe,
        "unsupported_keys": sorted(coordinator.unsupported_keys),
        "decoded": dict(coordinator.decoded),
    }
