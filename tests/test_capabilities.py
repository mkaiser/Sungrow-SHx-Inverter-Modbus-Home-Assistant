"""What a device exposes, resolved from model, register and probe.

The reference fingerprint is the anchor: an SH10RT that reports three phases,
answers MPPT1 and MPPT2, returns 0xFFFF for MPPT3 and MPPT4, has a meter
directly wired and a third-party battery. If the model says one thing and that
machine says another, the machine wins.
"""

from __future__ import annotations

import pytest

from sungrow_modbus.capabilities import (
    Capability,
    Family,
    family_for,
    known_absent,
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
    ],
)
def test_families_are_recognised(code: int, family: Family) -> None:
    assert family_for(code) is family


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
