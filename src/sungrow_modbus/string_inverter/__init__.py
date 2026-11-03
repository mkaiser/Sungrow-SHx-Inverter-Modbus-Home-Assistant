"""The SG string inverters: a PV inverter with no battery, on a map of its own.

Recognised by input 5000 (`is_string_inverter`), read as the entry's inverter
with the components in `registers`, read only. See `registers` for why the
map is not a family of the hybrid one, and where every address comes from.
The published form is a document of its own kind (`document`).
"""

from ..dump import SG_BANDS as BANDS
from .device import TIER_COMPONENTS, SungrowStringInverter
from .document import (
    STRING_INVERTER_DOCUMENT,
    device_block,
    document,
    firmware,
    label_for,
    mask,
    readings,
    section,
    serial,
)
from .registers import COMPONENTS, MODELS, WORK_STATES, is_string_inverter, model_for

DOCUMENT = STRING_INVERTER_DOCUMENT

__all__ = [
    "BANDS",
    "COMPONENTS",
    "DOCUMENT",
    "MODELS",
    "STRING_INVERTER_DOCUMENT",
    "TIER_COMPONENTS",
    "WORK_STATES",
    "SungrowStringInverter",
    "device_block",
    "document",
    "firmware",
    "is_string_inverter",
    "label_for",
    "mask",
    "model_for",
    "readings",
    "section",
    "serial",
]
