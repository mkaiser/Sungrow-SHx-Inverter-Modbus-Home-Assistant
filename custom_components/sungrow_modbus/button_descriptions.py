"""Button descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py buttons` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is a command register: a press writes one word, and there is no state to
show, because a command does not read back what was sent.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory
from sungrow_modbus import Capability

from .entity import SungrowButtonDescription

BUTTON_DESCRIPTIONS: tuple[SungrowButtonDescription, ...] = (
    SungrowButtonDescription(
        key="force_startup",
        component="fast_holding",
        field="forced_startup_under_low_soc_raw",
        translation_key="force_startup",
        requires=Capability.FORCED_STARTUP_CONTROL,
        press_value=0xAA,
        entity_category=EntityCategory.CONFIG,
    ),
)
