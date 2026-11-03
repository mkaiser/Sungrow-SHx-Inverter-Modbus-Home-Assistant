---
type: entity
title: SAPPHIRE-H_B001.V000.P022
tags: [firmware, sapphire-h-b001-v000-p022]
created: '2026-10-29'
---

# SAPPHIRE-H_B001.V000.P022

SH-RT firmware in the B001 numbering ([SH-RT](device-sh-rt.md)).

- [Register 13074](register-13074.md) writes **times ten** (probed at [gerd](installation-gerd.md), cable and dongle).
- [Register 31211](register-31211.md) answers 0x55, and the cut is **confirmed** by a control test at [gerd](installation-gerd.md) over the cable (2938 W, 0 W, 1913 W), so P022 is in `CONFIRMED_ON_FIRMWARE`.
- The cut did as told again on 2026-11-03, over the cable (2381, 0, 1976 W) and through the dongle (1208.5, 0, 1466 W).
- A Modbus restart in daylight took 181 s from stop to Running, at three runs at gerd.

## Surveys

- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md)
