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

- **The SBR's scales hold.** Voltage, health and temperature agree with what
  the inverter reports about the same pack ([ra1k-0](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md), [jm493](../sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md)).
  The pack's current is positive while discharging, as the inverter's
  `battery_power` is ([jm493](../sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md)).
- **The pack's state of charge is its own measurement**: jm493's pack said
  85.5 % where the inverter said 80.0 % ([jm493](../sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md)).
- **Both packs read over their rating**: 20.27 kWh on an SBH200, 40.55 kWh on
  an SBH400 ([jm493](../sources/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan-summary.md), [ra1k-0](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-summary.md)). So `model_for_capacity` names a
  pack within a window either side of its rating, not only below it.

Unmeasured: an SBH on an inverter's own LAN port, which is what would read
its cell and module layout.
