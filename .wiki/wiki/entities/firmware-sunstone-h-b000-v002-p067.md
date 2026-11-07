---
type: entity
title: SUNSTONE-H_B000.V002.P067
tags: [firmware, sunstone-h-b000-v002-p067]
created: '2026-11-05'
---

# SUNSTONE-H_B000.V002.P067

[SH-RS](device-sh-rs.md) firmware; version 1 reads `SUNSTONE-H_01011.02.67`, version 2
`SUNSTONE-H_03021.01.15`. Only read through a [WiNet-S](device-winet-s.md).

- [Register 31211](register-31211.md) answers 0x55; the PV cut is not confirmed here, so the
  switch waits (`CONFIRMED_ON_FIRMWARE` holds [P065](firmware-sunstone-h-b000-v002-p065.md), not
  this one).
- Writes are unmeasured: the one capability test was refused because the inverter was key-stopped.
- The battery firmware string (13280) carries bytes after its NUL, as on
  [P065](firmware-sunstone-h-b000-v002-p065.md).

## Diagnoses

- [SH10RS, B000.V002.P067, brendan, a WiNet-S on Ethernet, capability test refused](../sources/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md)
