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

    ACTIVE_POWER_LIMIT = "active_power_limit"
    """Active power limitation and its ratio."""

    BATTERY_START_POWER = "battery_start_power"
    """Battery charge and discharge start-power thresholds."""


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
    # Single-phase families have no phase B or C.
    Capability.THREE_PHASE: frozenset({Family.RS, Family.MG, Family.K}),
}

#: What register 5002 reports. Asking beats inferring, so this outranks the
#: family table for THREE_PHASE.
OUTPUT_TYPES: dict[int, str] = {0: "single phase", 1: "3P4L", 2: "3P3L"}


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
    Capability.BATTERY_START_POWER: ("battery_charging_start_power",),
    Capability.ACTIVE_POWER_LIMIT: ("active_power_limitation_raw",),
}


def probe(read: Callable[[str], object]) -> frozenset[Capability]:
    """Return the capabilities whose registers actually answered.

    `read` returns a register's decoded value, or None where the inverter
    reported the specification's "unavailable" sentinel. A capability counts
    as present when every register it needs came back with a value: a
    two-tracker inverter answers 0xFFFF for MPPT3 forever, and that is the
    device telling us, which is better evidence than any table.
    """
    found: set[Capability] = set()
    for capability, fields in PROBES.items():
        try:
            values = [read(field) for field in fields]
        except AttributeError:
            continue
        if values and all(v is not None for v in values):
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
