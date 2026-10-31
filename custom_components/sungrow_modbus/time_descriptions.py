"""Time descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py times` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is a time of day the inverter holds in two registers, an hour and a
minute. One entity per pair, so a schedule reads as times rather than as
numbers.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory
from sungrow_modbus import Capability

from .entity import SungrowTimeDescription

TIME_DESCRIPTIONS: tuple[SungrowTimeDescription, ...] = (
    SungrowTimeDescription(
        key="forced_charging_start_1",
        component="forced_charging",
        field="forced_charging_start_1_hour",
        minute_field="forced_charging_start_1_minute",
        translation_key="forced_charging_start_1",
        requires=Capability.FORCED_CHARGING,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="forced_charging_end_1",
        component="forced_charging",
        field="forced_charging_end_1_hour",
        minute_field="forced_charging_end_1_minute",
        translation_key="forced_charging_end_1",
        requires=Capability.FORCED_CHARGING,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="forced_charging_start_2",
        component="forced_charging",
        field="forced_charging_start_2_hour",
        minute_field="forced_charging_start_2_minute",
        translation_key="forced_charging_start_2",
        requires=Capability.FORCED_CHARGING,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="forced_charging_end_2",
        component="forced_charging",
        field="forced_charging_end_2_hour",
        minute_field="forced_charging_end_2_minute",
        translation_key="forced_charging_end_2",
        requires=Capability.FORCED_CHARGING,
        entity_category=EntityCategory.CONFIG,
    ),
)
