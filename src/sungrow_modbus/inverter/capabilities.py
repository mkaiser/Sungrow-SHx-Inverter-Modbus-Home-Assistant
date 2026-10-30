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

The knowledge encoded here is prose in `modbus_sungrow.yaml`: comments like
"only for SH*T inverters with 3 MPPTs" and "not available on SHxRS". Prose
cannot gate an entity. Note the shape of what those comments
say — they record where a feature is **absent**, on which model, learned from
somebody's bug report. So absence is what this module models, and presence is
what probing establishes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import StrEnum

from ..battery.power import model_for_capacity
from ..const import model_for


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

    Not probed by `resolve`: it needs a second unit. `with_sungrow_battery`
    grants it once a pack has answered on its own unit **and** register 5639's
    capacity names an **SBR**. An SBH is not granted yet: every SBH surveyed
    was read through a WiNet-S, so its own-unit reading on a direct link is
    unmeasured. Granting it moves write bounds, from BMS current times voltage
    to the datasheet's conservative power (`battery.ceiling`).
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

    Over a cable the register arrives in a frame the device pads, and only the
    count in `layout.COUNTS` reads it; what cannot read it at all is a dongle.
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

    METER_PHASE_MEASUREMENTS = "meter_phase_measurements"
    """The meter's per-phase voltage and current, registers 5741-5746.

    Undocumented by Sungrow, and the YAML package's most complained-about
    registers: "pymodbus returned isError True" on every poll, for years
    (#655, #660, #678, #756). **Measured, the problem is the dongle.** All
    five houses read through a WiNet-S on 2026-09/10 refuse these registers
    read alone and answer **zero** inside a pooled block -- which is how the
    library reads them, so behind a dongle six entities would report 0 V and
    0 A forever. Every cable reading with a meter answers, on firmware 95.03,
    95.12, 95.13 and 95.14.

    That last one matters: #756 reports them refused over the LAN port of an
    SH10RT-20 on **95.14**, and bar12's SH10RT-20 on 95.14 reads 231.7 V over
    its cable. So this is *not* a firmware gate, and `ABSENT_ON_FIRMWARE`
    does not carry it.
    """

    FORCED_STARTUP = "forced_startup"
    """Forced startup from a low-SoC standby (register 13017).

    Added to the specification in V1.1.7. V1.1.16 excludes only SH50~125CX.
    """

    PV_POWER_LIMITATION = "pv_power_limitation"
    """Whether PV generation itself may be limited (register 13018).

    "Only SHT are supported", so every other family answers 0xFFFF — which is
    what the reference SH10RT does.
    """

    PV_GENERATION_CUT = "pv_generation_cut"
    """Register 31211 answers: PV generation can be cut, and its state read.

    Undocumented by Sungrow (#554, #738), and present by firmware rather than
    by model -- see `InverterPvGenerationCut`. Granted only by one of its two
    codes, 0xAA or 0x55 (`MODE_CODES_ONLY`), never by 0xFFFF or a dongle's 0.
    This is the *read*; writing it is `PV_GENERATION_CUT_CONTROL`.
    """

    PV_GENERATION_CUT_CONTROL = "pv_generation_cut_control"
    """Register 31211 may be written, because a write was confirmed here.

    Never probed: that a register answers says nothing about what writing it
    does, and this one is outside the specification. Granted by `resolve`
    only where the read capability answered **and** the firmware is in
    `CONFIRMED_ON_FIRMWARE`.
    """


class Family(StrEnum):
    """The product line a device type code belongs to."""

    RS = "RS"
    """Single-phase hybrids, SH3.0RS to SH10RS."""

    MG = "MG"
    """Three-phase MG5RL to MG12RL.

    Not the same family as `RL` even though every member's name ends in RL --
    see that entry.
    """

    RT = "RT"
    """Three-phase hybrids, SH5.0RT to SH10RT and their variants."""

    T = "T"
    """The newer three-phase line, SH5T to SH25T."""

    K = "K"
    """The withdrawn SH*K series, still in the field."""

    RL = "RL"
    """Single-phase SH3RL to SH10RL.

    Distinct from `MG` despite sharing the RL suffix and interleaving with it
    in the device type codes. The specification treats them as two groups,
    writing "MG5-12RL and SH3-10RL are not supported" wherever it excludes
    both, and they differ in the thing that matters: an MG*RL is three-phase,
    an SH*RL single-phase.
    """

    CX = "CX"
    """SH50CX to SH125CX, three-phase with ten MPP trackers.

    Added to the specification in V1.1.14 and V1.1.15. Nothing here has been
    tested against one, and the register map this project reads stops at
    MPPT4, so a CX would report a fraction of its trackers. It is named so
    that the specification's many "SH50~125CX are not supported" remarks can
    be recorded rather than lost.
    """


