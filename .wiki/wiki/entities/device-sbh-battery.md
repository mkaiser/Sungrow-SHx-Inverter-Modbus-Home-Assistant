---
type: entity
title: SBH battery
tags: [battery, sbh, sub-device]
created: '2026-10-29'
---

# SBH battery

The high-voltage pack for the [SH-T](device-sh-t.md): SBH200 and SBH400 in
this corpus, both read through a [WiNet-S](device-winet-s.md). The
survey reads it with the [SBR](device-sbr-battery.md)'s map, so its components carry
`sbr_battery_*` names.

- At [ra1k-0](installation-ra1k-0.md) the SBH400 answered at unit **2**
  through the dongle with the summary block (voltage around 588 V).
- At [jm493](installation-jm493.md) the SBH200's `sbr_battery_cells` and
  `sbr_battery_modules` did not read. That is the same pattern as an SBR
  behind a dongle, so it says nothing yet about whether the SBH has cell
  data.

Unmeasured: an SBH on an inverter's own LAN port.
