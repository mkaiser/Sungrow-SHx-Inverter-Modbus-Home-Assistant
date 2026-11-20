"""Which registers the integration will write, and within what bounds.

Milestone 3 in slices, safest first. The write path has never run against real
hardware, and `EMS mode selection` is not where anybody wants to find out
about that — so this table starts with the settings whose worst case is a
battery that charges to the wrong percentage, and grows once the mechanism is
proven.

**Writability is declared here and nowhere else.** `registers.py` marks
exactly these fields `writable=True` -- `tests/test_writes.py` fails if the two
disagree -- so the library refuses a write to anything this table does not
name, and `scripts/generate/descriptions.py` builds the entities from the same
rows. A register the integration cannot write is a
register it cannot write by accident.

Every bound was read from two sources that agree: the YAML package's own
`number:` templates, which are field-proven, and *Communication Protocol of
Residential Hybrid Inverter* V1.1.11. `tests/test_writes.py` re-extracts the
YAML's bounds and fails if this table drifts from them.

Not here yet, deliberately:

* the **power** limits — `battery_max_charge_power` and friends. Their upper
  bound is `!secret sungrow_modbus_battery_max_power` in the YAML, a value the
  user supplies, and deciding where the integration gets it instead is a
  design question rather than a transcription;
* everything the YAML guards behind its **danger-mode** toggle: EMS mode,
  forced charge/discharge, backup mode, the inverter start/stop buttons.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class Number(TypedDict, total=False):
    """One writable register exposed as a `number` entity."""

    field: str
    """The register field, which is read and written by the same entity."""

    legacy_unique_id: str
    """The YAML `number` template's unique_id, so its entity id can be kept."""

    minimum: float
    maximum: float
    step: float

    unit: str
    """`%`, `W` or `A`. Decides the device class too."""

    minimum_field: str
    """Read the lower bound from this register instead of using `minimum`.

    The inverter knows its own limits better than a table does. The YAML did
    this for the export power limit, whose bounds are registers 5622 and 5623,
    and it was right to.
    """

    maximum_field: str
    """Read the upper bound from this register instead of using `maximum`."""

    requires: str
    """The `Capability` this control needs, or absent where it needs none.

    Declared here for the same reason writability is: one table, and the
    entities derived from it cannot disagree with it. A blanket rule --
    `BATTERY` for everything except the export limit -- is wrong in a way that
    is not cosmetic: on an SH*RS, where the start-power pair below is reported
    absent (issue #743), `BATTERY` is present whenever a battery is, so both
    entities would be created **writable** against registers that are not
    there.
    """

    key: str
    """The entity key, where the field's own is not the name it should have."""

    maximum_from_battery: bool
    """Cap at what the battery will take.

    V1.1.11: "the charging and discharging power range is from 0 to BDC rated
    power (register 5628)". That is the *inverter's* ceiling; the pack has its
    own, and the lower of the two is the real one. Resolved at runtime — see
    `battery/power.py` for where each candidate comes from.
    """


#: Step 1: the state-of-charge limits. Percentages with static bounds the
#: specification states outright, no unit ambiguity, and a worst case of a
#: battery held at the wrong level.
NUMBERS: tuple[Number, ...] = (
    # Spec reg 13059, U16, 0.0~50.0, 0.1%, Read-Write. The register's
    # resolution is 0.1% but the step stays 1, as the YAML has it: tenths of a
    # percent of state of charge are not a setting anybody wants to make.
    # Set above the battery's charge it buys electricity: on P020 the inverter
    # charged from the grid at the charge limit (33047, 4500 W) and reported
    # 0x8000 Stop until set back (wiki: mkaiser-forced-startup-2026-11-08,
    # doc/integration_help.md, Known limitations).
    {
        "field": "battery_min_soc",
        "requires": "BATTERY",
        "unit": "%",
        "legacy_unique_id": "uid_battery_min_soc",
        "minimum": 0,
        "maximum": 50,
        "step": 1,
    },
    # Spec reg 13058, U16, 50.0~100.0, 0.1%, Read-Write.
    {
        "field": "battery_max_soc",
        "requires": "BATTERY",
        "unit": "%",
        "legacy_unique_id": "uid_battery_max_soc",
        "minimum": 50,
        "maximum": 100,
        "step": 1,
    },
    # Spec reg 13100, U16, 0~100, whole percent, Read-Write. Below this the
    # battery charges from the grid in an outage, so it is a safety setting
    # rather than an optimisation.
    {
        "field": "battery_reserved_soc_for_backup",
        "requires": "BATTERY",
        "unit": "%",
        "legacy_unique_id": "uid_battery_reserved_soc_for_backup",
        "minimum": 0,
        "maximum": 100,
        "step": 1,
    },
)

