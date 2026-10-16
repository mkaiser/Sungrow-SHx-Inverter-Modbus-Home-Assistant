"""The SBR battery: a device of its own, on a unit of its own.

Reached through the inverter's connection on whichever unit answers
(`discovery`), read as a device with its own map (`device`, `registers`),
and the source of the charge ceiling the integration offers (`power`).
"""

from .device import SungrowBattery
from .discovery import IMPLAUSIBLE, INVERTER_TYPE, PACK_UNITS, PACK_VOLTAGE, probe_units
from .power import (
    CAPACITY_TOLERANCE_FRACTION,
    FALLBACK_W,
    MODELS,
    BatteryModel,
    ceiling,
    model_for_capacity,
    power_from_bms,
)

__all__ = [
    "CAPACITY_TOLERANCE_FRACTION",
    "FALLBACK_W",
    "IMPLAUSIBLE",
    "INVERTER_TYPE",
    "MODELS",
    "PACK_UNITS",
    "PACK_VOLTAGE",
    "BatteryModel",
    "SungrowBattery",
    "ceiling",
    "model_for_capacity",
    "power_from_bms",
    "probe_units",
]
