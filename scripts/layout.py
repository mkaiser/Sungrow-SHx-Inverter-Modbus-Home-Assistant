"""Registers that must be read on their own, and why.

The library pools neighbouring registers into single block reads, which is
what makes a full poll 23 reads instead of 105. The cost is that one register
the device cannot answer takes its whole block with it — and a `Component`
either updates or raises, so a bad block loses every field in the component.

That is normally the right trade. `UpdateReport` reports failures per
component precisely so a device that answers a different subset of the map is
ordinary rather than broken. It stops being the right trade when the
component is large and one of its registers is absent on real hardware.

There are two ways a device refuses, and this module handles both. One is a
reply of the wrong length, below. The other is cruder: **the inverter closes
the TCP connection** rather than returning an exception code, which
`modbus-connection` surfaces as `ModbusConnectionError` and which looks
exactly like being dropped by a competing Modbus session. Telling them apart
takes repetition -- a register fault fails every attempt while its neighbours
succeed in the same session -- and the entries below say which was measured.

**Measured on the reference SH10RT (2026-09-07, cause corrected 2026-09-08),
firmware ARM SAPPHIRE-H_V11_V01_B.** The two firmware strings at 2612 and
2628 come back in a frame the device **pads to fifteen registers while
declaring the correct byte count**. Captured off the wire, asking for 11:

    -> 00 01 00 00 00 06 01 04 0a 34 00 0b      address 2612, count 11
    <- 00 01 00 00 00 21 01 04 16 53 55 42 ...  39 bytes

`mbap_len = 0x21 = 33` describes 30 data bytes, so the frame is sized for
fifteen registers. `byte_count = 0x16 = 22` says eleven -- which is what was
asked for, and the first 22 bytes hold it correctly; the rest is zero
padding. The two numbers disagree, `modbus-connection` validates against the
MBAP length, and the whole answer is rejected.

Asking for exactly 15 is what makes the frame self-consistent, which is why
`COUNTS` works and why it is a workaround rather than a correction: the data
was never wrong and the count was never wrong either. A lenient client that
trusts the byte count reads these registers perfectly well, which is exactly
how the first diagnosis went astray -- a raw-socket probe called them fine
while the shipping stack could not read them at all.
`scripts/sungrow_scan/blocks.py` is deliberately as strict as the shipping
stack for that reason, and reports both numbers plus the count that
reconciles them.

Two consequences, and this module fixes both.

`COUNTS` corrects the length. Pooled into `slowest_input`, these two fields
made its one 58-register read fail every time, so **all 36 other slowest-tier
entities were permanently empty** — on the maintainer's own inverter.

`ISOLATE` keeps them out of that pool. The corrected length is only correct
for a request that covers exactly one of these fields, so they can never
share a read: 15 registers at 2612 and 15 at 2628 would otherwise pool into
one 31-register request and fail again.

The YAML package never hit the second part because it reads every register in
its own request; it hits the first, and its Sungrow Version 3 is unavailable
on this inverter for the same reason. Block pooling is strictly better for
the wire and strictly worse for blast radius, and this is where the balance
has to be corrected by hand.
"""

from __future__ import annotations

