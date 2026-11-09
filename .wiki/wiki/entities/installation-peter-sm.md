---
type: entity
title: Installation peter-sm
tags: [installation, peter-sm]
created: '2026-10-29'
---

# Installation peter-sm

An [SH10RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md) with an
[SBR160](device-sbr-battery.md), read on the inverter's own LAN port, with a WiNet-S fitted but not
in the path. Fifteen readings, all from Home Assistant, twelve with a capability test. The first was
published as `anonymous`; the later fourteen are signed `peter_sm`. All carry the stand-in
`anon-91477823483`, so they are one installation.

- **[13074](register-13074.md) writes times ten.** The probe answered it by refusal in every
  reading that ran, and the readback through the cable matched with feed-in limitation on.
- **[31211](register-31211.md) answers 0x55**; the PV cut has not been written here (no leave).
- **Forced charge, forced discharge and the export limit all act as commanded**, over the cable,
  in the third reading (outcome 0): 1248 W, 1250 W and an export held at 1250 W against 1250 W
  commanded. The first P023 SH10RT-V112 with all three confirmed. The sixth and seventh readings
  confirm all three again, with nine of nine readbacks matched.
- **The charge window's write of 33213 lost the connection every time it was tried**: in the
  sixth, seventh, tenth, twelfth, thirteenth and fifteenth readings (2026-11-02 to 2026-11-09), six
  of six, so the window was never measured here;
  [open](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- **A Modbus restart did as it was told** in the tenth reading: stopped in 2.0 s, running again
  269 s after the start command, in daylight; and four times more, at 271 s, 301 s, 361 s (after
  dark) and 271 s ([twelfth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10-summary.md) to
  [fifteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md) readings).
- **Forced discharge and the export limit acted again** in the thirteenth and fifteenth readings
  (1250 W and 1248 W; export held at 1249 W and 1246.5 W against 1250 W); nine of nine readbacks
  matched, 13074 times ten each time.
- The tenth reading's file is named `battery-thirdparty`, though the pack is the SBR160: its
  document lost the pack's own section (see [the page](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md)).
- The house often holds `battery_max_charge_power` at 10 W (the twelfth to fifteenth readings), so
  the forced charge has not been checked since the third reading.
- The fifth reading's capability test did not run: the inverter was in Standby that evening.
- **The second reading's forced checks are not evidence**: the house held
  `battery_max_charge_power` and `battery_max_discharge_power` at 10 W then, where the first and
  third readings have 10000 W, so neither could move the battery.

- **The history block and the schedules**, in the fourth reading's dump: inputs 6101-6826 all
  answer over the cable, and the forced-charging schedule (33208-33219) is off. [Register 32998](register-32998.md),
  which the owner uses as a site import power limit, holds 950 (9.50 kW, at 0.01 kW).

## Diagnoses

- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fourth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fifth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-4-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventh reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighth reading, a diagnostics download](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, ninth reading, a diagnostics download](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, tenth reading, with a capability test](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eleventh reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-9-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twelfth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, thirteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fourteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-12-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fifteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md)