#: Step 2: the power limits. Bounds come from the hardware rather than a
#: table wherever the hardware states them, which the specification is
#: explicit about for the charge and discharge maxima.
NUMBERS += (
    # Spec reg 33047, U16, 0.01 kW, Read-Write. Range 0..BDC rated power
    # (reg 5628), further limited by the pack itself.
    {
        "field": "battery_max_charge_power",
        "requires": "BATTERY",
        "legacy_unique_id": "uid_battery_max_charge_power",
        "minimum": 10,
        "maximum": 0,
        "maximum_from_battery": True,
        "step": 100,
        "unit": "W",
    },
    # Spec reg 33048, U16, 0.01 kW, Read-Write.
    {
        "field": "battery_max_discharge_power",
        "requires": "BATTERY",
        "legacy_unique_id": "uid_battery_max_discharge_power",
        "minimum": 10,
        "maximum": 0,
        "maximum_from_battery": True,
        "step": 100,
        "unit": "W",
    },
    # Spec reg 13074, U16, 1 W, Read-Write. The YAML read its bounds from
    # registers 5622 and 5623 rather than hardcoding them, which is right:
    # the inverter states what it will accept.
    {
        "field": "export_power_limit",
        "legacy_unique_id": "uid_export_power_limit",
        "minimum": 0,
        "maximum": 0,
        "minimum_field": "export_power_limit_min",
        "maximum_field": "export_power_limit_max",
        "step": 100,
        "unit": "W",
    },
)

#: The power the forced charge/discharge select uses. Spec reg 13052, U16,
#: **1 W**, Read-Write, "0-100% of BDC rated power (RO register 5628)" -- so
#: the same ceiling as the charge and discharge maxima, and note the unit: 1 W
#: here where 33047/33048 are 0.01 kW. Two neighbouring settings for the same
#: quantity in different units is exactly the kind of thing a single hand-typed
#: table gets wrong.
#:
#: It does nothing on its own. Without `battery_forced_charge_discharge` set to
#: charge or discharge, the inverter ignores it -- which is why the select came
#: first and this follows rather than the other way round.
NUMBERS += (
    {
        "field": "battery_forced_charge_discharge_power",
        "requires": "BATTERY",
        "legacy_unique_id": "uid_battery_forced_charge_discharge_power",
        "minimum": 0,
        "maximum": 0,
        "maximum_from_battery": True,
        "step": 100,
        "unit": "W",
    },
)

