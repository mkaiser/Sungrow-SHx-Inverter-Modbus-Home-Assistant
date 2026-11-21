"""Which registers the library will write, and how 13074 is written.

The write table, `scripts/generate/tables/writes.py`, is the one place
writability is declared; these tests hold the register map to it, keep the
danger-mode registers out of it, and pin 13074's asymmetric write scale on the
raw word, where a wrong one shows.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "scripts/generate/tables")

from writes import WRITABLE_FIELDS

from sungrow_modbus.hybrid_inverter.registers import InverterFastHolding


def test_only_declared_fields_are_writable() -> None:
    """The safety property: the library refuses everything else.

    A register the integration cannot write is a register it cannot write by
    accident, so the set of writable fields in the register map must be
    exactly this table -- no more.
    """
    from sungrow_modbus import COMPONENTS

    writable = {
        name
        for component in COMPONENTS.values()
        for name, field in component.declared_fields.items()
        if getattr(field, "writable", False)
    }
    assert writable == set(WRITABLE_FIELDS)


def test_the_dangerous_registers_are_not_writable_yet() -> None:
    """Named individually, so adding one is a deliberate act.

    These are what the YAML package guards behind its danger-mode toggle. The
    list shrinks one deliberate commit at a time: when this test fails because
    a field was made writable, that is the question being asked -- did you
    mean to?
    """
    for field in (
        # Power limiting, distinct from feed-in limiting -- and its
        # shutdown-at-zero behaviour.
        "active_power_limitation_raw",
        "active_power_limitation_ratio_raw",
        "apl_shutdown_at_zero_raw",
        # SHT-only, and the reference hardware answers 0xFFFF.
        "pv_power_limitation_raw",
        # The most dangerous register in the map. Reading it gives the running
        # state; writing 0xCF or 0xCE to it boots or shuts down the inverter,
        # which is what the YAML's start/stop buttons do. Nothing should be
        # able to write this by accident, and a `button` is the only shape
        # that cannot be nudged by a slider or a stale automation.
        "running_state_raw",
    ):
        assert field not in WRITABLE_FIELDS


def test_the_export_limit_writes_in_tens_and_reads_in_ones() -> None:
    """Register 13074 is the one place the two directions disagree.

    It reads in watts -- 10000 back against a 10000 W maximum from register
    5623, which is the read side agreeing with its own bounds -- and writes in
    tens of watts, multiplying the word it is handed by ten before storing it.
    Measured six times on the reference SH10RT with feed-in limitation on,
    including values no rounding could produce, and replicated at a second
    house on an SH10RT-20 through a dongle.

    Every other register in the map shares one scale between `encode` and
    `decode`, so the obvious tidy-up is to make this one an `integer()` like
    its neighbours. That tidy-up sets ten times what the user asked for, and
    it is invisible to a readback through the library because `encode` and
    `decode` would agree with each other while both disagreed with the device.
    So the assertion is deliberately about the **raw word**, which is the only
    place the difference shows.
    """
    field = InverterFastHolding.__dict__["export_power_limit"]

    # The write side: what actually goes on the wire for a value a user types.
    assert field.encode(900) == [90]
    assert field.encode(10000) == [1000]
    assert field.encode(0) == [0]

    # The read side is untouched, and must stay so: the register contains watts.
    assert field.decode([900]) == 900
    assert field.decode([10000]) == 10000

    # Stated as the round trip through a device that behaves as measured.
    for watts in (100, 900, 3400, 10000):
        (word,) = field.encode(watts)
        assert field.decode([word * 10]) == watts
