---
type: source
title: mkaiser-import-limit-2026-11-07.md
source_path: raw/mkaiser-import-limit-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, forced-charge, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The site import limit under a forced charge, mkaiser, 2026-11-07

`.wiki/raw/mkaiser-import-limit-2026-11-07.md`: a watched write of
[register 32998](../entities/register-32998.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, at night with no PV, during a forced charge of 4500 W through 13050 and 13051.

| Claim | Evidence | Status |
| --- | --- | --- |
| On P020 the limit holds during a forced charge commanded through 13050/13051 | 32998 = 200: import 1978 W median (max 1999 W) against 5088 W before | watched by this repository, one run |
| The unit is 0.01 kW | 200 held import under 2.00 kW | agrees with [discussion #546](discussion-546-site-import-power-limit-summary.md) |
| The inverter meets the cap by cutting the charge, not the load | battery -4501 W to -1495 W, load ~405 W throughout | one run |
| It acts within one ~5 s sample, both ways | import 5088 to 1975 W, and 1978 to 5084 W | one run |
| The cable reads back what was written | 200, then 2000 | one run |

The run used a script outside the control test's engine, with its rules kept: stand-in checked,
snapshot flushed before the first write, a restore of raw words checked by raw read. Every word
was restored. It was through the cable, so it says nothing about a WiNet-S.