#: The two thresholds that stop a battery cycling between charge and
#: discharge. **Undocumented**, and the only entries here that are.
#:
#: They sit at YAML addresses 33148 and 33149 — **registers 33149 and 33150**
#: — and neither register exists in specification V1.1.11. The specification
#: has register 33148, "Charging/Discharging Power - Wide range", which is a
#: different register and a different thing. The YAML traces these two to
#: photovoltaikforum.com and forum.iobroker.net rather than to any datasheet,
#: and reports them absent on SHxRS (issue #743), which is why
#: `Capability.BATTERY_START_POWER` gates them.
#:
#: Writing a register whose identity cannot be confirmed is the class of
#: mistake this table exists to prevent. These two are writable on the
#: maintainer's decision, on this evidence:
#:
#: * the reference SH10RT reads 200 W and 100 W, stable across six reads,
#:   which is a plausible pair of thresholds and not a coincidence;
#: * the YAML has exposed both as writable for years, to many users, with no
#:   report of either doing something other than what its name says;
#: * the write round trip was verified on real hardware — read, write the same
#:   value, write a changed one, read it back, restore.
#:
#: What is still not known is what a *third-party* inverter family does with
#: them, so the capability gate stays and this comment stays with it.
#:
#: The bounds are the YAML's, and its author was explicit that 1000 W is a
#: judgement rather than a limit the device states: "I am pretty confident,
#: that a max: value for the number is ok with 1000W. Please open an issue, if
#: other values are needed."
#:
#: The behaviour worth knowing before setting one, from the YAML's comments:
#: the threshold is compared against the *achievable* charging power, not
#: against the available surplus; set above the battery's maximum charging
#: power, charging never starts at all; and when achievable power drops below
#: it, charging stops, ignoring the limit at register 33047 — so a value close
#: to the battery's maximum can stop a charge before 100%.
NUMBERS += (
    {
        "field": "battery_charging_start_power",
        "requires": "BATTERY_START_POWER",
        "legacy_unique_id": "uid_battery_charging_start_power",
        "minimum": 0,
        "maximum": 1000,
        "step": 10,
        "unit": "W",
    },
    {
        "field": "battery_discharging_start_power",
        "requires": "BATTERY_START_POWER",
        "legacy_unique_id": "uid_battery_discharging_start_power",
        "minimum": 0,
        "maximum": 1000,
        "step": 10,
        "unit": "W",
    },
)

#: Register 32998, the site import limit (#546, #785), outside Sungrow's
#: document: 0.01 kW per count, 1-5000 accepted, 0 and 5001 refused (P020,
#: P022, P023). Shown in W with a 10 W step, one count, like the other power
#: settings; the entity converts from the field's kW. It caps only a charge
#: the inverter draws from the grid, counting PV, and never the house load:
#: watched, it left PV, export, a charge from PV and a battery held at its
#: discharge limit alone. Gated by `SITE_IMPORT_LIMIT_CONTROL`, granted per
#: watched firmware in `capabilities.CONFIRMED_ON_FIRMWARE`.
NUMBERS += (
    {
        "field": "site_import_power_limit",
        "requires": "SITE_IMPORT_LIMIT_CONTROL",
        "unit": "W",
        "minimum": 10,
        "maximum": 50000,
        "step": 10,
    },
)

#: The forced-charging schedule's target states of charge, registers 33214
#: and 33219 (V1.1.16, 0~100 %, whole percent). No YAML entity, so no legacy
#: id; the times beside them are `TIMES` below.
NUMBERS += (
    {
        "field": "forced_charging_target_soc_1",
        "requires": "FORCED_CHARGING",
        "unit": "%",
        "minimum": 0,
        "maximum": 100,
        "step": 1,
    },
    {
        "field": "forced_charging_target_soc_2",
        "requires": "FORCED_CHARGING",
        "unit": "%",
        "minimum": 0,
        "maximum": 100,
        "step": 1,
    },
)

#: The wallbox the inverter manages: its user-defined current, register 33545
#: (0.1 A), outside Sungrow's document. Watched at gerd's on P022: the car
#: followed 6, 8, 10 and 12 A; 5 A was refused, so 6 A is the floor, and 33 A
#: was taken on a 32 A wallbox, so the inverter does not cap it. 32 A, the
#: largest Sungrow wallbox's rating, is the ceiling here, and the entity
#: narrows it to what this wallbox reports at input 21263 -- 16.0 A on an
#: AC011E-01 -- wherever that register is read (`number.py`). The inverter
#: takes the write **only in user-defined mode**; the number refuses before
#: writing in any other (`number.py`). Gated by `EV_CHARGER_CONTROL`, which
#: `capabilities.CONFIRMED_ON_FIRMWARE` grants per watched firmware.
NUMBERS += (
    {
        "field": "ev_charger_user_current",
        "key": "ev_charger_user_current",
        "requires": "EV_CHARGER_CONTROL",
        "unit": "A",
        "minimum": 6,
        "maximum": 32,
        "step": 1,
    },
)


