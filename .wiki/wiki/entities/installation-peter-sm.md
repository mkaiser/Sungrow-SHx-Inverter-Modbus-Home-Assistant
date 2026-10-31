---
type: entity
title: Installation peter-sm
tags: [installation, peter-sm]
created: '2026-10-29'
---

# Installation peter-sm

An [SH10RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md) with an
[SBR160](device-sbr-battery.md), read on the inverter's own LAN port, with a WiNet-S fitted but not
in the path. Three readings, each with a control test, all from Home Assistant. The first was
published as `anonymous`; the second and third are signed `peter_sm`. All carry the stand-in
`anon-91477823483`, so they are one installation.

- **[13074](register-13074.md) writes times ten.** The probe answered it by refusal in all three
  readings, and the readback through the cable matched with feed-in limitation on.
- **[31211](register-31211.md) answers 0x55**; the PV cut has not been written here (no leave).
- **Forced charge, forced discharge and the export limit all act as commanded**, over the cable,
  in the third reading (outcome 0): 1248 W, 1250 W and an export held at 1250 W against 1250 W
  commanded. The first P023 SH10RT-V112 with all three confirmed.
- **The second reading's forced checks are not evidence**: the house held
  `battery_max_charge_power` and `battery_max_discharge_power` at 10 W then, where the first and
  third readings have 10000 W, so neither could move the battery.

## Surveys

- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2-summary.md)
