---
type: source
title: fwitten-import-limit-cluster-2026-11-24.md
source_path: raw/fwitten-import-limit-cluster-2026-11-24.md
ingested: '2026-11-24'
created: '2026-11-24'
tags: [register-32998, import-limit, forced-charge, sh10rt-v112, sapphire-h-b001-v000-p023, fwitten, cluster, write]
---

# The site import limit at fwitten's cluster, by master, slave and both, 2026-11-24

`.wiki/raw/fwitten-import-limit-cluster-2026-11-24.md` records a script run over both inverters' cable ports at
[fwitten](../entities/installation-fwitten.md)'s cluster: master (`anon-86493117545`, SBR096) and
slave (`anon-33442450531`, no battery), both [SH10RT-V112](../entities/device-sh-rt.md) on
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md), after dark, the charge commanded on the
master through 13050, 13051 and 13052.

| Phase | Cap on | Cap, W | Import before / during / after, W | 32998 during, master / slave | Battery, W | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| A | master | 1150 | 1776 / 1783 / 1776 | 115 / 2000 | -1249 | did not hold |
| B | master | 2190 | 4190 / 4263 / 4276 | 219 / 2000 | -3601 | did not hold |
| C | slave | 2190 | 4276 / 4236 / 4192 | 2000 / 219 | -3601 | did not hold |
| D | both | 2190 | 4192 / 4185 / 4184 | 219 / 219 | -3601 | did not hold |

| Claim | Evidence | Status |
| --- | --- | --- |
| [Register 32998](../entities/register-32998.md) **is stored and has no effect on a forced charge here** | all four phases; every sample read the word back, and the charge never moved by more than 2 W | four brackets, agreeing with [the engine's](fwitten-import-limit-engine-2026-11-22-summary.md) |
| The size of the cap does not explain it | A asked for 625 W off, B-D for 2000 W off | |
| Neither does the unit it is written to | master, slave and both, all read back | first measurement of a slave's 32998 |
| Nor a low battery | SoC 79-88 % | |
| Everything was put back | the script's readback and a separate client's, nine seconds after | |

Not established: why; 32998 at a cluster written through a WiNet-S; whether the slave takes part when it
runs (it stood in Standby at 0 W); whether a slave mirrors the master's 13050, which was not read; why
the charge reached 3601 W of 4000 W.