class Switch(TypedDict):
    """One writable register exposed as a `switch`."""

    field: str
    #: The entity key, where the field's own would collide with another
    #: platform's entity reading the same register.
    key: NotRequired[str]
    legacy_unique_id: NotRequired[str]
    requires: NotRequired[str]
    on: int
    off: int
    #: Words the register holds that mean off but cannot be written: a
    #: factory value outside the two the specification defines.
    also_off: NotRequired[tuple[int, ...]]
    #: Seconds after an off is written for which a read of the on word is
    #: not believed: a register that keeps reading on for a while after it
    #: took the off.
    hold_off_seconds: NotRequired[float]


#: Step 3: the three mode flags. Each is one holding register holding 0xAA or
#: 0x55, which the specification states outright for all three, so there is no
#: decoding to get wrong -- only the question of what turning it off does.
#:
#: Note the names. The YAML's are what users have, so they are kept, but they
#: are not the specification's, and knowing which is which saves a reader
#: reconciling two documents:
#:
#: | YAML | Specification | Register |
#: | --- | --- | --- |
#: | Backup Mode | Off-grid option | 13075 |
#: | Export power limit | Feed-in Limitation | 13087 |
#: | Load adjustment mode | Load ON/OFF mode | 13011 |
SWITCHES: tuple[Switch, ...] = (
    {
        "field": "backup_mode_raw",
        "legacy_unique_id": "sg_backup_mode_switch",
        "on": 0xAA,
        "off": 0x55,
    },
    {
        "field": "export_power_limit_mode_raw",
        "legacy_unique_id": "sg_export_power_limit_switch",
        "on": 0xAA,
        "off": 0x55,
    },
    {
        "field": "load_adjustment_mode_enable_raw",
        "legacy_unique_id": "sg_load_adjustment_mode_switch",
        "on": 0xAA,
        "off": 0x55,
    },
    # Register 31211, outside the specification (#554, #738): on cuts PV
    # generation, off lets it run. No YAML entity, so no legacy id. Gated by
    # a capability no probe grants: `resolve` adds it only on firmware in
    # `capabilities.CONFIRMED_ON_FIRMWARE`, where the capability test saw a
    # write take DC power to zero -- a register answering 0x55 says it is
    # there, not what writing it does.
    #
    # Keyed `cut_pv_generation`, "Cut PV generation": the action the switch
    # performs, beside the binary sensor "PV generation cut" that reports the
    # state wherever the register answers.
    {
        "field": "pv_generation_cut_raw",
        "key": "cut_pv_generation",
        "requires": "PV_GENERATION_CUT_CONTROL",
        "on": 0xAA,
        "off": 0x55,
    },
    # Register 33208, V1.1.16: "0xAA: Enable, 0x55: Disable". Turns the
    # schedule below on; the times and targets do nothing without it.
    {
        "field": "forced_charging_raw",
        "key": "forced_charging_schedule",
        "requires": "FORCED_CHARGING",
        "on": 0xAA,
        "off": 0x55,
    },
    # Register 13017, V1.1.7's "Forced Startup Under Low SOC Standby": 0xAA
    # wakes an inverter waiting in standby with the battery at its minimum SoC
    # and no PV, which it otherwise does not leave until PV returns. The
    # specification names only 0xAA; watched on P023 (bar12) it is a switch:
    # 0xAA stays, reads back and keeps the inverter running, 0x55 sends it
    # back to standby, and every other word is refused with 0x04. Every SH-RT
    # reads 0 from the factory, which behaves as off and cannot be written
    # back, so 0 reads as off. Gated by `FORCED_STARTUP_CONTROL`, which
    # `capabilities.CONFIRMED_ON_FIRMWARE` grants per watched firmware.
    {
        "field": "forced_startup_under_low_soc_raw",
        "key": "forced_startup_under_low_soc",
        "requires": "FORCED_STARTUP_CONTROL",
        "on": 0xAA,
        "off": 0x55,
        "also_off": (0,),
    },
    # Register 33179, outside Sungrow's document (#785): the weekend
    # discharge schedule's own enable. Gated by `DISCHARGE_SCHEDULE_CONTROL`,
    # which `capabilities.CONFIRMED_ON_FIRMWARE` grants per watched firmware
    # -- moving every window away from now stopped a discharge at two houses.
    {
        "field": "weekend_discharge_raw",
        "key": "weekend_discharge_schedule",
        "requires": "DISCHARGE_SCHEDULE_CONTROL",
        "on": 0xAA,
        "off": 0x55,
    },
    # The wallbox the inverter manages (registers 33540 and 33550, outside
    # Sungrow's document; `sungrow_modbus.hybrid_inverter.ev_charger`).
    # Charging on/off: watched at gerd's on P022, off stopped the car within a
    # second, on started it within 7-15 s. Energy purchase (*Netzbezug*) in
    # PV surplus: followed the app's switch both ways. Both gated by
    # `EV_CHARGER_CONTROL`, granted per watched firmware. An off written while
    # a car charges reads back on for about 10 s (3-4 s after the write the
    # word reads 0xAA until about +13 s, the car at 0 A throughout; three
    # stops in four at gerd's, 2026-11-20), so the switch holds the off it
    # wrote for 20 s rather than show on for a poll.
    {
        "field": "ev_charger_charging_raw",
        "key": "ev_charger_charging",
        "requires": "EV_CHARGER_CONTROL",
        "on": 0xAA,
        "off": 0x55,
        "hold_off_seconds": 20,
    },
    {
        "field": "ev_charger_grid_purchase_raw",
        "key": "ev_charger_grid_purchase",
        "requires": "EV_CHARGER_CONTROL",
        "on": 0xAA,
        "off": 0x55,
    },
)


