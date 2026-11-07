---
type: entity
title: Installation bar12
tags: [installation, bar12]
created: '2026-10-29'
---

# Installation bar12

One [SH10RT-20](device-sh-rt.md) with an [SBR096](device-sbr-battery.md), reached two ways: a
cable in the inverter's own LAN port, and a [WiNet-S](device-winet-s.md) on WiFi (on Ethernet too,
earlier). Read on [P020](firmware-sapphire-h-b001-v000-p020.md) and on
[P023](firmware-sapphire-h-b001-v000-p023.md). [Register 13074](register-13074.md) writes times ten. After dark with the battery empty it waits in
Standby; [register 13017](register-13017.md) and a forced charge each wake it, and
[register 32998](register-32998.md) capped a forced charge over the cable and through the dongle
([forced startup](../sources/bar12-forced-startup-2026-11-07-summary.md),
[the import limit](../sources/bar12-import-limit-2026-11-07-summary.md)).

## Diagnoses

- [SH10RT-20, B001.V000.P020, bar12, a WiNet-S on Ethernet](../sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P020, bar12, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port, second reading](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi, second reading](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-2-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md)
- [The WiNet-S's TLS certificate](../sources/bar12-tls-certificate-2026-11-06-summary.md), 2026-11-06, the same as gerd's
