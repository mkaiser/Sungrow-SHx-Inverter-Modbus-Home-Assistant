---
type: source
title: mkaiser-import-limit-export-2026-11-08.md
source_path: raw/mkaiser-import-limit-export-2026-11-08.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-32998, import-limit, pv, export, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The site import limit with PV surplus and export, mkaiser, 2026-11-08

`.wiki/raw/mkaiser-import-limit-export-2026-11-08.md` records two watched writes of
[register 32998](../entities/register-32998.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, in self-consumption with ~0.9-1.2 kW of PV above the load.

| Claim | Evidence | Status |
| --- | --- | --- |
| The cap does not disturb a charge from PV surplus | at 0.01 kW the battery went on charging at ~-300 W | watched by this repository, one run |
| It does not curtail PV or export | with the charge limited, export ~-300 W under a 0.01 kW cap as without it; PV kept rising | one run |
| In self-consumption it does not hold small imports to the cap | import 20-60 W against 10 W, one sample at 1228 W | one run |
| A charge limit of 100 W (33047 = 10) stops the charge altogether | battery 0 W, the surplus exported | one run |

So the cap acts only on a charge the inverter draws from the grid; in normal operation it changes
nothing, with or without export. Restored and read back each time.
