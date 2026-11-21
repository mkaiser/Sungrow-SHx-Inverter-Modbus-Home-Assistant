---
type: concept
title: Padded frames
tags: [modbus, layout, block-read]
created: '2026-10-29'
---

# Padded frames

At input **2612** and **2628**, the inverter sends a frame sized for **15
registers while declaring the correct byte count**, and `modbus-connection`
rejects it. Asking for exactly 15 makes the two agree (`layout.COUNTS`), and
`layout.ISOLATE` keeps each in a read of its own, or the failure takes the
whole pooled block with it (`src/sungrow_modbus/hybrid_inverter/layout.py`).

**A lenient client says the register is fine.** A raw socket trusts
`byte_count` and reads the padded frames perfectly, while the shipping stack
cannot. `device-diagnosis/scripts/python/blocks.py` is as strict as the
shipping stack. It reports both numbers and the count that reconciles them.
Add to `layout.py` only from *its* measurement.

Do not confuse this with a [WiNet-S](../entities/device-winet-s.md), which
does not forward 2612 or 2628 at all. That is
[transport](transport-detection.md), not layout.

**The SBR at unit 200 sends two mismatched frames past its cell block**, read with a raw socket over an
SH10RT's own LAN port on P023: a read at protocol address 10750 for 41 words came back with an MBAP length two bytes longer
than its correct byte count and one extra word, and protocol address 10791 alone came back declaring two bytes and
carrying none ([the owner's frames](../sources/pvsonnenfreund-sbr096-cell-registers-788-summary.md)).
The library's SBR reads end at protocol address 10787, short of both, and the 16 committed cable SBR readings
read that block cleanly; a raw socket is the lenient client above, so this is a lead for `blocks.py`,
not a change to the layout.
