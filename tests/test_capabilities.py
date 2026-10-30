"""What a device exposes, resolved from model, register and probe.

The reference survey is the anchor: an SH10RT that reports three phases,
answers MPPT1 and MPPT2, returns 0xFFFF for MPPT3 and MPPT4, has a meter
directly wired and a third-party battery. If the model says one thing and that
machine says another, the machine wins.
"""

from __future__ import annotations

import pytest

from sungrow_modbus.const import DEVICE_TYPES
from sungrow_modbus.inverter import registers
from sungrow_modbus.inverter.capabilities import (
    ABSENT_ON_FIRMWARE,
    ZERO_MEANS_ABSENT,
    Capability,
    Family,
    family_for,
    known_absent,
    probe,
    resolve,
)

SH10RT = 0x0E03
SH10RS = 0x0D1B
MG5RL = 0x0D27
SH15T = 0x0E25
SH5K_30 = 0x0D0C


@pytest.mark.parametrize(
    ("code", "family"),
    [
        (SH10RT, Family.RT),
        (SH10RS, Family.RS),
        (MG5RL, Family.MG),
        (SH15T, Family.T),
        (SH5K_30, Family.K),
        (0x0E0F, Family.RT),  # SH10RT-V112, a variant inside the RT block
        (0x0D2A, Family.MG),  # MG10RL, added to the specification in V1.1.11
        # The interleaved 0x0D2x block, which is the whole reason family is
        # resolved from the model name and not from a code range. MG runs to
        # 0x0D2A, SH*RL takes 0x0D2B-0x0D2E, and MG resumes above it.
        (0x0D2B, Family.RL),  # SH5RL, immediately after MG10RL
        (0x0D2E, Family.RL),  # SH10RL, immediately before MG12RL
        (0x0D2F, Family.MG),  # MG12RL, above the SH*RL block
        (0x0D31, Family.MG),  # MG7.5RL, higher still
        (0x0D41, Family.RL),  # SH3RL, a second SH*RL block
        (0x0E51, Family.CX),  # SH50CX
        (0x0E3D, Family.CX),  # SH125CX
    ],
)
def test_families_are_recognised(code: int, family: Family) -> None:
    assert family_for(code) is family


def test_every_model_in_the_table_has_a_family() -> None:
    """No model may fall through the rules unclassified.

    This is the test the code-range classifier did not have. Nine models
    arrived between V1.1.12 and V1.1.16 outside every range it knew, and
    nothing failed -- they simply resolved to None and lost their capability
    gating silently.
    """
    unclassified = {
        f"0x{code:04X}": name
        for code, name in DEVICE_TYPES.items()
        if family_for(code) is None
    }
    assert not unclassified, f"models with no family: {unclassified}"


def test_no_single_phase_model_is_classified_three_phase() -> None:
    """The specific wrong answer a widened MG range would have given.

    SH5RL to SH10RL sit between MG10RL and MG12RL in the code space. Reaching
    MG12RL by extending the MG range would have swept them up, and MG is
    three-phase while SH*RL is not -- so four single-phase inverters would
    have been told they had a phase B and a phase C.
    """
    for code in (0x0D2B, 0x0D2C, 0x0D2D, 0x0D2E, 0x0D41, 0x0D42, 0x0D43):
        assert Capability.THREE_PHASE in known_absent(code), (
            f"0x{code:04X} ({DEVICE_TYPES[code]}) is single-phase"
        )
    # And the MG models around them keep their three phases.
    for code in (0x0D2A, 0x0D2F, 0x0D31):
        assert Capability.THREE_PHASE not in known_absent(code), (
            f"0x{code:04X} ({DEVICE_TYPES[code]}) is three-phase"
        )


