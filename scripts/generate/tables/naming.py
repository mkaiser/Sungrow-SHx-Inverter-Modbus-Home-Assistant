"""The entity naming convention, in one place, applied and enforced.

The YAML package's names drifted because nothing checked them. In one file
`Battery min SoC` sits beside `Battery Min Soc`, fourteen names are title-cased
among sentence-cased ones, fifteen begin with the device's own name — which
Home Assistant then prefixes again, giving "SH10RT Sungrow inverter serial" —
and two abbreviate with a full stop ("BMS max. charging current"). None of that
was a decision; it is what five years of contributions look like without a
rule.

The names are not cosmetic. With `has_entity_name` set, the object id is
slugified **from the name**, so "Sungrow inverter serial" becomes
`sensor.sh10rt_sungrow_inverter_serial` and "Serial number" becomes
`sensor.sh10rt_serial_number`. Naming is therefore free now and awkward after
release -- not impossible: a name supplies an entity_id at *creation* only, so
a later rename leaves an existing install's id alone and only diverges it from
a fresh one. What that costs is two houses answering one question with two
ids, which is a support and documentation problem. See
`tests/test_entity_naming.py`.

Legacy names are untouched. Legacy mode has to reproduce the old entity ids
byte for byte, inconsistency included, so `legacy_name` on each description
stays whatever the YAML said.

Two functions do the work, and they are deliberately separate:
`modern_name` produces a name, `violations` judges one. The test checks the
*committed* strings.json with `violations`, so an override that breaks the
rules fails just as loudly as a hand edit would.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

#: Words that keep their capitals wherever they appear: initialisms, plus
#: Sungrow's own spelling of state of charge and state of health. One canonical
#: spelling each, which is what stops `SoC` and `Soc` naming one concept.
ACRONYMS: frozenset[str] = frozenset(
    {
        "AC",
        "APL",
        "ARM",
        "BDC",
        "BMS",
        "DC",
        "DSP",
        "EMS",
        "MPPT",
        "MPPT1",
        "MPPT2",
        "MPPT3",
        "MPPT4",
        "MPPT5",
        "MPPT6",
        "MPPT7",
        "MPPT8",
        "MPPT9",
        "MPPT10",
        "MPPT11",
        "MPPT12",
        "PV",
        "SoC",
        "SoH",
    }
)

#: Proper nouns, capitalised anywhere in a name. "Sungrow" is one, even though
#: a name may not *start* with it: "Firmware version part 4 (Sungrow battery)"
#: distinguishes a Sungrow pack from a third-party one, which is information.
PROPER_NOUNS: frozenset[str] = frozenset({"Sungrow"})

#: Home Assistant prefixes the device name, so a name starting with one of
#: these says it twice. Stripped from the front, never from the middle.
DEVICE_WORDS: frozenset[str] = frozenset({"sungrow", "inverter"})

#: Where the rules alone produce something thin or wrong, the better name is
#: written out. Kept short on purpose: a long table here means the rules are
#: wrong, not the names.
OVERRIDES: dict[str, str] = {
    # -- the SBR pack, which is its own device on its own unit ------------
    #
    # These have no legacy name to derive from: the registers live in
    # `legacy/additional_sensors/`, an opt-in file, and are not in the entity
    # map. So every one is written out here.
    #
    # `Pack` rather than nothing, and it is not redundancy. Two of the bare
    # names would collide with the inverter's -- `inverter_temperature` is
    # already called "Temperature" -- and the word earns its place anyway: the
    # inverter reports "Battery voltage" as *its* view of the pack, and this
    # is the pack's own BMS reporting itself. A user comparing the two should
    # be able to tell which is which from the name.
    # -- the diagnosis, which is tooling rather than a reading ---------------
    #
    # Also without a legacy name: these describe what the integration is
    # doing, not what the inverter reports. "Diagnosis" leads every one of them
    # so they sort together on a device page among entities that are
    # otherwise all readings.
    # The two buttons are named as a pair a contributor chooses between:
    # "read only" on the one that never writes, so that the other one, which
    # adds the capability test's writes, is the one without that promise.
    "run_diagnosis": "Run read only diagnosis",
    "run_capability_test": "Run complete diagnosis and tests",
    "diagnosis_progress": "Diagnosis progress",
    "diagnosis_step": "Diagnosis step",
    "diagnosis_finished": "Diagnosis finished",
    # -- the SBR pack, which is its own device on its own unit ------------
    "battery_pack_voltage": "Pack voltage",
    "battery_pack_current": "Pack current",
    "battery_pack_temperature": "Pack temperature",
    "battery_pack_level": "Pack level",
    "battery_pack_state_of_health": "Pack state of health",
    "battery_pack_total_charge": "Total pack charge energy",
    "battery_pack_total_discharge": "Total pack discharge energy",
    # Highest and lowest rather than max and min, because these are readings
    # and not limits -- the inverter's "Battery max SoC" is a setting, and
    # reusing its word here would blur that. Warmest and coolest for the same
    # reason.
    "battery_max_cell_voltage": "Highest cell voltage",
    "battery_min_cell_voltage": "Lowest cell voltage",
    "battery_cell_voltage_spread": "Cell voltage spread",
    "battery_max_module_temperature": "Warmest module temperature",
    "battery_min_module_temperature": "Coolest module temperature",
    # The unpacked halves of the position words. `(module << 8) | cell`, so
    # each word becomes two entities -- see `SbrBatteryCells`.
    "battery_max_cell_module": "Module with highest cell",
    "battery_max_cell_number": "Highest cell number",
    "battery_min_cell_module": "Module with lowest cell",
    "battery_min_cell_number": "Lowest cell number",
    "battery_max_module_temperature_module": "Warmest module",
    "battery_min_module_temperature_module": "Coolest module",
    # Each module's own extremes, one pair per slot of the eight.
    **{
        f"battery_module_{module}_{end}_cell_voltage": (
            f"Module {module} {word} cell voltage"
        )
        for module in range(1, 9)
        for end, word in (("max", "highest"), ("min", "lowest"))
    },
    # -- the wallbox, its own device on its own unit ----------------------
    #
    # No legacy name to derive from: the YAML package never covered a wallbox
    # at all, not even in `legacy/additional_sensors/`. So every one is
    # written out, and none carries a `Wallbox` prefix -- Home Assistant
    # already says `AC22E-01` in front of it, and the uniqueness rule is
    # scoped per device precisely so a second device need not invent a word
    # to get out of the inverter's way.
    "wallbox_charging_power": "Charging power",
    "wallbox_session_energy": "Session energy",
    "wallbox_lifetime_energy": "Total charged energy",
    "wallbox_charging_status": "Charging status",
    "wallbox_phase_a_voltage": "Phase A voltage",
    "wallbox_phase_a_current": "Phase A charging current",
    "wallbox_phase_b_voltage": "Phase B voltage",
    "wallbox_phase_b_current": "Phase B charging current",
    "wallbox_phase_c_voltage": "Phase C voltage",
    "wallbox_phase_c_current": "Phase C charging current",
    "wallbox_available_current": "Offered charging current",
    # The Type 2 signalling line. Named for what it is rather than for what
    # it tells you, because what it tells you is a table: 12 V nothing
    # plugged in, 9 V connected and idle, 6 V charging.
    "wallbox_control_pilot_voltage": "Control pilot voltage",
    "wallbox_start_mode": "Start mode",
    "wallbox_rated_current": "Maximum charging current",
    "wallbox_maximum_charging_power": "Maximum charging power",
    "wallbox_minimum_charging_power": "Minimum charging power",
    "wallbox_phase_mode": "Phase mode",
    "wallbox_firmware_version": "Firmware version",
    # Four currents, named by who limits them: the hardware's maximum
    # (21263), the setpoint the owner or an EMS writes (21203), what the
    # wallbox offers the car -- the lower of the two, IEC 61851's word
    # (21322) -- and what the car draws per phase. "Setpoint" rather than
    # "setting", which would trip the `-ing` rule.
    "wallbox_output_current_setting": "Charging current setpoint",
    # `-ing` on a binary sensor, which is what the convention reserves it
    # for: something happening right now.
    "wallbox_charging": "Charging",
    "wallbox_enabled": "Charger enabled",
    # -- an SG string inverter, the entry's own inverter ------------------
    #
    # No legacy name either: the YAML package never read an SG. Named as the
    # hybrid's counterparts are, without an `SG` prefix -- the device already
    # says `SG5.0RS` -- and the key's `sg_` keeps the translation keys apart.
    # "Power limit" rather than "Power limitation setting", for the `-ing`
    # rule's reason on the wallbox's configured output current.
    "sg_total_dc_power": "Total PV input power",
    "sg_total_active_power": "Total active power",
    "sg_total_apparent_power": "Total apparent power",
    "sg_reactive_power": "Reactive power",
    "sg_power_factor": "Power factor",
    "sg_grid_frequency": "Grid frequency",
    "sg_inverter_temperature": "Device temperature",
    "sg_work_state": "Running state",
    "sg_mppt1_voltage": "MPPT1 voltage",
    "sg_mppt1_current": "MPPT1 current",
    "sg_mppt2_voltage": "MPPT2 voltage",
    "sg_mppt2_current": "MPPT2 current",
    "sg_mppt3_voltage": "MPPT3 voltage",
    "sg_mppt3_current": "MPPT3 current",
    "sg_phase_a_voltage": "Phase A voltage",
    "sg_phase_a_current": "Phase A current",
    "sg_phase_b_voltage": "Phase B voltage",
    "sg_phase_b_current": "Phase B current",
    "sg_phase_c_voltage": "Phase C voltage",
    "sg_phase_c_current": "Phase C current",
    "sg_daily_pv_generation": "Daily PV generation",
    "sg_total_pv_generation": "Total PV generation",
    "sg_monthly_pv_generation": "Monthly PV generation",
    "sg_total_running_time": "Total running time",
    "sg_daily_running_time": "Daily running time",
    "sg_meter_active_power": "Meter active power",
    "sg_meter_phase_a_power": "Meter phase A power",
    "sg_meter_phase_b_power": "Meter phase B power",
    "sg_meter_phase_c_power": "Meter phase C power",
    "sg_load_power": "Load power",
    "sg_daily_exported_energy": "Daily exported energy",
    "sg_total_exported_energy": "Total exported energy",
    "sg_daily_imported_energy": "Daily imported energy",
    "sg_total_imported_energy": "Total imported energy",
    "sg_daily_direct_energy_consumption": "Daily direct energy consumption",
    "sg_total_direct_energy_consumption": "Total direct energy consumption",
    "sg_mppt4_voltage": "MPPT4 voltage",
    "sg_mppt4_current": "MPPT4 current",
    "sg_mppt5_voltage": "MPPT5 voltage",
    "sg_mppt5_current": "MPPT5 current",
    "sg_mppt6_voltage": "MPPT6 voltage",
    "sg_mppt6_current": "MPPT6 current",
    "sg_mppt7_voltage": "MPPT7 voltage",
    "sg_mppt7_current": "MPPT7 current",
    "sg_mppt8_voltage": "MPPT8 voltage",
    "sg_mppt8_current": "MPPT8 current",
    "sg_mppt9_voltage": "MPPT9 voltage",
    "sg_mppt9_current": "MPPT9 current",
    "sg_mppt10_voltage": "MPPT10 voltage",
    "sg_mppt10_current": "MPPT10 current",
    "sg_mppt11_voltage": "MPPT11 voltage",
    "sg_mppt11_current": "MPPT11 current",
    "sg_mppt12_voltage": "MPPT12 voltage",
    "sg_mppt12_current": "MPPT12 current",
    # Computed, voltage times current, and its integral: no SG register
    # reports either per tracker.
    **{
        f"sg_mppt{n}_{quantity}": f"MPPT{n} {quantity}"
        for n in range(1, 13)
        for quantity in ("power", "energy")
    },
    "sg_fault_reported": "Fault reported",
    "sg_negative_voltage_to_ground": "Negative voltage to ground",
    "sg_bus_voltage": "Bus voltage",
    "sg_power_limitation": "Power limit active",
    "sg_power_limitation_setting": "Power limit",
    # -- corrections for a generator the inverter cannot see --------------
    #
    # No legacy name, like the wallbox's: the YAML package had no concept of
    # a second inverter on the supply. Both are named for what makes them
    # different from the register beside them, because that is the only
    # question a device page raises -- why are there two load figures?
    "corrected_load_power": "Corrected load power",
    # "Site" rather than "total": `total_dc_power` is already "Total PV
    # input power", so the distinguishing word has to be the one that says
    # *whose* production is counted, not that it is a total.
    "total_site_pv_power": "Total site PV power",
    # Stripping both device words leaves "Serial" and "State", which are too
    # thin to sit in a list of 127.
    "sungrow_inverter_serial": "Serial number",
    "sungrow_inverter_state": "Running state",
    # Sungrow's protocol document calls these the ARM and DSP software
    # versions; "software" alone does not say what the value is.
    "sungrow_arm_software": "ARM software version",
    "sungrow_dsp_software": "DSP software version",
    # Four registers holding four segments of one concatenated firmware
    # string, which "Version 1" does not tell anybody.
    "sungrow_version_1": "Firmware version part 1",
    "sungrow_version_2": "Firmware version part 2",
    "sungrow_version_3": "Firmware version part 3",
    "sungrow_version_4_sungrow_battery": "Firmware version part 4 (Sungrow battery)",
    # Two on/off registers whose YAML names are the names of the *values*
    # they gate, so a device page listed one label three times over: the
    # switch that turns limiting on, the number that sets the watts, and a
    # read-only copy of that number, all called "Export power limit".
    #
    # "Feed-in limit" for the whole family, as Sungrow has named these
    # registers since V1.1.9 ("Feed-in Limitation Value/Ratio", 13074,
    # 13088; "Min./Max. Feed-in Power Limitation Value", 5622/5623). The
    # measured flow keeps "export", which is Sungrow's word for it too
    # ("Export power", 13010).
    #
    # `-ing` was considered and rejected on the evidence: the three names in
    # this map that end in it -- Battery charging, Battery discharging, PV
    # generating -- are all binary sensors meaning "this is happening right
    # now", so "Export power limiting" would read as something observed
    # rather than something switched.
    #
    # A switch named for the mode register it writes is already the pattern
    # here: `switch.backup_mode` is "Backup mode". So this follows it, and
    # the number keeps the name a user would look for.
    "export_power_limit": "Feed-in limit",
    "export_power_limit_mode": "Feed-in limit mode",
    "export_power_limit_max": "Feed-in limit maximum",
    "export_power_limit_min": "Feed-in limit minimum",
    "feed_in_limitation_ratio": "Feed-in limit ratio",
    "site_import_power_limit": "Grid import limit",
    # Sungrow's "Load Control Mode" (13002) and its enable (13011): "load
    # control" is the document's word, and says what the feature does, which
    # "load adjustment" never did. The select owns the longer name; the
    # switch says whether load control happens at all.
    "load_adjustment_mode": "Load control mode",
    "load_adjustment_mode_enable": "Load control",
    "load_adjustment_mode_selection_raw": "Load control mode selection code",
    "load_adjustment_mode_enable_raw": "Load control mode enable code",
    # "Energy" on every battery throughput total, as on the grid's and the
    # house's ("Daily exported energy") and in Sungrow's own names ("Daily
    # battery discharge energy", 13026). Without it "Daily battery charge"
    # reads like `battery_charge`, which is the energy *stored* in the pack.
    "daily_battery_charge": "Daily battery charge energy",
    "total_battery_charge": "Total battery charge energy",
    "daily_battery_discharge": "Daily battery discharge energy",
    "total_battery_discharge": "Total battery discharge energy",
    "daily_battery_charge_from_pv": "Daily battery charge energy from PV",
    "total_battery_charge_from_pv": "Total battery charge energy from PV",
    # The raw number behind a decoded entity says "code": each is a value
    # looked up in a table (0xAA/0x55, a mode number, a state code), and one
    # word for all of them shows at a glance which entity is the raw one.
    # The power flow register is one too: its bits are the on/off sensors.
    "power_flow_status": "Power flow code",
    "running_state_raw": "Running state code",
    "backup_mode_raw": "Backup mode code",
    "ems_mode_selection_raw": "EMS mode selection code",
    "export_power_limit_mode_raw": "Feed-in limit mode code",
    "active_power_limitation_raw": "Active power limitation code",
    "pv_power_limitation_raw": "PV power limitation code",
    "pv_generation_cut_raw": "PV generation cut code",
    # Not a code: a signed power, like "Battery charging power signed".
    "export_power_raw": "Export power signed",
    # The inverter's own alarm word (13050), and the summary of all four
    # alarm words: "Device" says whose, as "Device temperature" does, where
    # "Inverter alarm" would repeat the device's name.
    "inverter_alarm": "Device alarm",
    "alarm_reported": "Any alarm",
    # Register 5017, Sungrow's "Total DC power" with the remark "Total PV
    # power": the trackers' inputs summed, on the DC side. "Total" because it
    # is the sum of the MPPT readings beside it, as "Total active power" is
    # of the phases.
    "total_dc_power": "Total PV input power",
    # Not raw at all: register 13090 has a scale of 0.1 and a unit, and reads
    # 100.0 % on every machine diagnosed. The YAML called it "raw" because it
    # sits beside the mode register, and the word has been describing the
    # neighbour ever since.
    "active_power_limitation_ratio_raw": "Active power limitation ratio",
    # Register 31213, which is in no Sungrow datasheet: issue #554 found it
    # by watching iSolarCloud, as "Shutdown at active power limit ratio of
    # 0%". Named for what it decides -- whether a 0 % active power limit
    # stops the inverter or holds it running at 0 W -- in words that need no
    # knowledge of "active power". The diagnoses read both 0x55 and 0xAA on it,
    # so the binary sensor decodes it and the number is a code.
    "apl_shutdown_at_zero": "Shutdown inverter when limited to 0 % power",
    "apl_shutdown_at_zero_raw": "Shutdown inverter when limited to 0 % power code",
    # Register 13017, Sungrow's "Forced Startup Under Low SOC Standby": a
    # switch, named after the specification.
    "forced_startup_under_low_soc": "Forced startup under low SoC",
    # The two mode registers, now that a binary sensor decodes each. The
    # entity says whether limiting is happening; the ratio above says how
    # much.
    "active_power_limitation_enabled": "Active power limitation",
    "pv_power_limitation_enabled": "PV power limitation",
    # A parenthetical qualifies the *value*, so it says what the value is
    # rather than which Home Assistant option produced it. Both of these
    # arrived from the YAML package naming the mechanism: `filter` is the
    # platform it used, `delay_on` the template option.
    #
    # "Filtered" is also ambiguous where "smoothed" is not -- a filter might
    # reject outliers, or cut high frequencies, or drop readings -- and this
    # one is a 300-second time-weighted moving average, which is what
    # `sungrow_modbus.hybrid_inverter.smoothing` has always called smoothing.
    # The module, the docs and the entity finally agree.
    "daily_consumed_energy_filtered": "Daily consumed energy (smoothed)",
    # `(delayed)` for the same reason and in the same grammar: the seven
    # binary sensors below report true only once the condition has held for
    # sixty seconds. `(delay)` is a noun, and reads as though the entity were
    # the delay itself.
    "battery_charging_delay": "Battery charging (delayed)",
    "battery_discharging_delay": "Battery discharging (delayed)",
    "exporting_power_delay": "Exporting power (delayed)",
    "importing_power_delay": "Importing power (delayed)",
    "negative_load_power_delay": "Negative load power (delayed)",
    "positive_load_power_delay": "Positive load power (delayed)",
    "pv_generating_delay": "PV generating (delayed)",
    # It is a power in watts, with device class power; "output" alone reads
    # like a mode.
    "inverter_rated_output": "Rated output power",
    # The YAML abbreviates with a full stop, which nothing else here does.
    "bms_max_charging_current": "BMS max charging current",
    "bms_max_discharging_current": "BMS max discharging current",
    # "Charging" for every limit, as beside it above and in Sungrow's own
    # "Max. Charging Power" (33047): the YAML's "charge power" was the one
    # limit spelled the other way.
    "battery_max_charge_power": "Battery max charging power",
    "battery_max_discharge_power": "Battery max discharging power",
    # Sungrow's "Inside Temperature" (5008). "Temperature" alone sat among
    # the pack's and the modules' temperatures without saying whose, and
    # "Device" says whose where "Internal" only said where.
    "inverter_temperature": "Device temperature",
    # "cmd" is banned below, and the slash reads better than three nouns in a
    # row; Home Assistant slugifies it away, so the entity_id is unaffected.
    "battery_forced_charge_discharge_cmd_raw": (
        "Battery forced charge/discharge command code"
    ),
    "battery_forced_charge_discharge_power": "Battery forced charge/discharge power",
    # And the select that drives them, which the YAML wrote without the slash.
    "battery_forced_charge_discharge": "Battery forced charge/discharge",
}

#: Abbreviations that save four characters and cost a reader a guess. "max"
#: and "min" are not here: they are used consistently and everybody reads them.
BANNED_WORDS: dict[str, str] = {
    "cfg": "configuration",
    "cmd": "command",
    "pwr": "power",
    "temp": "temperature",
}

#: Sensors that exist **only to carry the YAML package's history**, and are
#: not created in modern mode. The maintainer's decision: "I prefer a clean
#: cut more over 100% backwards compatibility. Also those values are not very
#: valuable, so having them erased wouldn't be a big deal for the users."
#:
#: Each one **names what replaces it**, and that is the whole discipline
#: here: a clean cut removes duplication, not capability, and the only way to
#: know which is being removed is to say where the reading went instead.
#: `tests/test_sensor_descriptions.py` checks every replacement exists among
#: the entities modern mode does create, by name rather than by a heuristic
#: that would guess.
#:
#: Two kinds, both a second copy of something the user already has:
#:
#: * **Nine read-only sensors duplicating a `number`.** A Home Assistant
#:   number shows its value *and* sets it, so `sensor.battery_max_soc` beside
#:   `number.battery_max_soc` is one reading listed twice under one name. The
#:   YAML package needed both because a YAML `sensor` cannot be written.
#: * **`_raw` codes whose decoded counterpart exists.**
#:   `backup_mode_raw` reads 170 or 85 where `switch.backup_mode` says on or
#:   off. Nobody should have to know that 170 means enabled.
#:
#: `active_power_limitation_ratio_raw` is **not** here: it is the only
#: exposure of its register, and not a code at all but a percentage.
#:
#: A field named here loses its *sensor* and keeps its switch, select or
#: number: its description in `sensor_descriptions.py` carries
#: `legacy_only=True`, which `tests/test_sensor_descriptions.py` holds to
#: exactly this table.
LEGACY_ONLY_SENSORS: dict[str, str] = {
    # A `number` of the same name shows the value and sets it.
    "battery_charging_start_power": "number.battery_charging_start_power",
    "battery_discharging_start_power": "number.battery_discharging_start_power",
    "battery_forced_charge_discharge_power": (
        "number.battery_forced_charge_discharge_power"
    ),
    "battery_max_charge_power": "number.battery_max_charge_power",
    "battery_max_discharge_power": "number.battery_max_discharge_power",
    "battery_max_soc": "number.battery_max_soc",
    "battery_min_soc": "number.battery_min_soc",
    "battery_reserved_soc_for_backup": "number.battery_reserved_soc_for_backup",
    "export_power_limit": "number.export_power_limit",
    # A raw code, and the decoded entity that says the same thing in words.
    "backup_mode_raw": "switch.backup_mode",
    "battery_forced_charge_discharge_cmd_raw": (
        "select.battery_forced_charge_discharge"
    ),
    "ems_mode_selection_raw": "select.ems_mode",
    "export_power_limit_mode_raw": "switch.export_power_limit_mode",
    "export_power_raw": "sensor.export_power",
    "load_adjustment_mode_enable_raw": "switch.load_adjustment_mode_enable",
    "load_adjustment_mode_selection_raw": "select.load_adjustment_mode",
    # The decoded state is a derived sensor, under its own key.
    "running_state_raw": "sensor.sungrow_inverter_state",
    # And the two mode registers, replaced by the binary sensors that decode
    # their 0xAA/0x55 rather than publishing 170 and 85.
    "active_power_limitation_raw": "binary_sensor.active_power_limitation_enabled",
    "pv_power_limitation_raw": "binary_sensor.pv_power_limitation_enabled",
    "pv_generation_cut_raw": "binary_sensor.pv_generation_cut",
    "apl_shutdown_at_zero_raw": "binary_sensor.apl_shutdown_at_zero",
}

#: Entities that belong under the device page's Diagnostic heading rather than
#: among the readings: raw enumeration codes, identity and firmware strings,
#: and nameplate constants. `_raw` entities are all here by rule — a raw code
#: has a decoded counterpart, and that is the one a dashboard wants.
DIAGNOSTIC: frozenset[str] = frozenset(
    {
        "active_power_limitation_ratio_raw",
        "active_power_limitation_raw",
        "apl_shutdown_at_zero_raw",
        "backup_mode_raw",
        "battery_forced_charge_discharge_cmd_raw",
        "ems_mode_selection_raw",
        "export_power_limit_mode_raw",
        "export_power_raw",
        "load_adjustment_mode_enable_raw",
        "load_adjustment_mode_selection_raw",
        "running_state_raw",
        "pv_power_limitation_raw",
        "pv_generation_cut_raw",
        # The two mode flags that replaced a raw number. They mirror a
        # setting rather than measure the house, which is what Diagnostic
        # means -- and their `number`/`select` counterparts, being writable,
        # are CONFIG instead.
        "active_power_limitation_enabled",
        "pv_power_limitation_enabled",
        "pv_generation_cut",
        "apl_shutdown_at_zero",
        # The discharge schedules (#785): settings mirrored read only, like
        # the flags above, so Diagnostic until a watched write makes them
        # writable and CONFIG.
        "weekday_discharge_window_1",
        "weekday_discharge_window_2",
        "weekend_discharge",
        "weekend_discharge_window_1",
        "weekend_discharge_window_2",
        # The battery pack's state of health, and the six halves of its
        # position words. Diagnostic because they are what you look at when
        # investigating a pack rather than what a dashboard shows: state of
        # health moves by a percent a year, and "which cell is highest" is a
        # question you ask once, when something looks wrong. The four cell
        # voltages and module temperatures they point *at* are ordinary
        # sensors, because those are worth graphing.
        "battery_pack_state_of_health",
        "battery_max_cell_module",
        "battery_max_cell_number",
        "battery_min_cell_module",
        "battery_min_cell_number",
        "battery_max_module_temperature_module",
        "battery_min_module_temperature_module",
        # Each module's own extremes: opened when the pack's spread grows.
        *(
            f"battery_module_{module}_{end}_cell_voltage"
            for module in range(1, 9)
            for end in ("max", "min")
        ),
        # The wallbox's ratings, settings and signalling line: what you look
        # at when a charge is not behaving, rather than what a dashboard
        # shows. Its power, current, energy and status are ordinary sensors,
        # because those are the ones worth graphing.
        "wallbox_control_pilot_voltage",
        "wallbox_start_mode",
        "wallbox_rated_current",
        "wallbox_maximum_charging_power",
        "wallbox_minimum_charging_power",
        "wallbox_phase_mode",
        "wallbox_firmware_version",
        "wallbox_output_current_setting",
        "wallbox_enabled",
        # A bitmask, whose seven bits are the binary sensors.
        "power_flow_status",
        # Appendix 4's fault and alarm words, counted. What you open when the
        # `Fault reported` or `Alarm reported` binary sensor goes on, which
        # is the entity a dashboard shows.
        "inverter_alarm",
        "grid_side_fault",
        "system_fault_1",
        "system_fault_2",
        "dc_side_fault",
        "permanent_fault",
        "bdc_side_fault",
        "bdc_side_permanent_fault",
        "battery_fault",
        "battery_alarm",
        "bms_alarm",
        "bms_protection",
        "bms_fault_1",
        "bms_fault_2",
        "bms_alarm_2",
        # A configured limit rather than a measurement, like the ones above it.
        "feed_in_limitation_ratio",
        "site_import_power_limit",
        # Identity and firmware.
        "sungrow_inverter_serial",
        "sungrow_device_type",
        "sungrow_device_type_code",
        "sungrow_protocol_version",
        "sungrow_arm_software",
        "sungrow_dsp_software",
        "sungrow_version_1",
        "sungrow_version_2",
        "sungrow_version_3",
        "sungrow_version_4_sungrow_battery",
        "inverter_firmware_version",
        "communication_module_firmware_version",
        "battery_firmware_version",
        # Nameplate constants, not measurements.
        "inverter_rated_output",
        "bdc_rated_power",
        # An SG's run counters, insulation and bus, and the curtailment as
        # set: for diagnosing, not for a dashboard.
        "sg_total_running_time",
        "sg_daily_running_time",
        "sg_negative_voltage_to_ground",
        "sg_bus_voltage",
        "sg_power_limitation",
        "sg_power_limitation_setting",
    }
)

#: **German names**, one per translation key, decided beside the English
#: ones in `doc/entity_names.md`. `scripts/generate/descriptions.py german`
#: writes them into `translations/de.json`. Entity ids stay English either way
#: (`doc/architecture.md`).
#:
#: The convention follows the English one: sentence case, no abbreviation with
#: a full stop, the device's own name left to Home Assistant. A reading is
#: written **quantity first, then the phase** ("Phase A Spannung"), so the
#: three phases and the four trackers sort together; `GERMAN_TERMS` holds the
#: words every name must use for the same idea, and `tests/test_naming_convention.py`
#: holds the table to them.
GERMAN: dict[str, str] = {
    # -- on/off states ----------------------------------------------------
    "active_power_limitation_enabled": "Wirkleistungsbegrenzung",
    "apl_shutdown_at_zero": "Abschalten bei Begrenzung auf 0 % Leistung",
    "alarm_reported": "Alarm aktiv",
    "battery_charging": "Batterie lädt",
    "battery_charging_delay": "Batterie lädt (verzögert)",
    "battery_discharging": "Batterie entlädt",
    "battery_discharging_delay": "Batterie entlädt (verzögert)",
    "exporting_power": "Einspeisung",
    "exporting_power_delay": "Einspeisung (verzögert)",
    "fault_reported": "Fehler gemeldet",
    "importing_power": "Netzbezug",
    "importing_power_delay": "Netzbezug (verzögert)",
    "negative_load_power": "Negative Leistungsaufnahme Verbraucher",
    "negative_load_power_delay": "Negative Leistungsaufnahme Verbraucher (verzögert)",
    "positive_load_power": "Positive Leistungsaufnahme Verbraucher",
    "positive_load_power_delay": "Positive Leistungsaufnahme Verbraucher (verzögert)",
    "pv_generating": "PV erzeugt",
    "pv_generating_delay": "PV erzeugt (verzögert)",
    "pv_generation_cut": "PV-Erzeugung abgeschaltet",
    "pv_power_limitation_enabled": "PV-Leistungsbegrenzung",
    "sg_fault_reported": "Fehler gemeldet",
    "wallbox_charging": "Lädt",
    "wallbox_enabled": "Ladestation aktiviert",
    "weekend_discharge": "Entladung am Wochenende",
    # -- the diagnosis -------------------------------------------------------
    "run_capability_test": "Vollständige Diagnose und Tests ausführen",
    "run_diagnosis": "Diagnose ausführen (nur lesend)",
    "diagnosis_finished": "Diagnose beendet",
    "diagnosis_progress": "Diagnosefortschritt",
    "diagnosis_step": "Diagnoseschritt",
    # -- settings: numbers, selects, switches, times ----------------------
    "backup_mode": "Backup-Modus",
    "battery_charging_start_power": "Batterie Ladestartleistung",
    "battery_discharging_start_power": "Batterie Entladestartleistung",
    "battery_forced_charge_discharge": "Batterie Zwangsladung/-entladung",
    "battery_forced_charge_discharge_power": (
        "Batterie Zwangsladung/-entladung Leistung"
    ),
    "battery_max_charge_power": "Maximale Batterie-Ladeleistung",
    "battery_max_discharge_power": "Maximale Batterie-Entladeleistung",
    "battery_max_soc": "Maximaler Batterie-Ladezustand",
    "battery_min_soc": "Minimaler Batterie-Ladezustand",
    "battery_reserved_soc_for_backup": "Reservierter Batterie-Ladezustand für Backup",
    "cut_pv_generation": "PV-Erzeugung abschalten",
    "ems_mode": "EMS-Modus",
    "export_power_limit": "Einspeiselimit",
    "export_power_limit_mode": "Einspeiselimit-Modus",
    "forced_charging_days": "Zwangsladung Tage",
    "forced_charging_end_1": "Zwangsladung Ende 1",
    "forced_charging_end_2": "Zwangsladung Ende 2",
    "forced_charging_schedule": "Zwangsladung Zeitplan",
    "forced_startup_under_low_soc": "Zwangsstart bei niedrigem Ladezustand",
    "forced_charging_start_1": "Zwangsladung Start 1",
    "forced_charging_start_2": "Zwangsladung Start 2",
    "forced_charging_target_soc_1": "Zwangsladung Ziel-Ladezustand 1",
    "forced_charging_target_soc_2": "Zwangsladung Ziel-Ladezustand 2",
    "load_adjustment_mode": "Laststeuerungsmodus",
    "load_adjustment_mode_enable": "Laststeuerung",
    # -- raw codes: "Code", never "Rohwert" ----------------------------
    "active_power_limitation_raw": "Wirkleistungsbegrenzung Code",
    "backup_mode_raw": "Backup-Modus Code",
    "battery_forced_charge_discharge_cmd_raw": (
        "Batterie Zwangsladung/-entladung Befehl Code"
    ),
    "ems_mode_selection_raw": "EMS-Modus Auswahl Code",
    "export_power_limit_mode_raw": "Einspeiselimit-Modus Code",
    "export_power_raw": "Einspeiseleistung (mit Vorzeichen)",
    "load_adjustment_mode_enable_raw": "Laststeuerungsmodus Aktivierung Code",
    "load_adjustment_mode_selection_raw": "Laststeuerungsmodus Auswahl Code",
    "pv_generation_cut_raw": "PV-Erzeugung abgeschaltet Code",
    "pv_power_limitation_raw": "PV-Leistungsbegrenzung Code",
    "running_state_raw": "Betriebszustand Code",
    # -- limits and control state -----------------------------------------
    "active_power_limitation_ratio_raw": "Wirkleistungsbegrenzung prozentual",
    "apl_shutdown_at_zero_raw": "Abschalten bei Begrenzung auf 0 % Leistung Code",
    "export_power_limit_max": "Einspeiselimit Maximum",
    "export_power_limit_min": "Einspeiselimit Minimum",
    "feed_in_limitation_ratio": "Einspeiselimit prozentual",
    "site_import_power_limit": "Netzbezugslimit",
    # -- the inverter's own readings --------------------------------------
    "backup_frequency": "Backup Frequenz",
    "bdc_rated_power": "BDC-Nennleistung",
    "corrected_load_power": "Korrigierte Leistungsaufnahme Verbraucher",
    "export_power": "Einspeiseleistung",
    "grid_frequency": "Netzfrequenz",
    "import_power": "Bezugsleistung",
    "inverter_alarm": "Gerätealarm",
    "inverter_rated_output": "Nennausgangsleistung",
    "inverter_temperature": "Gerätetemperatur",
    "load_power": "Leistungsaufnahme Verbraucher",
    "power_factor": "Leistungsfaktor",
    "power_flow_status": "Leistungsfluss Code",
    "reactive_power": "Blindleistung",
    "self_consumption_of_today": "Eigenverbrauch heute",
    "total_active_power": "Gesamte Wirkleistung",
    "total_backup_power": "Backup Gesamtleistung",
    "total_dc_power": "Gesamte PV-Eingangsleistung",
    "total_site_pv_power": "Gesamte PV-Leistung der Anlage",
    # -- faults and alarms ------------------------------------------------
    "battery_alarm": "Batteriealarm",
    "battery_fault": "Batteriefehler",
    "bdc_side_fault": "BDC-seitiger Fehler",
    "bdc_side_permanent_fault": "BDC-seitiger permanenter Fehler",
    "bms_alarm": "BMS-Alarm",
    "bms_alarm_2": "BMS-Alarm 2",
    "bms_fault_1": "BMS-Fehler 1",
    "bms_fault_2": "BMS-Fehler 2",
    "bms_protection": "BMS-Schutz",
    "dc_side_fault": "DC-seitiger Fehler",
    "grid_side_fault": "Netzseitiger Fehler",
    "permanent_fault": "Permanenter Fehler",
    "system_fault_1": "Systemfehler 1",
    "system_fault_2": "Systemfehler 2",
    # -- identity and firmware --------------------------------------------
    "battery_firmware_version": "Batterie Firmware-Version",
    "communication_module_firmware_version": "Firmware-Version Kommunikationsmodul",
    "inverter_firmware_version": "Firmware-Version",
    "sungrow_arm_software": "ARM-Software-Version",
    "sungrow_device_type": "Gerätetyp",
    "sungrow_device_type_code": "Gerätetypcode",
    "sungrow_dsp_software": "DSP-Software-Version",
    "sungrow_inverter_serial": "Seriennummer",
    "sungrow_inverter_state": "Betriebszustand",
    "sungrow_protocol_version": "Protokollversion",
    "sungrow_version_1": "Firmware-Version Teil 1",
    "sungrow_version_2": "Firmware-Version Teil 2",
    "sungrow_version_3": "Firmware-Version Teil 3",
    "sungrow_version_4_sungrow_battery": "Firmware-Version Teil 4 (Sungrow-Batterie)",
    # -- energy: today, the total, this month and this year ---------------
    "daily_battery_charge": "Tägliche Batterie-Ladeenergie",
    "daily_battery_charge_from_pv": "Tägliche Batterie-Ladeenergie aus PV",
    "daily_battery_discharge": "Tägliche Batterie-Entladeenergie",
    "daily_consumed_energy": "Tägliche Energieaufnahme Verbraucher",
    "daily_consumed_energy_filtered": (
        "Tägliche Energieaufnahme Verbraucher (geglättet)"
    ),
    "daily_direct_energy_consumption": "Täglicher Direktverbrauch",
    "daily_exported_energy": "Täglich eingespeiste Energie",
    "daily_exported_energy_from_pv": "Täglich aus PV eingespeiste Energie",
    "daily_imported_energy": "Täglich bezogene Energie",
    "daily_pv_generation": "Tägliche PV-Erzeugung",
    "daily_pv_generation_battery_discharge": (
        "Tägliche PV-Erzeugung und Batterieentladung"
    ),
    "direct_consumption_this_month": "Direktverbrauch diesen Monat",
    "direct_consumption_this_year": "Direktverbrauch dieses Jahr",
    "export_from_pv_this_month": "Einspeisung aus PV diesen Monat",
    "export_from_pv_this_year": "Einspeisung aus PV dieses Jahr",
    "pv_generation_this_month": "PV-Erzeugung diesen Monat",
    "pv_generation_this_year": "PV-Erzeugung dieses Jahr",
    "total_battery_charge": "Gesamte Batterie-Ladeenergie",
    "total_battery_charge_from_pv": "Gesamte Batterie-Ladeenergie aus PV",
    "total_battery_discharge": "Gesamte Batterie-Entladeenergie",
    "total_consumed_energy": "Gesamte Energieaufnahme Verbraucher",
    "total_direct_energy_consumption": "Gesamter Direktverbrauch",
    "total_exported_energy": "Gesamt eingespeiste Energie",
    "total_exported_energy_from_pv": "Gesamt aus PV eingespeiste Energie",
    "total_imported_energy": "Gesamt bezogene Energie",
    "total_pv_generation": "Gesamte PV-Erzeugung",
    "total_pv_generation_battery_discharge": (
        "Gesamte PV-Erzeugung und Batterieentladung"
    ),
    # -- the battery, as the inverter sees it -----------------------------
    "battery_capacity_high_precision": "Batteriekapazität (hohe Genauigkeit)",
    "battery_charge": "Gespeicherte Energie",
    "battery_charge_health_rated": "Gespeicherte Energie (gesundheitsbereinigt)",
    "battery_charge_nominal": "Gespeicherte Energie (nominal)",
    "battery_charging_power": "Batterie-Ladeleistung",
    "battery_charging_power_signed": "Batterie-Ladeleistung (mit Vorzeichen)",
    "battery_current": "Batteriestrom",
    "battery_discharging_power": "Batterie-Entladeleistung",
    "battery_discharging_power_signed": "Batterie-Entladeleistung (mit Vorzeichen)",
    "battery_level": "Batterie-Ladestand",
    "battery_level_nominal": "Batterie-Ladestand (nominal)",
    "battery_power": "Batterieleistung",
    "battery_state_of_health": "Batterie-Gesundheitszustand",
    "battery_temperature": "Batterietemperatur",
    "battery_voltage": "Batteriespannung",
    "bms_max_charging_current": "BMS maximaler Ladestrom",
    "bms_max_discharging_current": "BMS maximaler Entladestrom",
    # -- the SBR pack, which is its own device ----------------------------
    "battery_cell_voltage_spread": "Zellspannungsdifferenz",
    "battery_max_cell_module": "Modul mit höchster Zelle",
    "battery_max_cell_number": "Höchste Zellnummer",
    "battery_max_cell_voltage": "Höchste Zellspannung",
    "battery_max_module_temperature": "Temperatur wärmstes Modul",
    "battery_max_module_temperature_module": "Wärmstes Modul",
    "battery_min_cell_module": "Modul mit niedrigster Zelle",
    "battery_min_cell_number": "Niedrigste Zellnummer",
    "battery_min_cell_voltage": "Niedrigste Zellspannung",
    "battery_min_module_temperature": "Temperatur kühlstes Modul",
    "battery_min_module_temperature_module": "Kühlstes Modul",
    **{
        f"battery_module_{n}_max_cell_voltage": f"Modul {n} höchste Zellspannung"
        for n in range(1, 9)
    },
    **{
        f"battery_module_{n}_min_cell_voltage": f"Modul {n} niedrigste Zellspannung"
        for n in range(1, 9)
    },
    "battery_pack_current": "Packstrom",
    "battery_pack_level": "Pack-Ladestand",
    "battery_pack_state_of_health": "Pack-Gesundheitszustand",
    "battery_pack_temperature": "Packtemperatur",
    "battery_pack_total_charge": "Gesamte Pack-Ladeenergie",
    "battery_pack_total_discharge": "Gesamte Pack-Entladeenergie",
    "battery_pack_voltage": "Packspannung",
    # -- the meter and backup output, per phase ---------------------------
    "meter_active_power": "Zähler Wirkleistung",
    "meter_channel_2_total_active_power": "Zähler Kanal 2 Gesamtwirkleistung",
    **{
        f"meter_channel_2_phase_{p}_active_power": (
            f"Zähler Kanal 2 Phase {p.upper()} Wirkleistung"
        )
        for p in "abc"
    },
    **{
        f"meter_phase_{p}_{quantity}": f"Zähler Phase {p.upper()} {german}"
        for p in "abc"
        for quantity, german in (
            ("active_power", "Wirkleistung"),
            ("current", "Strom"),
            ("voltage", "Spannung"),
        )
    },
    **{
        f"backup_phase_{p}_{quantity}": f"Backup Phase {p.upper()} {german}"
        for p in "abc"
        for quantity, german in (
            ("current", "Strom"),
            ("power", "Leistung"),
            ("voltage", "Spannung"),
        )
    },
    **{
        f"phase_{p}_{quantity}": f"Phase {p.upper()} {german}"
        for p in "abc"
        for quantity, german in (
            ("current", "Strom"),
            ("power", "Leistung"),
            ("voltage", "Spannung"),
        )
    },
    # -- the PV trackers --------------------------------------------------
    **{
        f"mppt{n}_{quantity}": f"MPPT{n} {german}"
        for n in range(1, 5)
        for quantity, german in (
            ("current", "Strom"),
            ("energy", "Energie"),
            ("power", "Leistung"),
            ("voltage", "Spannung"),
        )
    },
    # -- discharge schedule ------------------------------------------------
    "weekday_discharge_window_1": "Entladefenster Werktag 1",
    "weekday_discharge_window_2": "Entladefenster Werktag 2",
    "weekend_discharge_window_1": "Entladefenster Wochenende 1",
    "weekend_discharge_window_2": "Entladefenster Wochenende 2",
    # -- the wallbox, which is its own device -----------------------------
    "wallbox_available_current": "Freigegebener Ladestrom",
    "wallbox_charging_power": "Ladeleistung",
    "wallbox_charging_status": "Ladestatus",
    "wallbox_control_pilot_voltage": "Control-Pilot-Spannung",
    "wallbox_firmware_version": "Firmware-Version",
    "wallbox_lifetime_energy": "Gesamte Ladeenergie",
    "wallbox_maximum_charging_power": "Maximale Ladeleistung",
    "wallbox_minimum_charging_power": "Minimale Ladeleistung",
    "wallbox_output_current_setting": "Ladestrom-Sollwert",
    "wallbox_phase_a_current": "Ladestrom Phase A",
    "wallbox_phase_a_voltage": "Phase A Spannung",
    "wallbox_phase_b_current": "Ladestrom Phase B",
    "wallbox_phase_b_voltage": "Phase B Spannung",
    "wallbox_phase_c_current": "Ladestrom Phase C",
    "wallbox_phase_c_voltage": "Phase C Spannung",
    "wallbox_phase_mode": "Phasenmodus",
    "wallbox_rated_current": "Maximaler Ladestrom",
    "wallbox_session_energy": "Energie der Ladesitzung",
    "wallbox_start_mode": "Startmodus",
    # -- an SG string inverter --------------------------------------------
    "sg_bus_voltage": "Zwischenkreisspannung",
    "sg_daily_direct_energy_consumption": "Täglicher Direktverbrauch",
    "sg_daily_exported_energy": "Täglich eingespeiste Energie",
    "sg_daily_imported_energy": "Täglich bezogene Energie",
    "sg_daily_pv_generation": "Tägliche PV-Erzeugung",
    "sg_daily_running_time": "Tägliche Laufzeit",
    "sg_grid_frequency": "Netzfrequenz",
    "sg_inverter_temperature": "Gerätetemperatur",
    "sg_load_power": "Leistungsaufnahme Verbraucher",
    "sg_meter_active_power": "Zähler Wirkleistung",
    "sg_monthly_pv_generation": "Monatliche PV-Erzeugung",
    **{
        f"sg_meter_phase_{p}_power": f"Zähler Phase {p.upper()} Leistung" for p in "abc"
    },
    **{
        f"sg_mppt{n}_{quantity}": f"MPPT{n} {german}"
        for n in range(1, 13)
        for quantity, german in (
            ("current", "Strom"),
            ("energy", "Energie"),
            ("power", "Leistung"),
            ("voltage", "Spannung"),
        )
    },
    "sg_negative_voltage_to_ground": "Negative Spannung gegen Erde",
    **{
        f"sg_phase_{p}_{quantity}": f"Phase {p.upper()} {german}"
        for p in "abc"
        for quantity, german in (("current", "Strom"), ("voltage", "Spannung"))
    },
    "sg_power_factor": "Leistungsfaktor",
    "sg_power_limitation": "Leistungsgrenze aktiv",
    "sg_power_limitation_setting": "Leistungsgrenze",
    "sg_reactive_power": "Blindleistung",
    "sg_total_active_power": "Gesamte Wirkleistung",
    "sg_total_apparent_power": "Gesamte Scheinleistung",
    "sg_total_dc_power": "Gesamte PV-Eingangsleistung",
    "sg_total_direct_energy_consumption": "Gesamter Direktverbrauch",
    "sg_total_exported_energy": "Gesamt eingespeiste Energie",
    "sg_total_imported_energy": "Gesamt bezogene Energie",
    "sg_total_pv_generation": "Gesamte PV-Erzeugung",
    "sg_total_running_time": "Gesamte Laufzeit",
    "sg_work_state": "Betriebszustand",
}

#: A word in an English name, and the German stem the name must then contain,
#: so one idea has one German word across 319 names. Matched on whole English
#: words and on the lower-cased German name.
GERMAN_TERMS: dict[str, str] = {
    "alarm": "alarm",
    "current": "strom",
    "daily": "tägl",
    "energy": "energie",
    "fault": "fehler",
    "firmware": "firmware",
    "frequency": "frequenz",
    "month": "monat",
    "monthly": "monatlich",
    "phase": "phase",
    "power": "leistung",
    "temperature": "temperatur",
    "total": "gesamt",
    "version": "version",
    "voltage": "spannung",
    "weekday": "werktag",
    "weekend": "wochenende",
    "year": "jahr",
}

#: Where an English word is there and its German stem rightly is not, by word.
#: Each is a name that says the idea another way, and says which.
GERMAN_EXEMPT: dict[str, frozenset[str]] = {
    # "Einspeisung" and "Netzbezug" are the grid's own words for exporting and
    # importing power.
    "power": frozenset(
        {
            "exporting_power",
            "exporting_power_delay",
            "importing_power",
            "importing_power_delay",
        }
    ),
    # "Direktverbrauch" is the German for direct energy consumption.
    "energy": frozenset(
        {
            "daily_direct_energy_consumption",
            "total_direct_energy_consumption",
            "sg_daily_direct_energy_consumption",
            "sg_total_direct_energy_consumption",
        }
    ),
}

#: **Open questions on a name**, by translation key, shown under its table in
#: `doc/entity_names.md` as "To discuss". Each says what the entity is
#: and offers names to choose from; an entry goes once its name is decided.
NAME_DISCUSSION: dict[str, str] = {}


#: **German for every other text in `strings.json`**: the setup and
#: options flows, selector options, repairs, actions, exceptions and the
#: select states -- everything but the entity names above. By dotted path, in
#: `german_texts.json` because a paragraph does not fit a line of source.
#: Decided beside the English, like `GERMAN`, and written into `de.json` the
#: same way. `tests/test_naming_convention.py` holds each to its
#: English text's placeholders, markup and paragraph structure.
GERMAN_TEXTS: dict[str, str] = json.loads(
    Path(__file__).with_name("german_texts.json").read_text(encoding="utf-8")
)


def text_leaves(document: dict[str, object]) -> dict[str, str]:
    """Return every text of `strings.json` that is not an entity name.

    By dotted path, in file order: the keys of `GERMAN_TEXTS`. An entity's
    name is a leaf too, but belongs to `GERMAN`, so it is left out here; an
    entity's other leaves (a select's states) are not.
    """
    found: dict[str, str] = {}

    def walk(node: object, path: list[str]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, [*path, key])
        else:
            found[".".join(path)] = str(node)

    for top, value in document.items():
        if top != "entity":
            walk(value, [top])
            continue
        assert isinstance(value, dict)
        for domain, entries in value.items():
            for key, entry in entries.items():
                for field, text in entry.items():
                    if field != "name":
                        walk(text, ["entity", domain, key, field])
    return found


_ACRONYM_BY_UPPER = {a.upper(): a for a in ACRONYMS}
_PROPER_BY_UPPER = {p.upper(): p for p in PROPER_NOUNS}
_PUNCTUATION = "()"


def _bare(token: str) -> str:
    """Return a token without the punctuation the rules do not judge."""
    return token.strip(_PUNCTUATION)


def _canonical(token: str, first: bool) -> str | None:
    """Return the one spelling this token is allowed, or None if free."""
    bare = _bare(token)
    upper = bare.upper()
    if upper in _ACRONYM_BY_UPPER:
        return _ACRONYM_BY_UPPER[upper]
    if upper in _PROPER_BY_UPPER:
        return _PROPER_BY_UPPER[upper]
    if not bare.isalpha():
        # Numbers, "&", "health-rated": nothing to enforce.
        return None
    if len(bare) == 1:
        # "Phase A current" — a single letter names a phase, not a word.
        return bare.upper()
    if first:
        return bare[:1].upper() + bare[1:].lower()
    return bare.lower()


def modern_name(key: str, legacy_name: str) -> str:
    """Return the name this entity should carry, from the one the YAML gave it."""
    if key in OVERRIDES:
        return OVERRIDES[key]

    words = legacy_name.split()
    # Home Assistant already says the device name.
    while len(words) > 1 and words[0].lower() in DEVICE_WORDS:
        words = words[1:]

    fixed: list[str] = []
    for index, token in enumerate(words):
        canonical = _canonical(token, first=index == 0)
        if canonical is None:
            fixed.append(token if index == 0 else token.lower())
        else:
            fixed.append(token.replace(_bare(token), canonical))
    return " ".join(fixed)


def violations(key: str, name: str, diagnostic: bool) -> list[str]:
    """Return every way this name breaks the convention. Empty means it holds.

    This is the rule, and it is checked against the committed names rather than
    against `modern_name`'s output — otherwise an override could quietly opt
    itself out of the convention it exists to serve.
    """
    problems: list[str] = []
    words = name.split()

    if not name.strip():
        return [f"{key}: empty name"]
    if words[0].lower() in DEVICE_WORDS:
        problems.append(
            f"{key}: starts with {words[0]!r}, which Home Assistant already "
            "prefixes as the device name"
        )
    for index, token in enumerate(words):
        canonical = _canonical(token, first=index == 0)
        if canonical is not None and _bare(token) != canonical:
            problems.append(f"{key}: {_bare(token)!r} should be {canonical!r}")
        if re.fullmatch(r"[A-Za-z]+\.", token):
            problems.append(f"{key}: {token!r} abbreviates with a full stop")
        for part in re.split(r"[^A-Za-z]+", token):
            if part.lower() in BANNED_WORDS:
                spelled = BANNED_WORDS[part.lower()]
                problems.append(f"{key}: {part!r} should be spelled {spelled!r}")
    if words[-1].lower() == "raw" and not diagnostic:
        problems.append(
            f"{key}: ends in 'raw' but is not EntityCategory.DIAGNOSTIC — a raw "
            "code belongs under Diagnostic, or the name should not say 'raw'"
        )
    return problems
