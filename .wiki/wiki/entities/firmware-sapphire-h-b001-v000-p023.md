---
type: entity
title: SAPPHIRE-H_B001.V000.P023
tags: [firmware, sapphire-h-b001-v000-p023]
created: '2026-10-29'
---

# SAPPHIRE-H_B001.V000.P023

SH-RT firmware in the B001 numbering ([SH-RT](device-sh-rt.md)), version strings `SAPPHIRE-H_01011.95.14`.
The most-measured firmware in the corpus.

- [Register 13074](register-13074.md) writes **times ten**, on SH10RT-20 and SH10RT-V112, cable and dongle.
- Forced charge, forced discharge and the export limit **act as commanded** on an SH10RT-V112,
  over the cable, all in one run at [peter-sm](installation-peter-sm.md).
- [Register 31211](register-31211.md) answers 0x55, and the cut is **confirmed** by a capability test
  on [fwitten](installation-fwitten.md)'s master: P023 is in `CONFIRMED_ON_FIRMWARE`.
- At [peter-sm](installation-peter-sm.md) the charge window's write of 33213 lost the connection
  in all nine runs that wrote it, on five days, where fwitten's window did as it was told;
  [open](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- **Upper bounds, at [peter-sm](installation-peter-sm.md) over the cable**: 13059 refuses 51 % and
  13058 101 % with 0x04, but 33047, 33048 and 13052 store 8200 W, above the run's 8100 W maximum, and 33149 and 33150 store 1010 W, above 1000 W
  ([sixteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)).
- **Register 13088 follows the export limit as a share of the rating**, at
  [peter-sm](installation-peter-sm.md) over the cable: with 13074 at 1250 W on a 10000 W
  SH10RT-V112 it read 12.5 %, and 92 % before the write, in every run that recorded it
  (the export check's `feed_in_ratio`;
  [sixteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md),
  [eighteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16-summary.md)
  readings).
- [Register 32998](register-32998.md), the site import limit, **holds under a forced charge**, over
  the cable and through a WiNet-S, at [bar12](installation-bar12.md); it does not cap the load with
  the battery empty ([the runs](../sources/bar12-import-limit-2026-11-07-summary.md)). It holds a
  scheduled charge too ([the schedule run](../sources/bar12-import-limit-schedule-2026-11-07-summary.md)).
- [Register 13017](register-13017.md) is a **switch**: `0xAA` wakes a low-SoC standby inverter and
  keeps it running, `0x55` returns it to Standby, any other word is refused
  ([the run](../sources/bar12-forced-startup-2026-11-07-summary.md)). A forced charge, EMS or
  scheduled, wakes it by itself in ~2 min.

- On an SH6.0RT-V112 ([firetribe](installation-firetribe.md)) the 13074 write scale is not
  measured: through a busy WiNet-S its read was refused, and on the cable the inverter
  was starting.
- On a 5 kW SH5.0RT-V112 with version 1 `.95.14` ([mahagon](installation-mahagon.md)) the probe of
  13074 was refused three times: it multiplies. The factor is not separated from 0.1 % of the
  rating, which a refusal cannot show.

## Diagnoses

- [SH5.0RT-V112, B001.V000.P023, mahagon, the inverter's own LAN port](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md)
- [SH5.0RT-V112, B001.V000.P023, mahagon, a WiNet-S2 on WiFi](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-winet-wlan-summary.md)
- [SH6.0RT-V112, B001.V000.P023, firetribe, the inverter's own LAN port](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-summary.md)
- [SH6.0RT-V112, B001.V000.P023, firetribe, a WiNet-S on Ethernet](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, the inverter's own LAN port](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on Ethernet](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan-summary.md)
- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fourth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fifth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-4-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventh reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighth reading, a diagnostics download](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, ninth reading, a diagnostics download](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eleventh reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-9-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twelfth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, thirteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fourteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-12-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fifteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md)
- [SH6.0RT-20, B001.V000.P023, anonymous, through a Modbus proxy, SBR064, second reading](../sources/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-2-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, tenth reading, with a capability test](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port, SBR224](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-40315531061-battery-sbr224-meter-direct-lan-summary.md)
- [SH6.0RT-20, B001.V000.P023, anonymous, through a Modbus proxy, SBR064](../sources/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventeenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, nineteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-17-summary.md)
- [SH8.0RT-V112, B001.V000.P023, tristangrichard, the inverter's own LAN port](../sources/sh80rt-v112-b001v000p023-3p-tristangrichard-anon-04477133025-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, anonymous, through a Modbus proxy under load, SBR128](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan-summary.md)
