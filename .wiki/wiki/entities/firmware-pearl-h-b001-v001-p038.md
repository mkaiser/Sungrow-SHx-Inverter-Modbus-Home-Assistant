---
type: entity
title: PEARL-H_B001.V001.P038
tags: [firmware, pearl-h-b001-v001-p038]
created: '2026-11-09'
---

# PEARL-H_B001.V001.P038

[SH-T](device-sh-t.md) firmware in the B001 numbering, read on an SH10T at
[BiergitKraft](installation-biergitkraft.md), only through a [WiNet-S](device-winet-s.md)2
(`WINET-SV300.001.03.P031`). Version 1 / 2 `PEARL-H_01011.01.42` / `PEARL-H_03011.01.42`; ARM
and DSP `*_PEARL-H_V11_V01_A`. One reading ([the diagnosis](../sources/sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan-summary.md)).

- [Register 31211](register-31211.md) answers 0x55, as on P067 and P071. The PV cut has not been
  written on this firmware, so it is not in `CONFIRMED_ON_FIRMWARE`.
- **33149-33150 (battery start power) answered** in every round of the block read test, through
  the dongle. The capability table marks them absent on the SH-T; see the contradiction on
  [P071](firmware-pearl-h-b000-v000-p071.md). A cable reading decides.
- [Register 13074](register-13074.md)'s write scale: not probed (no capability test ran). The B001
  in the name is not evidence of the SH-RT's B001 behaviour; the T's numbering is its own.
- 13018 (PV power limitation) answers, 0x55.

## Diagnoses

- [SH10T, B001.V001.P038, BiergitKraft, a WiNet-S2 on Ethernet, SBH100](../sources/sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan-summary.md)