class Option(TypedDict):
    """One choice of a `select`."""

    slug: str
    """Translation key for the option, so its label can be translated."""

    value: int
    """What goes in the register."""

    label: str
    """English label, written into strings.json."""


class Select(TypedDict):
    """One writable enumeration register exposed as a `select`."""

    key: str
    field: str
    legacy_unique_id: NotRequired[str]
    requires: NotRequired[str]
    options: tuple[Option, ...]


#: Step 4: the enumerations. Every value below appears in both the YAML
#: package's own option map and V1.1.11, and they agree throughout -- including
#: `3: Disable` for the load control mode, which is easy to miss because the
#: specification lists it on a continuation line.
#:
#: These are the settings the YAML guards behind its danger-mode toggle. Their
#: worst case is not a wrong reading: putting an inverter into External EMS
#: mode with no EMS on the other end, or leaving it in forced discharge, is a
#: house that behaves oddly until somebody notices. So they arrive after the
#: limits, once the write path had been exercised.
SELECTS: tuple[Select, ...] = (
    # Spec reg 13050, Read-Write. The specification calls value 2 "Compulsory
    # mode"; the YAML calls it "Forced mode" and its own comment notes the
    # rename, so the label says both.
    {
        "key": "ems_mode",
        "field": "ems_mode_selection_raw",
        "legacy_unique_id": "uid_ems_mode",
        "options": (
            {"slug": "self_consumption", "value": 0, "label": "Self-consumption"},
            {"slug": "forced", "value": 2, "label": "Forced (compulsory)"},
            {"slug": "external_ems", "value": 3, "label": "External EMS"},
            {"slug": "vpp", "value": 4, "label": "VPP"},
        ),
    },
    # Spec reg 13051: 0xAA charge, 0xBB discharge, 0xCC stop. The power it
    # uses is register 13052, which is a separate setting and not yet written.
    {
        "key": "battery_forced_charge_discharge",
        "field": "battery_forced_charge_discharge_cmd_raw",
        "legacy_unique_id": "uid_battery_forced_charge_discharge",
        "requires": "BATTERY",
        "options": (
            {"slug": "stop", "value": 0xCC, "label": "Stop"},
            {"slug": "charge", "value": 0xAA, "label": "Forced charge"},
            {"slug": "discharge", "value": 0xBB, "label": "Forced discharge"},
        ),
    },
    # Spec reg 13002, Read-Write. Distinct from the load on/off *switch* at
    # 13011: this chooses which mode the load output runs in, that one turns
    # it on and off.
    {
        "key": "load_adjustment_mode",
        "field": "load_adjustment_mode_selection_raw",
        "legacy_unique_id": "uid_load_adjustment_mode",
        "options": (
            {"slug": "timing", "value": 0, "label": "Timing"},
            {"slug": "on_off", "value": 1, "label": "On/off"},
            {"slug": "power_optimised", "value": 2, "label": "Power optimised"},
            {"slug": "disabled", "value": 3, "label": "Disabled"},
        ),
    },
    # Spec reg 33209, "Forced Charging Valid Time": 0 weekday, 1 every day.
    {
        "key": "forced_charging_days",
        "field": "forced_charging_days_raw",
        "requires": "FORCED_CHARGING",
        "options": (
            {"slug": "weekdays", "value": 0, "label": "Weekdays"},
            {"slug": "every_day", "value": 1, "label": "Every day"},
        ),
    },
    # Register 33541, the managed wallbox's charging mode, as the app sets it.
    # Watched at gerd's on P022. 162 (quantity and time) is the ioBroker
    # thread's and was never seen, so it is not offered. A change has side
    # effects the select undoes (`select.py`): leaving user defined, and fast
    # to PV surplus, end the session; user defined switches charging on.
    {
        "key": "ev_charger_mode",
        "field": "ev_charger_mode_raw",
        "requires": "EV_CHARGER_CONTROL",
        "options": (
            {"slug": "fast", "value": 160, "label": "Fast charge"},
            {"slug": "pv_surplus", "value": 161, "label": "PV surplus"},
            {"slug": "user_defined", "value": 163, "label": "User defined"},
        ),
    },
)


