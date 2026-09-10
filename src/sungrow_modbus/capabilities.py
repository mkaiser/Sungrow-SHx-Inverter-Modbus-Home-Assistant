"""What a particular inverter exposes, and how that is decided.

There is one register map for every model. What varies is which parts of it a
given device answers, and that comes from four different places — so it is
resolved from four different sources rather than guessed from one:

* the **model**, from the device type code in register 5000;
* the **phase count**, which register 5002 states outright, so it is never
  inferred;
* the **wiring** — a battery, a directly connected meter — which no register
  identifies, so it is probed;
* the **firmware**, which nothing predicts at all.

The knowledge encoded here was, until now, prose in `modbus_sungrow.yaml`:
comments like "only for SH*T inverters with 3 MPPTs" and "not available on
SHxRS". Prose cannot gate an entity. Note the shape of what those comments
say — they record where a feature is **absent**, on which model, learned from
somebody's bug report. So absence is what this module models, and presence is
what probing establishes.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum


class Capability(StrEnum):
    """Something a device may or may not have, gating a group of registers."""

    MPPT3 = "mppt3"
    """A third MPP tracker."""

    MPPT4 = "mppt4"
    """A fourth MPP tracker."""

    THREE_PHASE = "three_phase"
    """Three-phase output; register 5002 says so directly."""

    METER_DIRECT = "meter_direct"
    """A smart energy meter wired to the inverter rather than to an EMS.

    Sungrow's protocol marks the meter measurements "only valid when the
    inverter is directly connected to the smart energy meter", and an
    iHomeManager in the path silences them.
    """

    BATTERY = "battery"
    """Any battery, which most of the 13xxx block depends on."""

    SUNGROW_BATTERY = "sungrow_battery"
    """A Sungrow SBR or SBH specifically, not a third-party pack.

    The per-module registers at 10740-10788 are a Sungrow battery's own Modbus
    unit. A Pylontech answers the generic block and nothing there.
    """

    FIRMWARE_VERSIONS = "firmware_versions"
    """The firmware version registers."""

    SUB_CONTROLLER_FIRMWARE = "sub_controller_firmware"
    """The sub-controller firmware string, at register 2613.

    **Absent through a communication module, present over a cable.** Measured
    2026-09-08 across two houses: input 2612 refuses with exception 0x02,
    three attempts out of three, on every WiNet-S path -- two dongles, two
    dongle firmwares, two inverter models -- and reads normally on both
    direct-LAN readings of the same register map.

    This docstring used to say the reference SH10RT could not read register
    2611 or beyond at all. That was measured before `scripts/layout.py`
    existed: those registers arrive in a frame the device pads, and asking
    for the count in `layout.COUNTS` reads them. The same machine now reads
    all 27 blocks, three attempts each. What cannot read them is a dongle.
    """

    BATTERY_FIRMWARE = "battery_firmware"
    """The battery firmware string, at register 2629.

    The YAML package's own comment calls this the "fourth part of firmware
    string (only for sungrow batteries)", so a third-party pack is expected
    not to have it.
    """

    ACTIVE_POWER_LIMIT = "active_power_limit"
    """Active power limitation and its ratio."""

    BATTERY_START_POWER = "battery_start_power"
    """Battery charge and discharge start-power thresholds."""

    METER_CHANNEL_2 = "meter_channel_2"
    """A dual-channel energy meter, such as a DTSU666-20.

    Specification V1.1.9 added registers 13200-13207 for its second channel,
    and states they are "only valid when the inverter is connected to a
    dual-channel meter". A single-channel meter answers the first channel and
    nothing here.
    """

    FEED_IN_LIMITATION_RATIO = "feed_in_limitation_ratio"
    """The feed-in limitation expressed as a percentage (register 13088).

    Distinct from the active power limit ratio at 13090, which the YAML
    package already reads: the specification is explicit that feed-in
    limitation controls the **grid connection point** while power limiting
    controls the **inverter's AC output**. They are different measurements of
    different things.
    """

    PV_POWER_LIMITATION = "pv_power_limitation"
    """Whether PV generation itself may be limited (register 13018).

    "Only SHT are supported", so every other family answers 0xFFFF — which is
    what the reference SH10RT does.
    """


class Family(StrEnum):
    """The product line a device type code belongs to."""

    RS = "RS"
    """Single-phase hybrids, SH3.0RS to SH10RS."""

    MG = "MG"
    """MG5RL and up."""

    RT = "RT"
    """Three-phase hybrids, SH5.0RT to SH10RT and their variants."""

    T = "T"
    """The newer three-phase line, SH5T to SH25T."""

    K = "K"
    """The withdrawn SH*K series, still in the field."""


#: Device type code to family. Ranges rather than a per-model list, because
#: Sungrow allocates them in blocks and new models land inside those blocks.
_FAMILY_RANGES: tuple[tuple[int, int, Family], ...] = (
    (0x0D03, 0x0D0C, Family.K),
    (0x0D0D, 0x0D1B, Family.RS),
    (0x0D27, 0x0D2A, Family.MG),
    (0x0E00, 0x0E13, Family.RT),
    (0x0E20, 0x0E28, Family.T),
)

#: Where a capability is known to be absent, and where that was learned.
#: These are the YAML's comments turned into data. Absence only: a family not
#: listed here is not thereby known to *have* the capability, which is what
#: probing is for.
ABSENT_IN: dict[Capability, frozenset[Family]] = {
    # "only for SH*T inverters with 3 MPPTs"
    Capability.MPPT3: frozenset({Family.RS, Family.MG, Family.RT, Family.K}),
    # "only for inverters with 4 MPPTs (SH8|10RS)"
    Capability.MPPT4: frozenset({Family.MG, Family.RT, Family.T, Family.K}),
    # "MG5-6RL is not supported."
    Capability.ACTIVE_POWER_LIMIT: frozenset({Family.MG}),
    # "NOTE: SH3.0-10RS and MG5-6RL are NOT supported"
    Capability.FIRMWARE_VERSIONS: frozenset({Family.RS, Family.MG}),
    # "not available on SHxRS as per issue #743"
    Capability.BATTERY_START_POWER: frozenset({Family.RS}),
    # V1.1.9: "SH3.0-10RS and MG5-10RL are not supported."
    Capability.METER_CHANNEL_2: frozenset({Family.RS, Family.MG}),
    # V1.1.7: "MG5-10RL is not supported."
    Capability.FEED_IN_LIMITATION_RATIO: frozenset({Family.MG}),
    # V1.1.10: "Only SHT are supported."
    Capability.PV_POWER_LIMITATION: frozenset(
        {Family.RS, Family.MG, Family.RT, Family.K}
    ),
    # Single-phase families have no phase B or C.
    Capability.THREE_PHASE: frozenset({Family.RS, Family.MG, Family.K}),
}

#: What register 5002 reports. Asking beats inferring, so this outranks the
#: family table for THREE_PHASE.
OUTPUT_TYPES: dict[int, str] = {0: "single phase", 1: "3P4L", 2: "3P3L"}

#: 3P4L and 3P3L are both three-phase, so both resolve THREE_PHASE and get the
#: same entities. But they are **not** interchangeable, and one register table
#: entry says why:
#:
#:     22. A-B line voltage / phase A voltage   5019  U16  0.1V
#:         Refer to Output type (address: 5002)
#:         0: phase voltage; 1: phase voltage; 2: line voltage
#:
#: On 3P3L there is no neutral, so registers 5019-5021 report **line**
#: voltages -- A-B, B-C, C-A -- rather than phase-to-neutral. Same registers,
#: different measurement, and a value about 1.73x higher.
#:
#: **This integration does not yet model that**, and its entities are named
#: `Phase A voltage` for everybody. On a 3P3L inverter that name, and the
#: derived `phase_a_power` computed from it, are wrong -- they are line
#: quantities. Nobody has 3P3L hardware to test against, so it is recorded
#: here rather than guessed at; a fingerprint from such a system is what would
#: unblock it.
LINE_VOLTAGE_OUTPUT_TYPE = 2


def family_for(device_type_code: int | None) -> Family | None:
    """Return the product family for a device type code, if it is known."""
    if device_type_code is None:
        return None
    for low, high, family in _FAMILY_RANGES:
        if low <= device_type_code <= high:
            return family
    return None


def known_absent(device_type_code: int | None) -> frozenset[Capability]:
    """Return the capabilities this model is documented not to have.

    An unknown code returns nothing, which is deliberate: a model nobody has
    written down should be probed rather than assumed crippled.
    """
    family = family_for(device_type_code)
    if family is None:
        return frozenset()
    return frozenset(
        capability for capability, families in ABSENT_IN.items() if family in families
    )


#: A capability to a register that is present only when it is. The
#: specification defines 0xFFFF as "unavailable", so a field decoding to None
#: is the device saying the feature is not there — which beats any table.
PROBES: dict[Capability, tuple[str, ...]] = {
    Capability.MPPT3: ("mppt3_voltage", "mppt3_current"),
    Capability.MPPT4: ("mppt4_voltage", "mppt4_current"),
    Capability.THREE_PHASE: ("phase_b_voltage", "phase_c_voltage"),
    Capability.BATTERY: ("battery_voltage", "battery_level"),
    Capability.METER_DIRECT: ("meter_phase_a_active_power",),
    Capability.FIRMWARE_VERSIONS: ("inverter_firmware_version",),
    Capability.SUB_CONTROLLER_FIRMWARE: ("sungrow_version_3",),
    Capability.BATTERY_FIRMWARE: ("sungrow_version_4_sungrow_battery",),
    Capability.BATTERY_START_POWER: ("battery_charging_start_power",),
    Capability.ACTIVE_POWER_LIMIT: ("active_power_limitation_raw",),
    Capability.METER_CHANNEL_2: ("meter_channel_2_total_active_power",),
    Capability.FEED_IN_LIMITATION_RATIO: ("feed_in_limitation_ratio",),
    Capability.PV_POWER_LIMITATION: ("pv_power_limitation_raw",),
}


#: Capabilities that an all-zero answer must **not** grant.
#:
#: This is the numeric twin of the empty-string case `present()` handles: a
#: reading of nothing arriving as a value. Two independent sources of it have
#: been measured, and they need the same treatment for different reasons.
#:
#: **A cluster member with no hardware of its own answers zero.** Found on a
#: real master/slave pair, where the slave inverter has no battery and answers
#: 0 for voltage, level, temperature and capacity alike -- so the probe
#: granted `BATTERY` and the whole 13xxx block became entities reporting zero
#: forever. A lone inverter without storage answers 0xFFFF and never had the
#: problem, which is why only a cluster exposes it.
#:
#: **A WiNet-S substitutes zero for the specification's sentinel.** Measured
#: on one inverter read both ways on 2026-09-08: on its own LAN port MPPT3,
#: MPPT4 and the second meter channel all answered 0xFFFF, correctly absent;
#: through the dongle the same registers answered 0, which granted all three
#: and created **ten entities reporting zero forever**. Most users are behind
#: a dongle, so this is the wider of the two problems.
#:
#: Zero is only read as absence when **every** register of the capability is
#: zero. A flat battery reports level 0 at its nominal voltage, so level alone
#: must never decide it.
#:
#: For MPPT and meter channels, "absent" is a conclusion rather than a fact:
#: a real third tracker reads 0 V at night, and a real second meter channel
#: reads 0 W when nothing flows through it. Denying them is still right,
#: because the recovery is automatic and the alternative is not. Capabilities
#: are re-probed after every poll and the integration reloads when they
#: **grow**, so the first non-zero reading creates the entities -- an inverter
#: set up after dark gets its MPPT3 sensors at sunrise. Granting on zero has
#: no such recovery: nothing ever removes an entity, and a permanently empty
#: one is what `legacy/doc/cleanup_entities.md` exists to help people delete.
#:
#: Deliberately not conditional on the transport, though the transport is
#: knowable (register 6100). A rule that reads the same everywhere is easier
#: to reason about than one that changes behind a dongle, and the only cost of
#: applying it to a direct connection is the sunrise case above.
ZERO_MEANS_ABSENT: frozenset[Capability] = frozenset(
    {
        Capability.BATTERY,
        Capability.MPPT3,
        Capability.MPPT4,
        Capability.METER_CHANNEL_2,
    }
)


def probe(read: Callable[[str], object]) -> frozenset[Capability]:
    """Return the capabilities whose registers actually answered.

    `read` returns a register's decoded value, or None where the inverter
    reported the specification's "unavailable" sentinel. A capability counts
    as present when every register it needs came back with a value: a
    two-tracker inverter answers 0xFFFF for MPPT3 forever, and that is the
    device telling us, which is better evidence than any table.

    Some hardware reports its absence as zeros instead of that sentinel; for
    the capabilities in `ZERO_MEANS_ABSENT`, an all-zero answer is therefore
    read as absence too.
    """
    found: set[Capability] = set()
    for capability, fields in PROBES.items():
        try:
            values = [read(field) for field in fields]
        except AttributeError:
            continue
        if not values or any(v is None for v in values):
            continue
        if capability in ZERO_MEANS_ABSENT and all(v == 0 for v in values):
            continue
        found.add(capability)
    return frozenset(found)


def resolve(
    device_type_code: int | None,
    output_type: int | None = None,
    probed: frozenset[Capability] | None = None,
) -> frozenset[Capability]:
    """Work out what a device has, from what it said and what answered.

    Sources are applied in order of authority: what the device states about
    itself outranks what its model implies, and what actually answered a probe
    outranks both. Anything a probe found is kept even where the family table
    said it should not be there — the table is a record of bug reports, not a
    specification, and a device that answers is the better authority.
    """
    absent = known_absent(device_type_code)
    resolved = set(probed or frozenset())

    if output_type is not None:
        # Register 5002 is definitive about phases, so it lifts the family
        # table's veto rather than merely adding alongside it.
        if output_type in (1, 2):
            resolved.add(Capability.THREE_PHASE)
            absent = absent - {Capability.THREE_PHASE}
        else:
            resolved.discard(Capability.THREE_PHASE)
            absent = absent | {Capability.THREE_PHASE}

    return frozenset(resolved - (absent - set(probed or frozenset())))
