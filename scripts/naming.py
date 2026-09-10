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
    "battery_pack_voltage": "Pack voltage",
    "battery_pack_current": "Pack current",
    "battery_pack_temperature": "Pack temperature",
    "battery_pack_level": "Pack level",
    "battery_pack_state_of_health": "Pack state of health",
    "battery_pack_total_charge": "Pack total charge",
    "battery_pack_total_discharge": "Pack total discharge",
    # Highest and lowest rather than max and min, because these are readings
    # and not limits -- the inverter's "Battery max SoC" is a setting, and
    # reusing its word here would blur that. Warmest and coolest for the same
    # reason.
    "battery_max_cell_voltage": "Highest cell voltage",
    "battery_min_cell_voltage": "Lowest cell voltage",
    "battery_max_module_temperature": "Warmest module temperature",
    "battery_min_module_temperature": "Coolest module temperature",
    # The unpacked halves of the position words. `(module << 8) | cell`, so
    # each word becomes two entities -- see `SbrBatteryCells`.
    "battery_max_cell_module": "Highest cell module",
    "battery_max_cell_number": "Highest cell number",
    "battery_min_cell_module": "Lowest cell module",
    "battery_min_cell_number": "Lowest cell number",
    "battery_max_module_temperature_module": "Warmest module",
    "battery_min_module_temperature_module": "Coolest module",
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
    "wallbox_lifetime_energy": "Lifetime energy",
    "wallbox_charging_status": "Charging status",
    "wallbox_phase_a_voltage": "Phase A voltage",
    "wallbox_phase_a_current": "Phase A current",
    "wallbox_phase_b_voltage": "Phase B voltage",
    "wallbox_phase_b_current": "Phase B current",
    "wallbox_phase_c_voltage": "Phase C voltage",
    "wallbox_phase_c_current": "Phase C current",
    "wallbox_available_current": "Available current",
    # The Type 2 signalling line. Named for what it is rather than for what
    # it tells you, because what it tells you is a table: 12 V nothing
    # plugged in, 9 V connected and idle, 6 V charging.
    "wallbox_control_pilot_voltage": "Control pilot voltage",
    "wallbox_start_mode": "Start mode",
    "wallbox_rated_current": "Rated current",
    "wallbox_maximum_charging_power": "Maximum charging power",
    "wallbox_minimum_charging_power": "Minimum charging power",
    "wallbox_phase_mode": "Phase mode",
    "wallbox_firmware_version": "Firmware version",
    # "Output current setting" was the first name and it trips the `-ing`
    # rule on "setting" -- a noun there, not a present participle. Renamed
    # rather than exempted: the rule is a good one, a narrow exception would
    # weaken it for a name nobody prefers, and "configured" says the same
    # thing without the argument.
    "wallbox_output_current_setting": "Configured output current",
    # `-ing` on a binary sensor, which is what the convention reserves it
    # for: something happening right now.
    "wallbox_charging": "Charging",
    "wallbox_enabled": "Enabled",
    # -- corrections for a generator the inverter cannot see --------------
    #
    # No legacy name, like the wallbox's: the YAML package had no concept of
    # a second inverter on the supply. Both are named for what makes them
    # different from the register beside them, because that is the only
    # question a device page raises -- why are there two load figures?
    "corrected_load_power": "Corrected load power",
    # "Site" rather than "total": `sensor.total_dc_power` is already "Total
    # DC power", so the distinguishing word has to be the one that says
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
    # `-ing` was considered and rejected on the evidence: the three names in
    # this map that end in it -- Battery charging, Battery discharging, PV
    # generating -- are all binary sensors meaning "this is happening right
    # now", so "Export power limiting" would read as something observed
    # rather than something switched.
    #
    # A switch named for the mode register it writes is already the pattern
    # here: `switch.backup_mode` is "Backup mode". So this follows it, and
    # the number keeps the name a user would look for.
    "export_power_limit_mode": "Export power limit mode",
    # And the enable beside `select.load_adjustment_mode`, which owns the
    # longer name: the switch says whether load adjustment happens at all.
    "load_adjustment_mode_enable": "Load adjustment",
    # Not raw at all: register 13090 has a scale of 0.1 and a unit, and reads
    # 100.0 % on every machine surveyed. The YAML called it "raw" because it
    # sits beside the mode register, and the word has been describing the
    # neighbour ever since.
    "active_power_limitation_ratio_raw": "Active power limitation ratio",
    # APL is Sungrow's "active power limitation" -- capping the inverter's AC
    # output, as a grid operator's curtailment does. Spelled out because an
    # acronym only somebody who has read the forum thread would recognise is
    # not a name, and without "raw" because the number is all there is.
    #
    # **Experimental.** Register 31213 is not in Sungrow's protocol document;
    # it comes from community feedback in issue #554 and nobody here has
    # tested what it does. It stays a diagnostic number rather than becoming a
    # binary sensor because all three surveyed inverters read the same single
    # value, so its enum is assumed and not observed. `scripts/layout.py`
    # carries the same warning where the component is described.
    "apl_shutdown_at_zero_raw": "Active power limitation shutdown at zero",
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
    # `sungrow_modbus.smoothing` has always called smoothing. The module, the
    # docs and the entity finally agree.
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
    # "cmd" is banned below, and the slash reads better than three nouns in a
    # row; Home Assistant slugifies it away, so the entity_id is unaffected.
    "battery_forced_charge_discharge_cmd_raw": (
        "Battery forced charge/discharge command raw"
    ),
    "battery_forced_charge_discharge_power": "Battery forced charge/discharge power",
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
#: not created in modern mode. Settled 2026-09-09: "I prefer a clean cut more
#: over 100% backwards compatibility. Also those values are not very valuable,
#: so having them erased wouldn't be a big deal for the users."
#:
#: Each one **names what replaces it**, and that is the whole discipline
#: here: a clean cut removes duplication, not capability, and the only way to
#: know which is being removed is to say where the reading went instead.
#: `tests/test_sensor_descriptions.py` checks every replacement exists among
#: the entities modern mode does create -- written as a heuristic first, which
#: passed for fifteen of the seventeen and quietly guessed at the other two.
#:
#: Two kinds, both a second copy of something the user already has:
#:
#: * **Nine read-only sensors duplicating a `number`.** A Home Assistant
#:   number shows its value *and* sets it, so `sensor.battery_max_soc` beside
#:   `number.battery_max_soc` is one reading listed twice under one name. The
#:   YAML package needed both because a YAML `sensor` cannot be written.
#: * **Eight `_raw` codes whose decoded counterpart exists.**
#:   `backup_mode_raw` reads 170 or 85 where `switch.backup_mode` says on or
#:   off. Nobody should have to know that 170 means enabled.
#:
#: The four `_raw` codes **not** here -- `active_power_limitation_raw`, its
#: ratio, `apl_shutdown_at_zero_raw` and `pv_power_limitation_raw` -- are the
#: only exposure of their register, so dropping them would remove the
#: capability. They join this list when their friendly forms land.
#:
#: Consulted by `generate_sensors.py` only, so a field named here loses its
#: *sensor* and keeps its switch, select or number.
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
        # The two mode flags that replaced a raw number. They mirror a
        # setting rather than measure the house, which is what Diagnostic
        # means -- and their `number`/`select` counterparts, being writable,
        # are CONFIG instead.
        "active_power_limitation_enabled",
        "pv_power_limitation_enabled",
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
        # A configured limit rather than a measurement, like the ones above it.
        "feed_in_limitation_ratio",
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
    }
)

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
