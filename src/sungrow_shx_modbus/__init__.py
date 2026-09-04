"""Talk to Sungrow SHx hybrid inverters over Modbus.

A backend-neutral device library built on ``modbus-connection``: it is given a
``ModbusUnit`` and knows nothing about Home Assistant, so it can be used from
any Python program and tested without a network.
"""

from .components import InverterIdentity, InverterReadings
from .const import DEVICE_TYPES, MANUFACTURER, model_for
from .device import SungrowInverter
from .model import UpdateReport

__all__ = [
    "DEVICE_TYPES",
    "MANUFACTURER",
    "InverterIdentity",
    "InverterReadings",
    "SungrowInverter",
    "UpdateReport",
    "model_for",
]
