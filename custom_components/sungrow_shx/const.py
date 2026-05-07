"""Constants for the Sungrow SHx Inverter integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import (  # noqa: F401  (re-exported for intra-package use)
    CONF_HOST,
    CONF_PORT,
    CONF_SLAVE,
    Platform,
)

DOMAIN: Final = "sungrow_shx"
MANUFACTURER: Final = "Sungrow"

PLATFORMS: Final[list[Platform]] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]

# ---------------------------------------------------------------------------
# Config / options keys
# ---------------------------------------------------------------------------
# Standard keys (CONF_HOST, CONF_PORT, CONF_SLAVE) are imported above from
# homeassistant.const. Only Sungrow-specific keys are defined here.
CONF_SBR_SLAVE: Final = "sbr_slave"
CONF_BATTERY_MAX_POWER: Final = "battery_max_power"
CONF_WAIT_MS: Final = "wait_ms"
CONF_SCAN_INTERVAL_REALTIME: Final = "scan_interval_realtime"
CONF_SCAN_INTERVAL_FAST: Final = "scan_interval_fast"
CONF_SCAN_INTERVAL_MEDIUM: Final = "scan_interval_medium"
CONF_SCAN_INTERVAL_SLOWEST: Final = "scan_interval_slowest"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_PORT: Final = 502
DEFAULT_SLAVE: Final = 1
DEFAULT_SBR_SLAVE: Final = 200
DEFAULT_BATTERY_MAX_POWER: Final = 5000  # Watts
DEFAULT_WAIT_MS: Final = 5  # ms between Modbus requests

# Polling intervals (seconds) matching the legacy YAML package behavior.
DEFAULT_SCAN_REALTIME: Final = 5
DEFAULT_SCAN_FAST: Final = 10
DEFAULT_SCAN_MEDIUM: Final = 60
DEFAULT_SCAN_SLOWEST: Final = 600
