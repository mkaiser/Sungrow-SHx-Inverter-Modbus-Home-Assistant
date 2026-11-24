---
type: entity
title: Register 32998 (site import power limit)
tags: [register, holding, import-limit, undocumented]
created: '2026-11-07'
---

# Register 32998 (site import power limit)

A holding register in no Sungrow document here, which iSolarCloud shows as "Site import power
limit". Protocol address 32997. On firmware with a watched write the integration offers it as a
number, **Grid import limit** in W; elsewhere it reads it as a diagnostic sensor of the same name
in kW. The diagnosis's register dump reads it too.

## What is established

- **The unit is 0.01 kW.** [Jam3s97](installation-jam3s97.md) wrote 1300 and the meter held
  13.00 kW; two other owners' readbacks fit the same scale
  ([discussion #546](../sources/discussion-546-site-import-power-limit-summary.md)).
- **On an [SH10RS](device-sh-rs.md) it limits grid import**, through a WiNet-S and over RS485
  alike, and the device refuses a word above 5000 (50.00 kW) with an exception
  ([discussion #546](../sources/discussion-546-site-import-power-limit-summary.md)).
- **On an [SH10RT](device-sh-rt.md) on [P020](firmware-sapphire-h-b001-v000-p020.md) it holds during a
  forced charge** commanded through 13050 and 13051: at 200 (2.00 kW) under a 4500 W charge, import
  held at 1978 W median, the charge cut to ~1500 W and the house load untouched, within one ~5 s
  sample both ways; watched by this repository over the cable ([the run](../sources/mkaiser-import-limit-2026-11-07-summary.md)).
- **There it caps grid import alone, with PV counted.** With ~1.1 kW of PV at 200, the battery took
  PV + 2.00 kW - load, and it followed a load step from 1810 W to 615 W within ~4 s. At 1 (0.01 kW) a
  forced charge drew only on PV (import ~15 W). It settles within ~4-6 s and holds 0-3 % above the
  cap. **PV was above the load there, with a clean after-bracket**: at ~1.05-1.1 kW of PV and ~0.6 kW of
  load, import was 2047 W under the 2.00 kW cap, 20 W under 0.01 kW and 4269 W with the cap lifted, the
  4500 W charge commanded throughout. The device refuses 0 and 5001 with exception 0x04 and accepts 5000
  ([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)). The capability test's
  `--import-limit` check confirmed it there too ([the run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)),
  and again from the integration on 0.1.0a46 (1830 W cap, import 2439 W -> 1876.5 W -> 2323 W, PV below
  the load). **With PV above the load** it held again, by hand under passing clouds: a 2190 W cap
  under a 4500 W forced charge took median import from 4386 W to 1933 W while PV (2.6-3.6 kW) exceeded
  the ~2.1 kW load, the charge cut to 2.4-3.0 kW; single samples overshot to ~4 kW for ~10 s where PV
  dipped, and no clean after-bracket was possible
  ([the production install](../sources/mkaiser-production-install-2026-11-21-summary.md)). The
  engine's own check cannot take that case: its fixed 1250 W forced charge is absorbed by a PV surplus
  and draws too little from the grid to cap.
  **At peter-sm the same three words answered differently in one respect**: 0 refused with 0x04 and
  5000 was taken, but 5001 **lost the connection** instead of drawing a refusal -- that house drops
  the link on several writes it will not take, so it says nothing about the register's range
  ([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).
- **There it does not hold against house load the battery does not cover.** With the battery
  held idle by a forced stop and ~2.2 kW of load, import ran at the whole load against a
  2.00 kW cap, as at 20.00 kW; the inverter neither shed load nor discharged
  ([the load run](../sources/mkaiser-import-limit-load-2026-11-07-summary.md)). The cap limits
  what the inverter draws, a charge, not the house past it. In self-consumption with PV above the
  load it changes nothing: a 0.01 kW cap left a charge from PV, export and PV as they were
  ([the export run](../sources/mkaiser-import-limit-export-2026-11-08-summary.md)).
  Nor does it draw on the battery past its own limit: with the discharge limit at 500 W under a
  ~1.1 kW load after dark, a 0.05 kW cap left import at ~700 W and the battery at 499 W
  ([the discharge run](../sources/mkaiser-import-limit-discharge-2026-11-08-summary.md)).
- **On [P023](firmware-sapphire-h-b001-v000-p023.md) it holds under a forced charge too**, over the
  cable and written through a [WiNet-S](device-winet-s.md): at [bar12](installation-bar12.md) a
  1.00 kW cap cut a 1250 W charge to ~550-730 W and held import at 942 W and ~960 W, slightly
  under the cap. With the battery empty in normal operation a 0.10 kW cap left the whole load
  imported ([the bar12 runs](../sources/bar12-import-limit-2026-11-07-summary.md)). It holds a
  charge commanded by the forced-charging schedule (33208-33219) as well: 4099 W cut to ~510-690 W,
  import 947-964 W against 1.00 kW, following the load ([the schedule run](../sources/bar12-import-limit-schedule-2026-11-07-summary.md)).
- **On [P022](firmware-sapphire-h-b001-v000-p022.md) it holds under a forced charge**, over the cable
  (import 1002 W against 1.00 kW) and written through a WiNet-S (956-1009 W), at
  [gerd](installation-gerd.md) ([the run](../sources/gerd-import-limit-2026-11-08-summary.md)), and a
  scheduled charge through the dongle: 4399 W cut to 862 W, import 994 W
  ([the schedule run](../sources/gerd-import-limit-schedule-2026-11-08-summary.md)).
- **On an SH10RT-V112 on [P023](firmware-sapphire-h-b001-v000-p023.md) it holds too**, twice, at
  [peter-sm](installation-peter-sm.md), over the cable, the charge commanded through 13050 and
  13051: a 800 W cap took import from 1438 W to 768 W and a 1730 W cap took 2359 W to 1702 W, each
  returning when the cap came off (the capability test's `--import-limit` check;
  [the twenty-first](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md)
  and [twenty-second readings](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20-summary.md)).
  That is the model of the one report against it.
- **At [fwitten](installation-fwitten.md)'s master SH10RT-V112 on P023 it did not hold**, which
  contradicts peter-sm on the same model and firmware: over the cable, after dark, a 1090 W cap
  under the engine's 1250 W forced charge left import at 1718 W (1724 W before, 1710 W after),
  with the charge itself obeying, the battery at 15.2 % against a 7 % floor and PV at 0 W
  ([the run](../sources/fwitten-import-limit-engine-2026-11-22-summary.md)). The range words
  answered as everywhere: 0 and 5001 refused with 0x04, 5000 taken. **Nor did it on any of four further
  caps**, the word read back in every sample: 1150 W under a 1250 W charge (1783 W), and 2190 W
  under a 3601 W charge on the master (4263 W), on the slave (4236 W) and on both (4185 W), the charge
  never moving by more than 2 W, the battery at 79-88 % ([the cluster run](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md)). So the cap's size, the unit and
  a low battery do not explain it. What does is open. The one difference on record: fwitten's master leads a
  **cluster**, as swo14's did where it failed below, and every house where it held is a single inverter.
- **On an [SH6.0RS](device-sh-rs.md) on [P066](firmware-sunstone-h-b000-v001-p066.md) it holds**, the
  first SH-RS watched: at [icefest](installation-icefest.md)'s, over RS485, a 520 W cap took import from
  1040 W to 528 W, 1029 W after; the house's own setting is 10.0 kW (word 1000)
  ([the diagnosis](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2-summary.md)).
- **On [`01011.95.03`](firmware-sapphire-h-01011-95-03.md) it did not hold**, the first measured
  failure: at [swo14](installation-swo14.md)'s SH10RT-20 a 520 W cap against 1030 W of import
  under a forced charge moved nothing (992 W during, 1020.5 W after). That battery was at 3.3 %
  against a 10 % floor, so cutting the charge was nearly all the inverter had to give. Every
  SH-RT that obeyed is on P020, P022 or P023, and the integration offers the control there only
  ([the host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md)).
  The range words answered there as at mkaiser: 0 and 5001 refused with 0x04, 5000 taken.
  Not checked again on 2026-11-24, the battery too full ([the host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)).
  That house is a cluster master too, like fwitten's, where the cap failed on P023 with the
  battery well above its floor; so the low battery may not be the whole explanation here.
- **On one other SH10RT-V112 it does not hold during a forced charge**, by its owner's report, with
  how the charge was commanded and the B001 firmware unknown;
  [open](../queries/does-the-import-limit-hold-during-a-forced-charge.md).

## What the diagnoses read

| Value | kW | Where |
| --- | --- | --- |
| 2000 | 20.00 | every SH-RT dump on P020, P022 and P023 except peter-sm: [mkaiser](installation-mkaiser.md), [gerd](installation-gerd.md), [bar12](installation-bar12.md), [fwitten](installation-fwitten.md), [mahagon](installation-mahagon.md), [robbensonmio](installation-robbensonmio.md) and two published as `anonymous` |
| 950, then 990 | 9.50, 9.90 | [peter-sm](installation-peter-sm.md), whose owner sets it |
| 1300 | 13.00 | all four SH-RS dumps: [Jam3s97](installation-jam3s97.md), [brendan](installation-brendan.md) and two published as `anonymous` |
| 1000 | 10.00 | [icefest](installation-icefest.md)'s SH6.0RS on P066 (its readings; a download has no dump) |
| 4347 | 43.47 | [ra1k-0](installation-ra1k-0.md)'s [SH20T](device-sh-t.md) |

On [swo14](installation-swo14.md)'s cluster both inverters read 2000 as well, the slave included
-- but its capability test counts the register absent, because the snapshot gates it behind the
battery capability and the slave has no pack. At fwitten a slave's takes a word, reads it back and
caps nothing ([the cluster run](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md)).

Whether 2000 on the SH-RT and 1300 on the SH-RS are factory defaults is not on record: only
Jam3s97 is known to have written theirs. Every value is the device's own word, read through
the cable and a WiNet-S alike where a house has both.

## For the integration

A control needs a write watched by this repository, per firmware
([firmware gating](../concepts/firmware-gating.md)): P022 has two (gerd), P023 three (bar12), the SH-RS's P066 one (icefest), P020 three, the last by the
[capability test](../concepts/capability-test.md)'s `--import-limit` check, which is how other
firmware gets one.

So on P020, P022, P023 and the SH-RS's P066 it is the number *Grid import limit* (`Capability.SITE_IMPORT_LIMIT_CONTROL`
in `CONFIRMED_ON_FIRMWARE`), 10-50000 W in steps of 10 W, one count each: the words 1-5000 the
SH10RT and the SH10RS accept. There the read-only sensor is not created. On P023 it fails at a cluster
([fwitten](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md), five caps) and holds at single inverters: whether a
cluster master should be offered the control is open. Elsewhere the sensor
stays, and where 32998 reads 0 or 0xFFFF neither exists (`Capability.SITE_IMPORT_LIMIT`; the
register refuses 0, so a 0 is a dongle answering for nothing).