def test_the_specifications_model_exclusions_are_recorded() -> None:
    """The remarks column of V1.1.16, which is where these facts live.

    Register 13089/13090 excludes "MG5-12RL and SH3-10RL" and "SH50~125CX" --
    and notably *not* the RS models, which another project gates to a
    different register pair on exactly those models.
    """
    for code in (0x0D31, 0x0D2D, 0x0E51):  # MG7.5RL, SH8RL, SH50CX
        assert Capability.ACTIVE_POWER_LIMIT in known_absent(code)
    for code in (0x0D1B, 0x0E03):  # SH10RS, SH10RT
        assert Capability.ACTIVE_POWER_LIMIT not in known_absent(code)
    # Reg 13017 excludes only the CX series.
    assert Capability.FORCED_STARTUP in known_absent(0x0E51)
    assert Capability.FORCED_STARTUP not in known_absent(0x0E03)


def test_an_unknown_code_has_no_family_and_no_assumptions() -> None:
    # A model nobody has written down should be probed, not assumed crippled.
    assert family_for(0xBEEF) is None
    assert known_absent(0xBEEF) == frozenset()
    assert known_absent(None) == frozenset()


def test_the_yaml_comments_became_gates() -> None:
    # "only for SH*T inverters with 3 MPPTs"
    assert Capability.MPPT3 in known_absent(SH10RT)
    assert Capability.MPPT3 not in known_absent(SH15T)
    # "only for inverters with 4 MPPTs (SH8|10RS)"
    assert Capability.MPPT4 not in known_absent(SH10RS)
    assert Capability.MPPT4 in known_absent(SH10RT)
    # "MG5-6RL is not supported."
    assert Capability.ACTIVE_POWER_LIMIT in known_absent(MG5RL)
    # "not available on SHxRS as per issue #743"
    assert Capability.BATTERY_START_POWER in known_absent(SH10RS)
    # "NOTE: SH3.0-10RS and MG5-6RL are NOT supported"
    assert Capability.FIRMWARE_VERSIONS in known_absent(SH10RS)
    assert Capability.FIRMWARE_VERSIONS in known_absent(MG5RL)
    assert Capability.FIRMWARE_VERSIONS not in known_absent(SH10RT)


def test_register_5002_outranks_the_model_for_phases() -> None:
    # An RS is single-phase by family, and 5002 agreeing changes nothing.
    assert Capability.THREE_PHASE not in resolve(SH10RS, output_type=0)
    # But if one ever reported 3P4L, believe the register.
    assert Capability.THREE_PHASE in resolve(SH10RS, output_type=1)
    # And an RT reporting single phase is taken at its word.
    assert Capability.THREE_PHASE not in resolve(SH10RT, output_type=0)


def test_a_probe_outranks_the_family_table() -> None:
    # The table is a record of bug reports, not a specification. A device that
    # actually answers is the better authority.
    assert Capability.MPPT3 in resolve(SH10RT, probed=frozenset({Capability.MPPT3}))


def test_the_reference_inverter_resolves_as_measured() -> None:
    # Read from the maintainer's SH10RT: three phase, two MPPTs, meter wired
    # directly, a battery present but a Pylontech rather than an SBR.
    probed = frozenset(
        {Capability.METER_DIRECT, Capability.BATTERY, Capability.FIRMWARE_VERSIONS}
    )
    resolved = resolve(SH10RT, output_type=1, probed=probed)

    assert Capability.THREE_PHASE in resolved
    assert Capability.METER_DIRECT in resolved
    assert Capability.BATTERY in resolved
    assert Capability.FIRMWARE_VERSIONS in resolved
    assert Capability.MPPT3 not in resolved
    assert Capability.MPPT4 not in resolved
    assert Capability.SUNGROW_BATTERY not in resolved


def _reads(values: dict[str, object]):
    """Return a `read` for `probe`, raising for a field the library lacks."""

    def read(field: str) -> object:
        if field not in values:
            raise AttributeError(field)
        return values[field]

    return read


def test_a_battery_that_answers_is_probed_as_present() -> None:
    probed = probe(_reads({"battery_voltage": 199.2, "battery_level": 100.0}))
    assert Capability.BATTERY in probed


