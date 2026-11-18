---
type: entity
title: SUNSTONE-H_B000.V002.P067
tags: [firmware, sunstone-h-b000-v002-p067]
created: '2026-11-05'
updated: '2026-11-18'
---

# SUNSTONE-H_B000.V002.P067

[SH-RS](device-sh-rs.md) firmware, read on two machines through a [WiNet-S](device-winet-s.md)
only.

**The versions beside it move while the string does not.** The first reading, 2026-11-05, had
version 1 `SUNSTONE-H_01011.02.67` and version 2 `SUNSTONE-H_03021.01.15`; the second, 2026-11-17,
has **`SUNSTONE-H_01011.02.69`** and **`SUNSTONE-H_03021.01.16`** under the same
`SUNSTONE-H_B000.V002.P067`. So this string is not enough to say what an SH-RS is running, and an
update can arrive with nothing in 13250 to show for it
([firmware gating](../concepts/firmware-gating.md) keys its tables on version 1 for that reason).

- [Register 31211](register-31211.md) answers 0x55; the PV cut is not confirmed here, so the
  switch waits (`CONFIRMED_ON_FIRMWARE` holds [P065](firmware-sunstone-h-b000-v002-p065.md), not
  this one).
- Writes are unmeasured: the one capability test was refused because the inverter was key-stopped.
- The battery firmware string (13280) carries bytes after its NUL, as on
  [P065](firmware-sunstone-h-b000-v002-p065.md).

## Diagnoses

- [SH10RS, B000.V002.P067, brendan, a WiNet-S on Ethernet, capability test refused](../sources/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md)
- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, read only](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