class Time(TypedDict):
    """A time of day held in two writable registers, an hour and a minute."""

    key: str
    hour: str
    minute: str
    requires: NotRequired[str]


#: Step 6: the forced-charging windows, V1.1.16 registers 33210-33213 and
#: 33215-33218, each an hour (0~23) and a minute (0~59). One `time` entity per
#: pair, so a window reads 02:00-05:00 rather than as four numbers; setting
#: one writes the hour, then the minute.
TIMES: tuple[Time, ...] = tuple(
    {
        "key": f"forced_charging_{part}_{window}",
        "hour": f"forced_charging_{part}_{window}_hour",
        "minute": f"forced_charging_{part}_{window}_minute",
        "requires": "FORCED_CHARGING",
    }
    for window in (1, 2)
    for part in ("start", "end")
) + tuple(
    # The discharge windows, 33151-33158 and 33180-33187, outside Sungrow's
    # document (#785). Gated by `DISCHARGE_SCHEDULE_CONTROL`, which only a
    # watched write grants, so a house whose inverter answers these registers
    # still gets no control until its firmware is one where moving the
    # windows was seen to stop a discharge. An end of hour 24 reads as None
    # here and is written by the switch beside it (`WINDOW_ENDS`).
    {
        "key": f"{day}_discharge_{part}_{window}",
        "hour": f"{day}_discharge_{part}_{window}_hour",
        "minute": f"{day}_discharge_{part}_{window}_minute",
        "requires": "DISCHARGE_SCHEDULE_CONTROL",
    }
    for day in ("weekday", "weekend")
    for window in (1, 2)
    for part in ("start", "end")
)