def test_a_cluster_slave_reporting_all_zeros_has_no_battery() -> None:
    # Measured on a real master/slave pair of SH10RT-V112: the battery is
    # wired to the master, and the slave answers 0 for voltage, level,
    # temperature and capacity alike rather than the specification's 0xFFFF.
    # Zero decodes to a value, so this used to grant BATTERY and create the
    # whole 13xxx block as entities reporting zero forever.
    probed = probe(_reads({"battery_voltage": 0.0, "battery_level": 0.0}))
    assert Capability.BATTERY not in probed


def test_a_flat_battery_is_still_a_battery() -> None:
    # Level 0 is a reading, not an absence: a pack discharged to its floor
    # still reports its voltage. Only the whole block being zero is absence,
    # which is why level alone must never decide it.
    probed = probe(_reads({"battery_voltage": 180.4, "battery_level": 0.0}))
    assert Capability.BATTERY in probed


def test_the_unavailable_sentinel_is_still_how_a_lone_inverter_says_no() -> None:
    # The pre-existing path, unchanged: None is what the library decodes
    # 0xFFFF to, and an inverter fitted without storage answers that.
    probed = probe(_reads({"battery_voltage": None, "battery_level": None}))
    assert Capability.BATTERY not in probed


def test_a_slave_answering_zero_volts_beside_the_sentinel_has_no_battery() -> None:
    # fwitten's battery-less slave on SAPPHIRE-H_B001.V000.P023: voltage 0,
    # level 0xFFFF. Decoded through the real field, because the bug was the
    # field: without its sentinel 0xFFFF read 6553.5 % and granted BATTERY.
    level = registers.InverterMediumInput.battery_level
    assert level.decode([0xFFFF]) is None
    assert level.decode([1000]) == 100.0
    values = {"battery_voltage": 0.0, "battery_level": level.decode([0xFFFF])}
    assert Capability.BATTERY not in probe(_reads(values))


def test_zero_is_read_as_absence_only_where_it_was_measured_to_mean_that() -> None:
    # The rule is still confined to ZERO_MEANS_ABSENT rather than applied to
    # every probe -- three-phase output, the firmware strings and the power
    # limits all legitimately read zero.
    probed = probe(_reads({"phase_b_voltage": 0.0, "phase_c_voltage": 0.0}))
    assert Capability.THREE_PHASE in probed
    assert Capability.THREE_PHASE not in ZERO_MEANS_ABSENT


def test_a_dongles_zeros_do_not_invent_trackers_or_a_second_meter() -> None:
    """Measured on one inverter read both ways, 2026-09-08.

    On its own LAN port MPPT3, MPPT4 and the second meter channel answered
    0xFFFF -- correctly absent. Through its WiNet-S the same registers
    answered 0, which granted all three and created ten entities reporting
    zero forever. Most users are behind a dongle, so this is the common case
    rather than the exotic one.
    """
    probed = probe(
        _reads(
            {
                "mppt3_voltage": 0.0,
                "mppt3_current": 0.0,
                "mppt4_voltage": 0.0,
                "mppt4_current": 0.0,
                "meter_channel_2_total_active_power": 0,
            }
        )
    )

    assert Capability.MPPT3 not in probed
    assert Capability.MPPT4 not in probed
    assert Capability.METER_CHANNEL_2 not in probed


def test_a_tracker_at_zero_volts_is_denied_and_then_granted_at_sunrise() -> None:
    """The cost of the rule, and why it is affordable.

    A real third tracker reads 0 V at night, so an inverter set up after dark
    is denied MPPT3 -- which would be unacceptable if it were permanent. It is
    not: capabilities are re-probed after every poll and the entry reloads when
    they **grow**, so the first non-zero reading creates the entities.

    Granting on zero has no matching recovery. Nothing ever removes an entity,
    so a wrongly created one is permanent and manual to clean up, which is the
    asymmetry that decides this.
    """
    night = probe(_reads({"mppt3_voltage": 0.0, "mppt3_current": 0.0}))
    assert Capability.MPPT3 not in night

    morning = probe(_reads({"mppt3_voltage": 412.5, "mppt3_current": 3.1}))
    assert Capability.MPPT3 in morning
    # Growth is what the coordinator reloads on.
    assert morning - night == {Capability.MPPT3}


