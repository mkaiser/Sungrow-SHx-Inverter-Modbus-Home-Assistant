---
type: entity
title: SH-RS hybrid inverters
tags: [inverter, sh-rs, sunstone-h, single-phase]
created: '2026-10-31'
---

# SH-RS hybrid inverters

The single-phase hybrids, SH3.0RS to SH10RS, on firmware family `SUNSTONE-H`. One survey in the
corpus: an [SH6.0RS](../sources/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md)
on [`SUNSTONE-H_B000.V001.P068`](firmware-sunstone-h-b000-v001-p068.md), through a
[WiNet-S](device-winet-s.md), with an [SBR192](device-sbr-battery.md).

## What is established

- **Only read through a WiNet-S**, so nothing here separates the machine from the dongle.
- [31211](register-31211.md) answers 0x55; the forced-charging schedule and the discharge
  schedules answer with the SH-RT's layout.
- Version 1 reads `SUNSTONE-H_01011.03.68`: its own series, like the T's `PEARL-H_01011.01.45`
  (see [SH-T](device-sh-t.md)), never compared numerically with SH-RT's `.95.xx`.
- No control test yet: nothing about writes on this family is measured.