class WindowEnd(TypedDict):
    """The "all day" switch beside a discharge window's end time."""

    key: str
    hour: str
    minute: str
    requires: str


#: Step 6b: a discharge window ends at **hour 24**, the end of the day, and a
#: Home Assistant `time` entity holds 00:00 to 23:59 only. Every untouched
#: house reads `00:00` to `24:00`, so a `time` alone could read such a window
#: (as None) but never write it back, and an owner who nudged one window
#: could not restore the other.
#:
#: So each window's end carries a switch beside its time: **on writes 24:00**,
#: off writes 23:59 and hands the end back to the time entity to set properly.
#: The forced-charging windows need none -- V1.1.16 documents them as 0~23,
#: which is why `TIMES` fits them as they are.
WINDOW_ENDS: tuple[WindowEnd, ...] = tuple(
    {
        "key": f"{day}_discharge_end_{window}_all_day",
        "hour": f"{day}_discharge_end_{window}_hour",
        "minute": f"{day}_discharge_end_{window}_minute",
        "requires": "DISCHARGE_SCHEDULE_CONTROL",
    }
    for day in ("weekday", "weekend")
    for window in (1, 2)
)


class Button(TypedDict):
    """One command register exposed as a `button`: a press writes one word."""

    field: str
    key: str
    requires: str
    press: int


#: Commands, which hold no state to show: a press writes `press` and that is
#: all. Each needs a capability only a watched write grants, because a
#: command's readback proves nothing. None yet: register 13017, once a button
#: here, turned out to be a switch (`SWITCHES`).
BUTTONS: tuple[Button, ...] = ()

#: Step 5: starting and stopping the inverter. **Not an entity.**
#:
#: Register 13000 is the one register in the map that turns the inverter off:
#: 0xCF boots, 0xCE shuts down. Reading it gives the running state, which is
#: why `running_state_raw` sits on it.
#:
#: The YAML package exposes this as two dashboard buttons behind a
#: danger-mode toggle. This integration exposes it as **service actions
#: instead**, for a reason a button cannot address: Home Assistant has no
#: confirmation dialog for a button, so a card copied from somebody else, a
#: stale automation, or a misclick while scrolling stops an inverter. An
#: action has to be written into a script or called from Developer Tools, and
#: it is registered as an **admin** action, so a non-admin user cannot call it
#: at all.
#:
#: Hiding and showing it stays a dashboard concern, which is what the YAML's
#: own danger-mode toggle already does well -- see
#: `legacy/dashboards/DefaultDashboard`.
#: Note the space. Register 13000 is in **both** of Sungrow's tables: Table 3
#: is read-only over function code 0x04, where reading it gives the running
#: state, and Table 4 is read/write over 0x03/0x06/0x10, where it is
#: Start/Stop. They are different address spaces, so the writable field is not
#: `running_state_raw` -- that one is in the input space and the library
#: rightly refuses to write it, which is how this was noticed. The holding-side
#: field is hand-written in `sungrow_modbus.hybrid_inverter.components.InverterControl`,
#: because nothing reads it and it therefore has no entity and no tier.
START_STOP = {
    "component": "control",
    "field": "start_stop",
    "start": 0xCF,
    "stop": 0xCE,
}

#: Field names the library is allowed to write. Derived, so it cannot disagree
#: with the entities built from the same table.
#: Only the tiered registers in `registers.py`. The start/stop register is
#: written in `components.py` and writable there, so it is not part of this
#: set -- and the test that asserts `registers.py`'s writable set *is* this
#: table stays exact.
WRITABLE_FIELDS: frozenset[str] = (
    frozenset(entry["field"] for entry in (*NUMBERS, *SWITCHES, *SELECTS, *BUTTONS))
    | frozenset(field for entry in TIMES for field in (entry["hour"], entry["minute"]))
    | frozenset(
        field for entry in WINDOW_ENDS for field in (entry["hour"], entry["minute"])
    )
)
