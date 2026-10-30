"""A Sungrow Logger1000/3000/4000 at unit 247: identified and read raw.

Its identity is decoded (`registers`); the rest is published raw, with any
undocumented text masked (`document`). `BANDS` is what the survey reads.
"""

from ..dump import LOGGER_BANDS as BANDS
from .document import LOGGER_DOCUMENT, document, label_for, readings, section
from .registers import COMPONENTS, CONFIDENCE, MODELS, UNIT

DOCUMENT = LOGGER_DOCUMENT

__all__ = [
    "BANDS",
    "COMPONENTS",
    "CONFIDENCE",
    "DOCUMENT",
    "LOGGER_DOCUMENT",
    "MODELS",
    "UNIT",
    "document",
    "label_for",
    "readings",
    "section",
]
