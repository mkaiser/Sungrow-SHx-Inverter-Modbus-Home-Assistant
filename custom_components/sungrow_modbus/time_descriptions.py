"""Time descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py times` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is a time of day the inverter holds in two registers, an hour and a
minute. One entity per pair, so a schedule reads as times rather than as
numbers.

From github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT),
where `doc/architecture.md` records which document or measurement each
register comes from. Keep this line with any copy -- `doc/attribution.md`.
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
    SungrowTimeDescription(
        key="weekday_discharge_start_1",
        component="discharge_weekday",
        field="weekday_discharge_start_1_hour",
        minute_field="weekday_discharge_start_1_minute",
        translation_key="weekday_discharge_start_1",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekday_discharge_end_1",
        component="discharge_weekday",
        field="weekday_discharge_end_1_hour",
        minute_field="weekday_discharge_end_1_minute",
        translation_key="weekday_discharge_end_1",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekday_discharge_start_2",
        component="discharge_weekday",
        field="weekday_discharge_start_2_hour",
        minute_field="weekday_discharge_start_2_minute",
        translation_key="weekday_discharge_start_2",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekday_discharge_end_2",
        component="discharge_weekday",
        field="weekday_discharge_end_2_hour",
        minute_field="weekday_discharge_end_2_minute",
        translation_key="weekday_discharge_end_2",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekend_discharge_start_1",
        component="discharge_weekend",
        field="weekend_discharge_start_1_hour",
        minute_field="weekend_discharge_start_1_minute",
        translation_key="weekend_discharge_start_1",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekend_discharge_end_1",
        component="discharge_weekend",
        field="weekend_discharge_end_1_hour",
        minute_field="weekend_discharge_end_1_minute",
        translation_key="weekend_discharge_end_1",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekend_discharge_start_2",
        component="discharge_weekend",
        field="weekend_discharge_start_2_hour",
        minute_field="weekend_discharge_start_2_minute",
        translation_key="weekend_discharge_start_2",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowTimeDescription(
        key="weekend_discharge_end_2",
        component="discharge_weekend",
        field="weekend_discharge_end_2_hour",
        minute_field="weekend_discharge_end_2_minute",
        translation_key="weekend_discharge_end_2",
        requires=Capability.DISCHARGE_SCHEDULE_CONTROL,
        entity_category=EntityCategory.CONFIG,
    ),
)
