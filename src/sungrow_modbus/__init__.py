"""Talk to Sungrow hybrid inverters over Modbus.

A backend-neutral device library built on ``modbus-connection``: it is given a
``ModbusUnit`` and knows nothing about Home Assistant, so it can be used from
any Python program and tested without a network.
"""

from .capabilities import Capability, Family, family_for, known_absent, resolve
from .components import InverterIdentity, InverterReadings
from .const import DEVICE_TYPES, MANUFACTURER, model_for
from .derived import RUNNING_STATES, Derived
from .device import SungrowInverter
from .discovery import (
    DEFAULT_PORT,
    MAX_HOSTS,
    NetworkTooLarge,
    async_hostname,
    async_sweep,
    hosts_in,
    network_of,
)
from .model import UpdateReport
from .registers import COMPONENTS, TIERS

__all__ = [
    "COMPONENTS",
    "DEFAULT_PORT",
    "DEVICE_TYPES",
    "MANUFACTURER",
    "MAX_HOSTS",
    "RUNNING_STATES",
    "TIERS",
    "Capability",
    "Derived",
    "Family",
    "InverterIdentity",
    "InverterReadings",
    "NetworkTooLarge",
    "SungrowInverter",
    "UpdateReport",
    "async_hostname",
    "async_sweep",
    "family_for",
    "hosts_in",
    "known_absent",
    "model_for",
    "network_of",
    "resolve",
]
