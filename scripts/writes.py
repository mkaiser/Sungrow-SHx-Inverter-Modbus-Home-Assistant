"""Which registers the integration will write, and within what bounds.

Milestone 3 in slices, safest first. The write path has never run against real
hardware, and `EMS mode selection` is not where anybody wants to find out
about that — so this table starts with the settings whose worst case is a
battery that charges to the wrong percentage, and grows once the mechanism is
proven.

**Writability is declared here and nowhere else.** `generate_registers.py`
marks exactly these fields `writable=True`, so the library refuses a write to
anything this table does not name, and `generate_numbers.py` builds the
entities from the same rows. A register the integration cannot write is a
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

from typing import TypedDict


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
    """`%` or `W`. Decides the device class too."""

    minimum_field: str
    """Read the lower bound from this register instead of using `minimum`.

    The inverter knows its own limits better than a table does. The YAML did
    this for the export power limit, whose bounds are registers 5622 and 5623,
    and it was right to.
    """

    maximum_field: str
    """Read the upper bound from this register instead of using `maximum`."""

    maximum_from_battery: bool
    """Cap at what the battery will take.

    V1.1.11: "the charging and discharging power range is from 0 to BDC rated
    power (register 5628)". That is the *inverter's* ceiling; the pack has its
    own, and the lower of the two is the real one. Resolved at runtime — see
    `battery.py` for where each candidate comes from.
    """


#: Step 1: the state-of-charge limits. Percentages with static bounds the
#: specification states outright, no unit ambiguity, and a worst case of a
#: battery held at the wrong level.
NUMBERS: tuple[Number, ...] = (
    # Spec reg 13059, U16, 0.0~50.0, 0.1%, Read-Write. The register's
    # resolution is 0.1% but the step stays 1, as the YAML has it: tenths of a
    # percent of state of charge are not a setting anybody wants to make.
    {
        "field": "battery_min_soc",
        "unit": "%",
        "legacy_unique_id": "uid_battery_min_soc",
        "minimum": 0,
        "maximum": 50,
        "step": 1,
    },
    # Spec reg 13058, U16, 50.0~100.0, 0.1%, Read-Write.
    {
        "field": "battery_max_soc",
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
#: Held back until 2026-09-07, on the grounds that writing a register whose
#: identity cannot be confirmed is the class of mistake this table exists to
#: prevent. Released by the maintainer on the evidence that now exists:
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
        "legacy_unique_id": "uid_battery_charging_start_power",
        "minimum": 0,
        "maximum": 1000,
        "step": 10,
        "unit": "W",
    },
    {
        "field": "battery_discharging_start_power",
        "legacy_unique_id": "uid_battery_discharging_start_power",
        "minimum": 0,
        "maximum": 1000,
        "step": 10,
        "unit": "W",
    },
)

#: Nothing is held back any more. Kept as an empty table rather than deleted,
#: because it is the mechanism by which shrinking the list is a deliberate
#: commit and not a side effect -- and the next undocumented register that
#: turns up needs somewhere to wait.
UNCONFIRMED: tuple[str, ...] = ()


class Switch(TypedDict):
    """One writable register exposed as a `switch`."""

    field: str
    legacy_unique_id: str
    on: int
    off: int


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
    legacy_unique_id: str
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
)

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
#: field is hand-written in `sungrow_modbus.components.InverterControl`,
#: because nothing reads it and it therefore has no entity and no tier.
START_STOP = {
    "component": "control",
    "field": "start_stop",
    "start": 0xCF,
    "stop": 0xCE,
}

#: Field names the library is allowed to write. Derived, so it cannot disagree
#: with the entities built from the same table.
#: Only the tiered, generated registers. The start/stop register is
#: hand-written in `components.py` and writable there, so it is not part of
#: what `generate_registers.py` marks -- and the test that asserts the
#: generated map's writable set *is* this table stays exact.
WRITABLE_FIELDS: frozenset[str] = frozenset(
    entry["field"] for entry in (*NUMBERS, *SWITCHES, *SELECTS)
)
