---
type: entity
title: SH-T hybrid inverters
tags: [inverter, sh-t, pearl-h, three-phase]
created: '2026-10-29'
---

# SH-T hybrid inverters

The larger three-phase hybrids: SH15T and SH20T in this corpus, on firmware
family `PEARL-H`, here always [`PEARL-H_B000.V000.P071`](firmware-pearl-h-b000-v000-p071.md).
They pair with the [SBH](device-sbh-battery.md) high-voltage battery.

## What is established

- **Only read through a WiNet-S.** No T-series survey was taken at an
  inverter's own LAN port, so nothing here separates the machine from the
  [dongle](device-winet-s.md).
- **31211 answers 0x55** on P071, as on SH-RT P022/P023; see
  [register 31211](register-31211.md). The T also has 13018, and whether both
  registers act is unmeasured.
- **No control test** has run on a T. Everything about writes on this family
  is carried over from SH-RT, not measured.

## Surveys

[fullhd23](installation-fullhd23.md), [jm493](installation-jm493.md) and
[ra1k-0](installation-ra1k-0.md), all through a WiNet-S.
