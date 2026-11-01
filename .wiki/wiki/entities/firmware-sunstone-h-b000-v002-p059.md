---
type: entity
title: SUNSTONE-H_B000.V002.P059
tags: [firmware, sunstone-h-b000-v002-p059]
created: '2026-11-01'
---

# SUNSTONE-H_B000.V002.P059

[SH-RS](device-sh-rs.md) firmware; version 1 reads `SUNSTONE-H_01011.02.61`. Only read through a
[WiNet-S](device-winet-s.md).

- [Register 31211](register-31211.md) answers 0x55; the PV cut is not confirmed here, so the
  switch waits (`CONFIRMED_ON_FIRMWARE` holds [P065](firmware-sunstone-h-b000-v002-p065.md), not
  this one).
- Writes are unmeasured: no control test on this firmware.

## Surveys

- [SH10RS, B000.V002.P059, anonymous, a WiNet-S on Ethernet](../sources/sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan-summary.md)
