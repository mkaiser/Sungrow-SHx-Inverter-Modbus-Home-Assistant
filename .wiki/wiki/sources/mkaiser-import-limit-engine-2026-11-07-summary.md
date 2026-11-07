---
type: source
title: mkaiser-import-limit-engine-2026-11-07.md
source_path: raw/mkaiser-import-limit-engine-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, capability-test, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write, standby]
---

# The capability test's import limit check, mkaiser, 2026-11-07

`.wiki/raw/mkaiser-import-limit-engine-2026-11-07.md` records the first run of the
[capability test](../concepts/capability-test.md)'s `--import-limit` check on hardware: at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the cable, with the PV isolator
open.

| Claim | Evidence | Status |
| --- | --- | --- |
| The engine's check confirms the cap on P020 | cap 1580 W: import 2192 → 1549 → 2206 W, drift 14 W, "did as it was told" | one run, agrees with [the night](mkaiser-import-limit-2026-11-07-summary.md) and [PV](mkaiser-import-limit-pv-2026-11-07-summary.md) script runs |
| 0 and 5001 are refused with 0x04, 5000 is taken | the check's word probe | agrees with the PV script run |
| Everything was put back | the report, and a raw read after it | one run |
| With the DC isolator open, the inverter first goes to Standby, battery idle | 13000 = 0x0008, battery 0 W, the load from the grid; a run refused | one occasion |
| It returns to Running on the battery minutes later, PV still 0 W | 13000 = 0x0040, battery discharging 3299 W | one occasion; how long it took was not timed |

Over the cable, so the run says nothing about a WiNet-S.
