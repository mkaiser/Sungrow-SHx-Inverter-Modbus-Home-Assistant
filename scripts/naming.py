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
`sensor.sh10rt_serial_number`. Naming is therefore free now and expensive after
release, exactly like the domain rename was.

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
        # A bitmask, whose seven bits are the binary sensors.
        "power_flow_status",
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
