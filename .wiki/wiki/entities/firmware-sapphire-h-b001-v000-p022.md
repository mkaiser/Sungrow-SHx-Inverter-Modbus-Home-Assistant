---
type: entity
title: SAPPHIRE-H_B001.V000.P022
tags: [firmware, sapphire-h-b001-v000-p022]
created: '2026-10-29'
---

# SAPPHIRE-H_B001.V000.P022

SH-RT firmware in the B001 numbering ([SH-RT](device-sh-rt.md)).

- [Register 13074](register-13074.md) writes **times ten** (probed at [gerd](installation-gerd.md), cable and dongle).
- [Register 31211](register-31211.md) answers 0x55, and the cut is **confirmed** by a capability test at [gerd](installation-gerd.md) over the cable (2938 W, 0 W, 1913 W), so P022 is in `CONFIRMED_ON_FIRMWARE`.
- The cut did as told again on 2026-11-03, over the cable (2381, 0, 1976 W) and through the dongle (1208.5, 0, 1466 W).
- A Modbus restart in daylight took 181 s from stop to Running, at three runs at gerd.
- [Register 32998](register-32998.md), the site import limit, **holds under a forced charge**: at
  1.00 kW, import 1002 W over the cable and 956-1009 W written through the dongle, at gerd
  ([the run](../sources/gerd-import-limit-2026-11-08-summary.md)). It holds a scheduled charge too,
  through the dongle ([the schedule run](../sources/gerd-import-limit-schedule-2026-11-08-summary.md)).
- [Register 13052](register-13052.md), the forced power, refuses a value above the inverter's rated power
  (8000 W on an SH8.0RT) with 0x04, and stores one above the battery-derived maximum. `battery_max_soc`
  and `battery_min_soc` refuse a step past their maximum; the five power limits store it, as on P023
  ([the day](../sources/gerd-auto-repeat-2026-11-21-summary.md)).
- Forced discharge (1250 W, 1251 W measured), the export limit through the feed-in ratio (1250 W cap,
  1243 W), the charging start threshold and the charge ceiling did as told, from Home Assistant at gerd.

## Diagnoses

- [SH6.0RT-20, B001.V000.P022, anonymous, through a Modbus proxy, SBR128](../sources/sh60rt-20-b001v000p022-3p-anonymous-anon-45132049665-battery-sbr128-meter-direct-lan-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md)
