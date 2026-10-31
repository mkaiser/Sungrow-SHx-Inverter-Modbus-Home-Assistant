"""Switch descriptions, generated from the write table.

Do not edit by hand: `scripts/generate/descriptions.py switches` writes this
file from `scripts/generate/tables/writes.py`, and CI checks that it matches.

Each is one holding register carrying 0xAA or 0x55. The specification states
both values for the first three, and the owner of an SH10RT observed both by
their effect for the fourth -- the `on` and `off` codes travel with the
description rather than being assumed.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory
from sungrow_modbus import Capability

from .entity import SungrowSwitchDescription

SWITCH_DESCRIPTIONS: tuple[SungrowSwitchDescription, ...] = (
    SungrowSwitchDescription(
        key="backup_mode",
        component="fast_holding",
        field="backup_mode_raw",
        translation_key="backup_mode",
        legacy_name="Backup Mode",
        legacy_unique_id="sg_backup_mode_switch",
        legacy_platform="modbus",
        on_value=0xAA,
        off_value=0x55,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSwitchDescription(
        key="export_power_limit_mode",
        component="fast_holding",
        field="export_power_limit_mode_raw",
        translation_key="export_power_limit_mode",
        legacy_name="Export power limit",
        legacy_unique_id="sg_export_power_limit_switch",
        legacy_platform="modbus",
        on_value=0xAA,
        off_value=0x55,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSwitchDescription(
        key="load_adjustment_mode_enable",
        component="fast_holding",
        field="load_adjustment_mode_enable_raw",
        translation_key="load_adjustment_mode_enable",
        legacy_name="Load adjustment mode",
        legacy_unique_id="sg_load_adjustment_mode_switch",
        legacy_platform="modbus",
        on_value=0xAA,
        off_value=0x55,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSwitchDescription(
        key="cut_pv_generation",
        component="pv_generation_cut",
        field="pv_generation_cut_raw",
        translation_key="cut_pv_generation",
        requires=Capability.PV_GENERATION_CUT_CONTROL,
        on_value=0xAA,
        off_value=0x55,
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSwitchDescription(
        key="forced_charging_schedule",
        component="forced_charging",
        field="forced_charging_raw",
        translation_key="forced_charging_schedule",
        requires=Capability.FORCED_CHARGING,
        on_value=0xAA,
        off_value=0x55,
        entity_category=EntityCategory.CONFIG,
    ),
)
