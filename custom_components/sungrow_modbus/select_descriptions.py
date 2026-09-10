"""Select descriptions, generated from the write table.

Do not edit by hand: `scripts/generate_selectes.py` writes this file from
`scripts/writes.py`, and CI checks that it matches.

Each is one holding register carrying 0xAA or 0x55. The specification states
both values for all three, so there is nothing to infer -- the `on` and `off`
codes travel with the description rather than being assumed.
"""

from __future__ import annotations

from homeassistant.const import EntityCategory

from .entity import SungrowSelectDescription

SELECT_DESCRIPTIONS: tuple[SungrowSelectDescription, ...] = (
    SungrowSelectDescription(
        key="ems_mode",
        component="fast_holding",
        field="ems_mode_selection_raw",
        translation_key="ems_mode",
        legacy_name="EMS mode",
        legacy_unique_id="uid_ems_mode",
        legacy_platform="template",
        options=["self_consumption", "forced", "external_ems", "vpp"],
        values={"self_consumption": 0, "forced": 2, "external_ems": 3, "vpp": 4},
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSelectDescription(
        key="battery_forced_charge_discharge",
        component="fast_holding",
        field="battery_forced_charge_discharge_cmd_raw",
        translation_key="battery_forced_charge_discharge",
        legacy_name="Battery forced charge discharge",
        legacy_unique_id="uid_battery_forced_charge_discharge",
        legacy_platform="template",
        options=["stop", "charge", "discharge"],
        values={"stop": 204, "charge": 170, "discharge": 187},
        entity_category=EntityCategory.CONFIG,
    ),
    SungrowSelectDescription(
        key="load_adjustment_mode",
        component="fast_holding",
        field="load_adjustment_mode_selection_raw",
        translation_key="load_adjustment_mode",
        legacy_name="Load adjustment mode",
        legacy_unique_id="uid_load_adjustment_mode",
        legacy_platform="template",
        options=["timing", "on_off", "power_optimised", "disabled"],
        values={"timing": 0, "on_off": 1, "power_optimised": 2, "disabled": 3},
        entity_category=EntityCategory.CONFIG,
    ),
)
