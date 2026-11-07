---
type: source
title: mkaiser-import-limit-pv-2026-11-07.md
source_path: raw/mkaiser-import-limit-pv-2026-11-07.md
ingested: '2026-11-07'
created: '2026-11-07'
tags: [register-32998, import-limit, forced-charge, pv, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The site import limit with PV, mkaiser, 2026-11-07

`.wiki/raw/mkaiser-import-limit-pv-2026-11-07.md` records a watched write of
[register 32998](../entities/register-32998.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, with ~1.1 kW of PV, during a 4500 W forced charge through 13050 and 13051, and then
in self-consumption. It follows [the night run](mkaiser-import-limit-2026-11-07-summary.md).

| Claim | Evidence | Status |
| --- | --- | --- |
| The cap is on grid import alone, with PV counted | at 200 the battery took PV + 2.00 kW - load: ~1205 W at a 1810 W load, ~2396 W at 615 W | watched by this repository, one run |
| It follows a load step | the load fell from 1810 to 615 W during the cap, and import stayed at the cap within ~4 s | one run, one step |
| At 1 (0.01 kW) a forced charge draws only on PV | import ~15 W, battery charging at PV minus load | one run |
| It settles within ~4-6 s, both ways | 2 s samples, one sample in between | one run |
| It holds the cap slightly high | settled import 0-3 % above 2000 W | one run |
| 0 and 5001 are refused, 5000 accepted | exception 0x04 (server device failure) for both; 5000 read back 5000 | one run |
| In self-consumption with no import, 200 changes nothing | meter, battery and PV unchanged | one run; export not seen |

The run used a script outside the control test's engine, and it kept the engine's rules: the
stand-in was checked, the snapshot was flushed before the first write, and the restore wrote
raw words and checked them by raw read. Every word was restored. The run went over the cable,
so it says nothing about a WiNet-S.
