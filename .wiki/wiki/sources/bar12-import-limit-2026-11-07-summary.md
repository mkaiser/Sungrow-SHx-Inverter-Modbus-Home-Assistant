---
type: source
title: bar12-import-limit-2026-11-07.md
source_path: raw/bar12-import-limit-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, forced-charge, standby, sh10rt-20, sapphire-h-b001-v000-p023, bar12, winet-s, write]
---

# The site import limit from standby, bar12, 2026-11-07

`.wiki/raw/bar12-import-limit-2026-11-07.md` records six watched runs of
[register 32998](../entities/register-32998.md) and the forced charge at
[bar12](../entities/installation-bar12.md)'s [SH10RT-20](../entities/device-sh-rt.md) on
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md), after dark, with the battery below its
minimum SoC and the inverter in Standby. Five over the cable, one through the
[WiNet-S](../entities/device-winet-s.md) judged by the cable.

| Claim | Evidence | Status |
| --- | --- | --- |
| On P023 the cap holds under a forced charge, over the cable | 1.00 kW cap, 1250 W charge cut to ~547 W, import 942 W (936-952) | watched by this repository, one run |
| It holds when written through a WiNet-S | the cable read ~960 W against 1.00 kW; the dongle reported each change within ~3 s | one run |
| It holds slightly under the cap on P023 | 942 and ~960 W against 1000 W; P020 held 0-3 % over | two runs |
| With the battery empty in normal operation, the cap does not cap the load | 0.10 kW cap, import ~395 W, the whole load | one run |
| An EMS forced charge wakes an inverter in low-SoC Standby | Starting after 2 min 1 s, charging after 3 min 30 s | one run; a 90 s watch saw nothing |
| So does the forced-charging schedule (33208-33219) | Starting 2 min 3 s after it was switched on, charging at 4099 W | one run |
| A forced charge does not need [13017](../entities/register-13017.md) to start it | run 5 woke with 13017 at 0x55 | one run |

Not measured: the cap against a scheduled charge (the charge started 2 s after the cap was
lifted). The engine refuses to run on an inverter in Standby, so it could not make these checks.
