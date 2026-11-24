---
type: source
title: fwitten-cluster-mirror-2026-11-24.md
source_path: raw/fwitten-cluster-mirror-2026-11-24.md
ingested: '2026-11-24'
created: '2026-11-24'
tags: [cluster, ems, register-33500, sh10rt-v112, sapphire-h-b001-v000-p023, fwitten, mkaiser, write]
---

# The slave's EMS mode, and 33500, at fwitten's cluster, 2026-11-24

`.wiki/raw/fwitten-cluster-mirror-2026-11-24.md`: over the cable at [fwitten](../entities/installation-fwitten.md)'s cluster on
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md).

| Claim | Evidence | Status |
| --- | --- | --- |
| **A slave's 13050 follows the master's** | master written 2, the slave read 2 in the first sample after and in the 22 that followed; master put back to 0, the slave read 0 in the next | one run, nothing written to the slave |
| Both inverters' 13051 and 13052 stayed at stop and 0 | every sample | |
| Forced mode at stop idles the battery | 508 W to 0 W, the house on the grid; discharging again ~4 s after | |
| **33500 is 0xAA on both cluster members and 0x55 on a lone inverter** | both fwitten units; [mkaiser](../entities/installation-mkaiser.md)'s SH10RT | one cluster, one lone inverter ([register 33500](../entities/register-33500.md)) |
| 33501 is the role, 160 master and 161 slave; 33501 and 33502 say nothing about being in a cluster | the lone inverter reads 160 and 2 as the master does | as above |

Not established: whether a write to the slave's 13050 holds; whether the slave follows 13051 and 13052 too.
