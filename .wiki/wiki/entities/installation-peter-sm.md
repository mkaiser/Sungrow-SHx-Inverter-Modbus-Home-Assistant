---
type: entity
title: Installation peter-sm
tags: [installation, peter-sm]
created: '2026-10-29'
---

# Installation peter-sm

An [SH10RT-V112](device-sh-rt.md) on [P023](firmware-sapphire-h-b001-v000-p023.md) with an
[SBR160](device-sbr-battery.md), read on the inverter's own LAN port, with a WiNet-S fitted but not
in the path. Twenty-three readings, all from Home Assistant, nineteen with a capability test. The first was
published as `anonymous`; the later twenty-two are signed `peter_sm`. All carry the stand-in
`anon-91477823483`, so they are one installation.

- **[13074](register-13074.md) writes times ten.** The probe answered it by refusal in every
  reading that ran, and the readback through the cable matched with feed-in limitation on.
- **[31211](register-31211.md) answers 0x55**; the PV cut has not been written here (no leave).
- **[The site import limit holds](register-32998.md)**, twice, in the twenty-first and
  twenty-second readings: under a forced charge over the cable, caps of 800 W and 1730 W brought
  import from 1438 W to 768 W and from 2359 W to 1702 W, and it returned both times. This is the
  first SH10RT-V112 to be watched obeying 32998, the model of the one owner report against it
  ([the query](../queries/does-the-import-limit-hold-during-a-forced-charge.md)). The range words:
  0 refused with 0x04, 5000 taken, and **5001 lost the connection** rather than being refused, as
  writes this house will not take do.
- **Forced charge, forced discharge and the export limit all act as commanded**, over the cable,
  in the third reading (outcome 0): 1248 W, 1250 W and an export held at 1250 W against 1250 W
  commanded. The first P023 SH10RT-V112 with all three confirmed. The sixth and seventh readings
  confirm all three again, with nine of nine readbacks matched.
- **The charge window's write of 33213 lost the connection every time it was tried**: in the
  sixth, seventh, tenth, twelfth, thirteenth, fifteenth, sixteenth, seventeenth, eighteenth,
  twentieth, twenty-first, twenty-second and twenty-third readings (2026-11-02 to 2026-11-18),
  thirteen of thirteen,
  so the window was never measured here;
  [open](../queries/does-writing-33213-drop-the-link-at-peter-sm.md). From the sixteenth reading
  on, other writes lost it too: 13059 once, 13050 (EMS mode 3) four times, 33047 (a value above its
  bound) three times, 32998's word 5001, and the discharge-window write after 33213 each time.
- **A Modbus restart did as it was told** in the tenth reading: stopped in 2.0 s, running again
  269 s after the start command, in daylight; and four times more, at 271 s, 301 s, 361 s (after
  dark) and 271 s ([twelfth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10-summary.md) to
  [fifteenth](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md) readings),
  and three times more, at 363 s (after dark), 271 s and 303 s (sixteenth to eighteenth), and at
  271 s in the twentieth, twenty-first and twenty-second. Eleven restarts, six of them back at
  271 s to the second. Settings survived every restart.
- **A twelfth restart, after dark on an empty pack, did not come back to Running**, and the run
  reported outcome 5 and "the link dropped" though no poll was refused: the pack was at 1.0 %,
  under its 5 % minimum, and the inverter waited in Standby, as it does without the test. Every
  setting read back on the first attempt, and the inverter ran again in the days after (154
  Running observations to 57 Standby); a false alarm, not a house left changed
  ([twenty-third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21-summary.md)).
- **Forced discharge and the export limit acted again** in the thirteenth and fifteenth readings
  (1250 W and 1248 W; export held at 1249 W and 1246.5 W against 1250 W); nine of nine readbacks
  matched, 13074 times ten each time.
- **Write paths and upper bounds**, from the sixteenth reading on: backup mode, load control,
  the weekend discharge enable and the second forced-charging window took their own words, and
  EMS modes 2 and 4 were taken (3 twice, its write dropped twice). 13059 refuses 51 % and 13058
  101 %, but **33047, 33048 and 13052 store 8200 W above their 8100 W maximum, and 33149 and
  33150 store 1010 W above 1000 W**: the firmware does not enforce those bounds
  ([sixteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)).
  The discharging start threshold did as it was told twice.
- The tenth reading's file is named `battery-thirdparty`, though the pack is the SBR160: its
  document lost the pack's own section (see [the page](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md)).
- The house held `battery_max_charge_power` at 10 W from the twelfth to the twentieth reading, so
  the forced charge was not checked between the third and the twenty-first. In the twenty-first and
  twenty-second it is back at 10000 W, and **forced charge, forced discharge and the export limit
  all acted again** (1248 W, 1251 W and 1249 W, export held at 1249.5 W and 1253 W against 1250 W
  commanded, through the feed-in ratio rather than 13074).
- The fifth reading's capability test did not run: the inverter was in Standby that evening.
- **The second reading's forced checks are not evidence**: the house held
  `battery_max_charge_power` and `battery_max_discharge_power` at 10 W then, where the first and
  third readings have 10000 W, so neither could move the battery.

- **Its WiNet-S answers a multicast mDNS browse** from Home Assistant on the house's LAN, the
  first browse recorded in a house; its TXT record's `ethinfo` carries an address
  ([twentieth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md)).
  The twenty-second reading, the first written by schema 28, adds that 15 services were heard in
  the browse and that Home Assistant is on the inverter's own subnet.

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
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventeenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, nineteenth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-17-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twentieth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-first reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-second reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-third reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21-summary.md)
