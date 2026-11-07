---
type: entity
title: Register 32998 (site import power limit)
tags: [register, holding, import-limit, undocumented]
created: '2026-11-07'
---

# Register 32998 (site import power limit)

A holding register in no Sungrow document here, which iSolarCloud shows as "Site import power
limit". Protocol address 32997. The integration reads it as a diagnostic sensor, **Grid import
limit** in kW, and offers no control; the survey's register dump reads it too.

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
  cap. The device refuses 0 and 5001 with exception 0x04 and accepts 5000
  ([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)). The control test's
  `--import-limit` check confirmed it there too ([the run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)).
- **There it does not hold against house load the battery does not cover.** With the battery
  held idle by a forced stop and ~2.2 kW of load, import ran at the whole load against a
  2.00 kW cap, as at 20.00 kW; the inverter neither shed load nor discharged
  ([the load run](../sources/mkaiser-import-limit-load-2026-11-07-summary.md)). The cap limits
  what the inverter draws, a charge, not the house past it.
- **On one SH10RT-V112 it does not hold during a forced charge**, by its owner's report, with
  how the charge was commanded and the B001 firmware unknown;
  [open](../queries/does-the-import-limit-hold-during-a-forced-charge.md).

## What the surveys read

| Value | kW | Where |
| --- | --- | --- |
| 2000 | 20.00 | every SH-RT dump on P020, P022 and P023 except peter-sm: [mkaiser](installation-mkaiser.md), [gerd](installation-gerd.md), [bar12](installation-bar12.md), [fwitten](installation-fwitten.md), [mahagon](installation-mahagon.md), [robbensonmio](installation-robbensonmio.md) and two published as `anonymous` |
| 950, then 990 | 9.50, 9.90 | [peter-sm](installation-peter-sm.md), whose owner sets it |
| 1300 | 13.00 | all four SH-RS dumps: [Jam3s97](installation-jam3s97.md), [brendan](installation-brendan.md) and two published as `anonymous` |
| 4347 | 43.47 | [ra1k-0](installation-ra1k-0.md)'s [SH20T](device-sh-t.md) |

Whether 2000 on the SH-RT and 1300 on the SH-RS are factory defaults is not on record: only
Jam3s97 is known to have written theirs. Every value is the device's own word, read through
the cable and a WiNet-S alike where a house has both.

## For the integration

A control needs a write watched by this repository, per firmware
([firmware gating](../concepts/firmware-gating.md)): P020 has three, the last by the
[control test](../concepts/control-test.md)'s `--import-limit` check, which is how other
firmware gets one. A number entity would range over 1-5000 (0.01-50.00 kW), the words the
SH10RT and the SH10RS accept. `Todo.md` holds the plan.