#: Ordered rules mapping a model name to its family, first match winning.
#:
#: **Name-based, not code-based, and deliberately so.** Sungrow does not
#: allocate codes in one block per family: in protocol V1.1.12 to V1.1.16
#: MG5RL to MG10RL occupy 0x0D27-0x0D2A, SH5RL to SH10RL follow at
#: 0x0D2B-0x0D2E, and then MG12RL and MG7.5RL appear *above* them at 0x0D2F
#: and 0x0D31. A code range wide enough to cover MG12RL would classify four
#: single-phase inverters as three-phase MG.
#:
#: A name cannot interleave. `DEVICE_TYPES` is checked against Appendix 1 by
#: [tests/test_device_types.py](../../tests/test_device_types.py), so the
#: input to these rules is pinned to the specification, and an unrecognised
#: model still returns None and is probed.
#:
#: Order matters. `MG12RL` and `SH8RL` both end in `RL`, so MG is tested
#: first; `SH5K-30` and `SH10RT-20` both contain a hyphenated suffix, so the
#: K series is matched on its closed set of codes rather than on a substring.
_FAMILY_RULES: tuple[tuple[str, Family], ...] = (
    ("CX", Family.CX),
    ("RS", Family.RS),
    ("RL", Family.RL),
    ("T", Family.T),
)

#: The SH*K codes, matched as a set because the series is closed: protocol
#: V1.1.0 dropped it in 2023 and no new member can appear.
_K_SERIES: frozenset[int] = frozenset(
    {0x0D03, 0x0D06, 0x0D07, 0x0D09, 0x0D0A, 0x0D0B, 0x0D0C}
)

#: Where a capability is known to be absent, and where that was learned.
#: These are the YAML's comments turned into data. Absence only: a family not
#: listed here is not thereby known to *have* the capability, which is what
#: probing is for.
ABSENT_IN: dict[Capability, frozenset[Family]] = {
    # "only for SH*T inverters with 3 MPPTs". Not CX, which has ten, and not
    # RL: SH8RL and SH10RL have three where SH3RL to SH6RL have two, so the
    # family is mixed and only a probe can tell them apart. The same is now
    # true of MG -- MG7.5RL and up have three -- but a probed capability
    # survives this table, so the stale entry costs an MG8RL nothing.
    Capability.MPPT3: frozenset({Family.RS, Family.MG, Family.RT, Family.K}),
    # "only for inverters with 4 MPPTs (SH8|10RS)"
    Capability.MPPT4: frozenset({Family.MG, Family.RT, Family.T, Family.K}),
    # V1.1.16 reg 13089/13090: "MG5-12RL and SH3-10RL are not supported.
    # SH50~125CX are not supported." Note RS is *not* excluded, which settles
    # a question raised by another project gating these to a different pair of
    # registers on exactly the RS models -- see
    # [cross_reference_modbus_manager.md](../../doc/cross_reference_modbus_manager.md).
    Capability.ACTIVE_POWER_LIMIT: frozenset({Family.MG, Family.RL, Family.CX}),
    # V1.1.16 regs 13250-13369: "SH3.0-10RS and MG5-12RL and SH3-10RL are not
    # supported. SH50~125CX are not supported."
    Capability.FIRMWARE_VERSIONS: frozenset(
        {Family.RS, Family.MG, Family.RL, Family.CX}
    ),
    # "not available on SHxRS as per issue #743". T joins it from a
    # measurement rather than a remark: the SH20T in
    # [#772](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/772)
    # answers **0xFFFF** at holding 33148 and 33149 -- the specification's own
    # "unavailable", declared by the inverter and not a dongle's substituted
    # zero -- where both measured RT houses return values. One machine on one
    # firmware, so it is a head start rather than a verdict: `resolve` keeps
    # anything a probe finds, so an SH5T that does answer these keeps its
    # entities regardless of this line.
    Capability.BATTERY_START_POWER: frozenset({Family.RS, Family.T}),
    # V1.1.16 regs 13200-13207: "SH3.0-10RS and MG5-12RL and SH3-10RL are not
    # supported. SH50~125CX are not supported."
    Capability.METER_CHANNEL_2: frozenset({Family.RS, Family.MG, Family.RL, Family.CX}),
    # V1.1.16 reg 13088: "MG5-12RL and SH3-10RL are not supported.
    # SH50~125CX are not supported."
    Capability.FEED_IN_LIMITATION_RATIO: frozenset({Family.MG, Family.RL, Family.CX}),
    # V1.1.10: "Only SHT are supported."
    Capability.PV_POWER_LIMITATION: frozenset(
        {Family.RS, Family.MG, Family.RL, Family.CX, Family.RT, Family.K}
    ),
    # V1.1.16 reg 13017: "SH50~125CX are not supported."
    Capability.FORCED_STARTUP: frozenset({Family.CX}),
    # Single-phase families have no phase B or C.
    #
    # **MG is deliberately not in this set.** No source says it is
    # single-phase, and this table records absence *learned from* something.
    # The only external evidence anyone has produced says the opposite: the
    # datasheet-derived model table in
    # [ha-modbus-manager](https://github.com/TCzerny/ha-modbus-manager) gives
    # `phases: 3` for MG5RL through MG12RL. Sungrow's own Appendix 1 lists
    # MPPT and strings per model but not phases, so it does not settle it.
    #
    # Behaviourally this costs nothing either way: register 5002 states the
    # output type outright and `resolve` lets it lift or impose this veto, so
    # a real MG gets the right answer from the device. What changes is the
    # claim `doc/compatibility.md` publishes for a model nobody has read, and
    # asserting single-phase there on no evidence was the weaker of the two
    # options. One MG survey settles it.
    #
    # SH*RL stays, and is why RL is a separate family from MG.
    Capability.THREE_PHASE: frozenset({Family.RS, Family.RL, Family.K}),
}

