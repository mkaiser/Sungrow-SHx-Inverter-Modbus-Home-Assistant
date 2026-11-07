---
type: source
title: mkaiser-import-limit-load-2026-11-07.md
source_path: raw/mkaiser-import-limit-load-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, house-load, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The site import limit against house load, mkaiser, 2026-11-07

`.wiki/raw/mkaiser-import-limit-load-2026-11-07.md` records a watched write of
[register 32998](../entities/register-32998.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, after dark, with the battery held idle by a forced stop (13050 = 2,
13051 = 0xCC) and a house load of ~2.2 kW. It follows [the night](mkaiser-import-limit-2026-11-07-summary.md)
and [PV](mkaiser-import-limit-pv-2026-11-07-summary.md) runs, which capped a forced charge.

| Claim | Evidence | Status |
| --- | --- | --- |
| The cap does not hold against house load the battery does not cover | at 200 (2.00 kW), battery idle, import ~2197 W: the whole load, as at 2000 | watched by this repository, one run |
| The inverter neither sheds load nor discharges to meet it | battery 0 W throughout the forced stop, load unchanged | one run, under a forced stop |
| A forced stop takes effect within ~2 s | battery 2327 → 0 W, import -41 → 2195 W, one sample | one run |
| In self-consumption with the battery covering the load, 200 changes nothing | meter ~8 W, battery unchanged | one run |

So on P020 the cap limits what the inverter itself draws from the grid (a charge), not what
the house draws past it. Whether the battery would discharge to meet the cap in
self-consumption, with a load above what the battery's own limits let it cover, was not tried:
here the battery covered the whole load.

The run used a script outside the control test's engine, with its rules kept: the stand-in was
checked, the snapshot was flushed before the first write, and the restore wrote raw words and
checked them by raw read. Every word was restored. Over the cable, so it says nothing about a
WiNet-S.
