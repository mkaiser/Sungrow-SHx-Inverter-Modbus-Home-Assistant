---
type: source
title: bar12-import-limit-schedule-2026-11-07.md
source_path: raw/bar12-import-limit-schedule-2026-11-07.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-32998, import-limit, forced-charging-schedule, standby, sh10rt-20, sapphire-h-b001-v000-p023, bar12, write]
---

# The site import limit against a scheduled charge, bar12, 2026-11-07

`.wiki/raw/bar12-import-limit-schedule-2026-11-07.md` records a watched write of
[register 32998](../entities/register-32998.md) during a charge commanded by the forced-charging
schedule (33208-33219), at [bar12](../entities/installation-bar12.md)'s
[SH10RT-20](../entities/device-sh-rt.md) on [P023](../entities/firmware-sapphire-h-b001-v000-p023.md),
over the cable, after dark. It closes the gap [the evening's runs](bar12-import-limit-2026-11-07-summary.md)
left, where the scheduled charge began only after the cap was lifted.

| Claim | Evidence | Status |
| --- | --- | --- |
| The cap holds a scheduled charge | 1.00 kW cap: a 4099 W charge cut to ~510-690 W, import 947-964 W | watched by this repository, one run |
| It settles within one sample, both ways | ~2 s down, ~3 s back up | one run |
| It follows the house load | load ~385 → ~215 W, charge ~512 → ~688 W, import at the cap | one run, one step |
| It holds 4-5 % under the cap on P023 | median 956 W against 1000 W | agrees with the EMS runs |
| The schedule wakes a low-SoC standby inverter | Starting after 2 min 1 s, charging after 3 min 30 s | agrees with the evening's schedule run |

Every word was restored and read back. Over the cable, so the dongle is not in it.