def test_the_meter_phase_registers_read_zero_through_a_dongle() -> None:
    """Every WiNet-S path in the committed surveys, five houses.

    Read alone, 5741 and 5744 are refused; inside the pooled block the library
    actually reads, they answer zero -- six entities at 0 V and 0 A forever.
    A meter on a live grid does not read 0 V, so zero is safe to deny on.
    """
    dongle = probe(_reads({"meter_phase_a_voltage": 0.0}))
    cable = probe(_reads({"meter_phase_a_voltage": 231.7}))

    assert Capability.METER_PHASE_MEASUREMENTS not in dongle
    assert Capability.METER_PHASE_MEASUREMENTS in cable


def test_firmware_absence_is_an_exact_measured_version() -> None:
    """Keyed exactly: 95.13 is not 95.03, and unsurveyed firmware is not gated.

    #756 blames 95.14 for the meter phase registers, and bar12 reads them on
    95.14 -- the reason a bug report alone does not make an entry.
    """
    gated = known_absent(SH10RT, "SAPPHIRE-H_01011.95.03")
    assert {Capability.FIRMWARE_VERSIONS, Capability.METER_CHANNEL_2} <= gated
    assert Capability.FIRMWARE_VERSIONS not in known_absent(
        SH10RT, "SAPPHIRE-H_01011.95.13"
    )
    assert known_absent(None, None) == frozenset()
    assert Capability.METER_PHASE_MEASUREMENTS not in {
        c for caps in ABSENT_ON_FIRMWARE.values() for c in caps
    }


def test_every_firmware_entry_names_a_committed_document() -> None:
    """The rule for getting into the table, enforced: evidence, not a report."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent
        / "src/sungrow_modbus/inverter/capabilities.py"
    ).read_text(encoding="utf-8")
    surveys = Path(__file__).resolve().parent.parent / "device-survey" / "results"
    block = source.split("ABSENT_ON_FIRMWARE: dict", 1)[1].split("\n}\n", 1)[0]
    for version in ABSENT_ON_FIRMWARE:
        cited = [
            line.strip().lstrip("#").strip()
            for line in block.splitlines()
            if line.strip().startswith("#") and line.strip().endswith(".json")
        ]
        assert cited, f"{version} cites no survey"
        for name in cited:
            assert any(
                (surveys / directory / name).exists()
                for directory in ("inverter", "wallbox")
            ), name
            path = next(
                surveys / directory / name
                for directory in ("inverter", "wallbox")
                if (surveys / directory / name).exists()
            )
            assert version in path.read_text(encoding="utf-8"), name


@pytest.mark.parametrize(
    ("pack_found", "capacity", "granted"),
    [
        (True, 9.6, True),  # SBR096 on its own unit
        (True, 16.0, True),  # SBR160
        (True, 40.55, False),  # SBH400: not until one is read on a direct link
        (False, 9.6, False),  # an SBR's size, but no pack answered: third party
        (True, None, False),  # a pack, but 5639 did not read
        (True, 7.1, False),  # a pack whose capacity names no model
    ],
)
def test_sungrow_battery_is_granted_for_an_sbr_on_its_own_unit(
    pack_found, capacity, granted
) -> None:
    from sungrow_modbus.inverter.capabilities import with_sungrow_battery

    base = frozenset({Capability.BATTERY})
    result = with_sungrow_battery(base, pack_found=pack_found, capacity_kwh=capacity)

    assert (Capability.SUNGROW_BATTERY in result) is granted
    assert base <= result
