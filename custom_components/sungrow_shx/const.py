"""Constants for the Sungrow SHx integration."""

DOMAIN = "sungrow_shx"

DEFAULT_NAME = "Sungrow SHx"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1

CONF_UNIT_ID = "unit_id"

# The YAML package polls in four tiers (5 / 10 / 60 / 600 s). Only the fast
# tier exists so far; the others arrive with the components that need them.
READINGS_SCAN_INTERVAL = 10