#: Field name to the component it is moved into, away from its tier's main
#: component. Anything here is read in its own request group, so its absence
#: costs only itself.
#:
#: Add to this when hardware proves a register unreadable — not when a
#: document hints it might be, and not when a lenient client says it is fine.
#: `scripts/sungrow_scan/blocks.py` is the measurement, because it fails
#: wherever the shipping stack fails. Every entry should name the machine that
#: proved it.
#:
#: Two shapes of evidence are **not** enough on their own, both learned here:
#:
#: * a range the block read test marked `not narrowed`, which means its
#:   narrowing budget ran out rather than that the range is minimal — the
#:   register named would be a guess out of up to fifteen;
#: * a read that only ever *timed out*, with no exception code and no closed
#:   connection. Every entry below is one of those two: an exception 0x02, a
#:   deterministic hangup, or a padded frame. A bare timeout cannot tell a
#:   silent inverter from a lost answer, and the same four blocks that timed
#:   out over a VPN on 2026-09-09 had closed the connection deterministically
#:   on a LAN two days earlier — same machines, different sentence. Re-measure
#:   from a link that fails fast before adding anything.
ISOLATE: dict[str, str] = {
    # Frame padded to 15 registers on SH10RT firmware ARM_SAPPHIRE-H_V11_V01_B,
    # so anything but a 15-register request is rejected. Not absent: the data
    # is there, and a client that trusts the byte count reads it.
    # One group each rather than one group for both, because they describe
    # different pieces of hardware. Pooled together, an inverter that has a
    # Sungrow battery but no sub-controller string would lose the battery
    # version to its neighbour's silence — the same bug one level down.
    "sungrow_version_3": "sub_controller_firmware",
    "sungrow_version_4_sungrow_battery": "battery_firmware",
    # Measured on fwitten's SH10RT-V112 pair (0x0E0F, ARM
    # SAPPHIRE-H_V11_V01_B, 2026-09-07), both machines identically. These four
    # blocks do not return an exception code -- the inverter **closes the TCP
    # connection**. Deterministically: 3 of 3 attempts each, while their
    # immediate neighbours answered 3 of 3 in the same session.
    #
    # The three firmware strings are adjacent at 15 registers apiece, so they
    # pooled into one 45-register read and took `slowest_input` with them --
    # all 36 of its fields. One group each rather than one for the three,
    # because they are adjacent: any two in a group would pool back into a
    # single read and fail together again.
    "inverter_firmware_version": "firmware_block_inverter",
    "communication_module_firmware_version": "firmware_block_communication_module",
    "battery_firmware_version": "firmware_block_battery",
    # And these four killed `fast_input`, all 41 fields of it, on a house
    # whose 5.0-second tier is the one people actually watch. They are one
    # group because they are one optional device: a second meter either
    # answers or it does not.
    "meter_channel_2_total_active_power": "meter_channel_2",
    "meter_channel_2_phase_a_active_power": "meter_channel_2",
    "meter_channel_2_phase_b_active_power": "meter_channel_2",
    "meter_channel_2_phase_c_active_power": "meter_channel_2",
    # Measured on gerd's SH8.0RT-V112 (0x0E0E, ARM SAPPHIRE-H_V11_V01_B,
    # 2026-09-07) with the block read test -- then `discover_probe.py
    # components`, now `scripts/sungrow_scan/blocks.py`: each of these
    # refused on **every** round while its neighbours answered, and each was
    # the only unanswerable read in a component that then lost every field it
    # had. One field apiece, so isolating them costs one extra read and saves
    # 41 and 12 fields respectively.
    #
    # Both answer on the same inverter through its WiNet-S, and on every other
    # machine measured, so this is the inverter's own LAN port on this
    # firmware refusing them rather than the registers being absent.
    "battery_power": "battery_power",
    "apl_shutdown_at_zero_raw": "apl_shutdown_at_zero",
}

#: Field name to the register count that actually reads, where the YAML's
#: count does not. Only ever set from a measurement against real hardware --
#: the module docstring has the transcript for these two.
#:
#: Safe on firmware that behaves: the extra registers a longer read collects
#: are the nulls after the string, and the decoder stops at the first one.
COUNTS: dict[str, int] = {
    "sungrow_version_3": 15,
    "sungrow_version_4_sungrow_battery": 15,
}

#: One sentence per group, used verbatim as the generated class docstring.
GROUP_DESCRIPTIONS: dict[str, str] = {
    "sub_controller_firmware": (
        "The sub-controller firmware string, which some firmware versions do "
        "not publish at all."
    ),
    "battery_firmware": (
        "The battery firmware string, which the YAML package documents as "
        "being for Sungrow batteries only."
    ),
    "firmware_block_inverter": (
        "The inverter firmware string at register 13250, which some firmware "
        "answers by closing the connection."
    ),
    "firmware_block_communication_module": (
        "The communication module's firmware string at register 13265, absent "
        "on a direct LAN connection and read on its own because some firmware "
        "answers it by closing the connection."
    ),
    "firmware_block_battery": (
        "The battery firmware string at register 13280, which some firmware "
        "answers by closing the connection."
    ),
    "meter_channel_2": (
        "A second metering channel, which most installations do not have and "
        "some firmware answers by closing the connection."
    ),
    "battery_power": (
        "Battery power at register 5214, which one measured firmware refuses "
        "on the inverter's own LAN port while serving it through a WiNet-S."
    ),
    "apl_shutdown_at_zero": (
        "The active-power-limit shutdown flag at register 31213, refused by "
        "one measured firmware on the inverter's own LAN port. "
        "**Experimental and unverified:** this register is not in Sungrow's "
        "protocol document -- the comment that added it to the YAML package "
        "says so outright -- and it comes from community feedback in issue "
        "#554, a request for ramping PV production down. What it does is "
        "inferred from its name, whether the inverter shuts down when the "
        "active power limit is set to zero or idles at zero output, and "
        "nobody here has tested it. All three surveyed inverters read 85 "
        "(0x55), one value three times, so its 0xAA/0x55 pair is a "
        "convention assumed rather than observed -- which is why it stays a "
        "number instead of becoming a binary sensor like the two documented "
        "mode registers beside it."
    ),
}


def component_for(field: str, tier: str, space: str) -> str:
    """Return the component attribute a field belongs to."""
    return ISOLATE.get(field, f"{tier}_{space}")
