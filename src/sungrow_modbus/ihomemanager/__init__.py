"""Sungrow's iHomeManager: an energy manager at unit 247, on an address of its own.

Not a gateway: it forwards none of the devices it manages, so it is its own
endpoint and its own document. The map is Sungrow's document (`registers`),
and the published form masks any undocumented text (`document`).
"""

from ..dump import IHOMEMANAGER_BANDS as BANDS
from .document import (
    IHOMEMANAGER_DOCUMENT,
    document,
    label_for,
    masked_text,
    readings,
    section,
)
from .registers import COMPONENTS, CONFIDENCE, PORTS, TYPE_CODE, UNIT, protocol_version

DOCUMENT = IHOMEMANAGER_DOCUMENT

__all__ = [
    "BANDS",
    "COMPONENTS",
    "CONFIDENCE",
    "DOCUMENT",
    "IHOMEMANAGER_DOCUMENT",
    "PORTS",
    "TYPE_CODE",
    "UNIT",
    "document",
    "label_for",
    "masked_text",
    "protocol_version",
    "readings",
    "section",
]
