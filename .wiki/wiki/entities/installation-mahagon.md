---
type: entity
title: Installation mahagon
tags: [installation, mahagon]
created: '2026-11-04'
---

# Installation mahagon

An [SH5.0RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md), version 1
`SAPPHIRE-H_01011.95.14`, with a three-module [SBR096](device-sbr-battery.md), read from Home
Assistant on 2026-11-04 over the inverter's own LAN port and, minutes later, through its
WiNet-S2 (P038) on WiFi, issue #786. Both read only: the owner skipped the capability test. The
owner's YAML package was polling the LAN port during both runs.

## Diagnoses

- [SH5.0RT-V112, B001.V000.P023, mahagon, the inverter's own LAN port](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md)
- [SH5.0RT-V112, B001.V000.P023, mahagon, a WiNet-S2 on WiFi](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-winet-wlan-summary.md)

## What it shows

- The first SH5.0RT-V112, and the first 5 kW inverter on `.95.14`: [register 13074](register-13074.md)
  multiplies a written word (the probe was refused three times), but a refusal cannot tell ten
  from 0.1 % of the rating. See [the export-scale source](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md).
- [31211](register-31211.md) reads 0x55; the PV cut is not yet watched on this size.
- A dongle again hides the history blocks, the meter phases and the firmware blocks that the
  cable answers.