#: Where a capability is **measured** absent on one firmware, keyed by the ARM
#: version string in register 2582 (`sungrow_version_1`) -- the part a
#: firmware update changes, as opposed to the hardware strings beside it.
#:
#: The firmware twin of `ABSENT_IN`, with a stricter rule for getting in:
#: **a committed survey, not a bug report.** Issue reports name firmware
#: that is wrong as often as right -- #756 blames 95.14 for refusing the meter
#: phase registers, and bar12 reads them on 95.14 -- and a gate keyed on a
#: version string hides entities from everyone on that version. So an entry
#: names the surveys it rests on, and a version is matched **exactly**:
#: the neighbouring versions are unmeasured, not implied.
#:
#: Unlike the family table this also stops the **read**, through
#: `device.FIRMWARE_GATED_COMPONENTS`. That is the point of it: these
#: registers are not refused with an exception but answered by **closing the
#: connection**, so polling them costs a timeout and a reconnect every time --
#: enough, on the firmware below, to keep an entry from setting up at all.
ABSENT_ON_FIRMWARE: dict[str, frozenset[Capability]] = {
    # fwitten's SH10RT-V112 master and slave, both over their own LAN port,
    # 2026-09-07 and again 2026-09-25: the three firmware strings at 13250,
    # 13265 and 13280, and the second meter channel at 13200, each closed the
    # connection 3 of 3 while their neighbours answered in the same session
    # (`src/sungrow_modbus/inverter/layout.py` has the transcript). Both
    # machines identically.
    #   sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan.json
    #   sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json
    # The same model reads all four on 95.13 (gerd's SH8.0RT-V112), as do an
    # SH10RT on 95.12 and an SH10RT-20 on 95.14, so it is the firmware.
    #
    # The YAML package's reports go further -- 13250-13280 missing on 51.0x
    # (#660, #673) -- but nothing on 51.0x has been surveyed, so it stays out.
    "SAPPHIRE-H_01011.95.03": frozenset(
        {Capability.FIRMWARE_VERSIONS, Capability.METER_CHANNEL_2}
    ),
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
#: here rather than guessed at; a survey from such a system is what would
#: unblock it.
LINE_VOLTAGE_OUTPUT_TYPE = 2


def family_for(device_type_code: int | None) -> Family | None:
    """Return the product family for a device type code, if it is known.

    Resolved from the model name in `DEVICE_TYPES` rather than from the code,
    because the codes interleave -- see `_FAMILY_RULES`. A code that is not in
    that table returns None, which `known_absent` turns into "probe it".
    """
    if device_type_code is None:
        return None
    if device_type_code in _K_SERIES:
        return Family.K
    model = model_for(device_type_code)
    if model is None:
        return None
    # MG*RL before the bare RL rule, and RT before the bare T rule: both
    # suffixes are substrings of the other family's names.
    if model.startswith("MG"):
        return Family.MG
    if "RT" in model:
        return Family.RT
    for suffix, family in _FAMILY_RULES:
        if suffix in model:
            return family
    return None


def known_absent(
    device_type_code: int | None,
    firmware: str | Iterable[str | None] | None = None,
) -> frozenset[Capability]:
    """Return the capabilities this model, on this firmware, is known not to have.

    An unknown code returns nothing from the family table, which is
    deliberate: a model nobody has written down should be probed rather than
    assumed crippled. The same goes for firmware nobody has surveyed.
    """
    by_firmware = absent_on_firmware(firmware)
    family = family_for(device_type_code)
    if family is None:
        return by_firmware
    return by_firmware | frozenset(
        capability for capability, families in ABSENT_IN.items() if family in families
    )


#: Firmware on which a write is **confirmed by its effect**, per capability.
#:
#: The positive twin of `ABSENT_ON_FIRMWARE`, and it has to be a separate
#: table. Absence is something the device says by answering 0xFFFF; permission
#: to write a register Sungrow never documented is not something any read can
#: establish. So a capability here is granted from evidence about the write --
#: the control test's behavioural check, on that exact firmware -- and not from
#: the register merely answering.
#:
#: The same rules as the absence table: a version is matched **exactly**,
#: against either firmware string (`firmware_strings`), and every entry names
#: the survey whose `control_test` block carries the passing check. An
#: empty set means the entity waits; the read-only state still ships.
CONFIRMED_ON_FIRMWARE: dict[Capability, frozenset[str]] = {
    # fwitten's SH10RT-V112 master over its own LAN port, 2026-10-29: DC power
    # 1213 W before, 0 W during, 1199 W after. A trace showed the ramp: 0 W
    # 20 s after 0xAA, back 8 s after 0x55.
    #   sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json  # noqa: E501
    # gerd's SH8.0RT-V112 over its own LAN port, 2026-10-30: 2938 W before,
    # 0 W during, 1913 W after, judged by its bracket (`STOP_BRACKET_W`).
    #   sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan.json  # noqa: E501
    Capability.PV_GENERATION_CUT_CONTROL: frozenset(
        {"SAPPHIRE-H_B001.V000.P022", "SAPPHIRE-H_B001.V000.P023"}
    ),
}

#: The read a confirmed write also needs, so a firmware entry can never grant
#: control over a register this particular device does not answer.
CONTROL_REQUIRES: dict[Capability, Capability] = {
    Capability.PV_GENERATION_CUT_CONTROL: Capability.PV_GENERATION_CUT,
}


def firmware_strings(firmware: str | Iterable[str | None] | None) -> tuple[str, ...]:
    """Return the firmware strings worth matching, trimmed and non-empty.

    A device reports two that move independently: 2582
    (`SAPPHIRE-H_01011.95.14`) and 13250 (`SAPPHIRE-H_B001.V000.P023`). Their
    formats never coincide, so a table keyed by exact strings can mix both.
    """
    if firmware is None:
        return ()
    values = (firmware,) if isinstance(firmware, str) else tuple(firmware)
    return tuple(v.strip() for v in values if v and v.strip())


def absent_on_firmware(
    firmware: str | Iterable[str | None] | None,
) -> frozenset[Capability]:
    """Return what this firmware was measured not to have; see `ABSENT_ON_FIRMWARE`.

    Matched exactly after trimming, because the next version up is unmeasured.
    Either firmware string may match.
    """
    found: set[Capability] = set()
    for value in firmware_strings(firmware):
        found |= ABSENT_ON_FIRMWARE.get(value, frozenset())
    return frozenset(found)


def confirmed_on_firmware(
    firmware: str | Iterable[str | None] | None,
) -> frozenset[Capability]:
    """Return the writes confirmed on this firmware; see `CONFIRMED_ON_FIRMWARE`."""
    values = set(firmware_strings(firmware))
    return frozenset(
        capability
        for capability, versions in CONFIRMED_ON_FIRMWARE.items()
        if values & versions
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
    # Voltage alone, and only phase A: a real meter on a live grid never reads
    # 0 V, where a current of 0 A is an ordinary night.
    Capability.METER_PHASE_MEASUREMENTS: ("meter_phase_a_voltage",),
    Capability.FIRMWARE_VERSIONS: ("inverter_firmware_version",),
    Capability.SUB_CONTROLLER_FIRMWARE: ("sungrow_version_3",),
    Capability.BATTERY_FIRMWARE: ("sungrow_version_4_sungrow_battery",),
    Capability.BATTERY_START_POWER: ("battery_charging_start_power",),
    Capability.ACTIVE_POWER_LIMIT: ("active_power_limitation_raw",),
    Capability.METER_CHANNEL_2: ("meter_channel_2_total_active_power",),
    Capability.FEED_IN_LIMITATION_RATIO: ("feed_in_limitation_ratio",),
    Capability.PV_POWER_LIMITATION: ("pv_power_limitation_raw",),
    Capability.FORCED_STARTUP: ("forced_startup_under_low_soc_raw",),
    Capability.PV_GENERATION_CUT: ("pv_generation_cut_raw",),
}

#: Capabilities granted only by a Sungrow mode code, 0xAA or 0x55.
#:
#: Stricter than `ZERO_MEANS_ABSENT`, for a register outside the
#: specification: the specification's sentinel is not promised there, and a
#: dongle answers 0 where the inverter answers 0xFFFF. A mode register that
#: holds neither code is not one this integration knows how to drive.
MODE_CODES_ONLY: frozenset[Capability] = frozenset({Capability.PV_GENERATION_CUT})

#: The two codes every Sungrow mode register uses.
MODE_CODES: frozenset[int] = frozenset({0xAA, 0x55})


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
        # A third source of the same zero, and the safest of them to read as
        # absence: the grid's own voltage is not zero while it is there.
        # See the capability's docstring for the five dongle paths.
        Capability.METER_PHASE_MEASUREMENTS,
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
        if capability in MODE_CODES_ONLY and not all(v in MODE_CODES for v in values):
            continue
        found.add(capability)
    return frozenset(found)


def resolve(
    device_type_code: int | None,
    output_type: int | None = None,
    probed: frozenset[Capability] | None = None,
    firmware: str | Iterable[str | None] | None = None,
) -> frozenset[Capability]:
    """Work out what a device has, from what it said and what answered.

    Sources are applied in order of authority: what the device states about
    itself outranks what its model implies, and what actually answered a probe
    outranks both. Anything a probe found is kept even where the family table
    said it should not be there — the table is a record of bug reports, not a
    specification, and a device that answers is the better authority.

    A write in `CONFIRMED_ON_FIRMWARE` is added last, and only where the read
    it acts on is among the result: a firmware entry says the write does what
    it should, and only the device can say the register is there.
    """
    absent = known_absent(device_type_code, firmware)
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

    resolved -= absent - set(probed or frozenset())
    for capability in confirmed_on_firmware(firmware):
        if CONTROL_REQUIRES.get(capability) in resolved:
            resolved.add(capability)
    return frozenset(resolved)


def with_sungrow_battery(
    capabilities: frozenset[Capability],
    *,
    pack_found: bool,
    capacity_kwh: float | None,
) -> frozenset[Capability]:
    """Return `capabilities`, with `SUNGROW_BATTERY` where an SBR is proven.

    Two signals, both required: a pack answered on its own unit
    (`battery.probe_units`), and the inverter's capacity register names an
    SBR model. Either alone is not enough -- a capacity alone fits a
    third-party pack of the same size, and a pack alone may be an SBH, which
    is not granted until one is measured on a direct link.
    """
    if not pack_found:
        return capabilities
    model = model_for_capacity(capacity_kwh)
    if model is None or not model.name.startswith("SBR"):
        return capabilities
    return capabilities | {Capability.SUNGROW_BATTERY}
