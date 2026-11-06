"""A Sungrow Logger1000/3000/4000 at unit 247, from Sungrow's document.

Its documented registers are decoded (`registers`); every word is published
raw too, with any text no field reads masked (`document`). `BANDS` is what
the survey reads.
"""

from ..dump import LOGGER_BANDS as BANDS
from .document import LOGGER_DOCUMENT, document, label_for, readings, section
from .registers import CODES, COMPONENTS, CONFIDENCE, MODELS, UNIT

DOCUMENT = LOGGER_DOCUMENT

__all__ = [
    "BANDS",
    "CODES",
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
