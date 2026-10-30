---
type: entity
title: Installation peter-sm
tags: [installation, peter-sm]
created: '2026-10-29'
---

# Installation peter-sm

An [SH10RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md) with an
[SBR160](device-sbr-battery.md), read on the inverter's own LAN port, with a WiNet-S fitted but not
in the path. Two readings, both with a control test, both from Home Assistant. The first was
published as `anonymous`; the second is signed `peter_sm`. Both carry the stand-in
`anon-91477823483`, so they are one installation.

- **[13074](register-13074.md) writes times ten.** The probe answered it by refusal in both
  readings, and the second run's readback through the cable matched with feed-in limitation on.
- **The house holds the battery at 10 W** in the second reading: `battery_max_charge_power` and
  `battery_max_discharge_power` were 10 W before the run, where the first reading had 10000 W. So
  neither forced check could move the battery, and their "nothing measurable happened" says
  nothing about the inverter.

## Surveys

- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
