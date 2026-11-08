---
type: source
title: mkaiser-import-limit-discharge-2026-11-08.md
source_path: raw/mkaiser-import-limit-discharge-2026-11-08.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-32998, import-limit, battery, discharge-limit, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The site import limit against a lowered discharge limit, mkaiser, 2026-11-08

`.wiki/raw/mkaiser-import-limit-discharge-2026-11-08.md` records a watched write of
[register 32998](../entities/register-32998.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, after dark, in self-consumption, with the battery's discharge limit (33048) lowered
to about half the house's load.

| Claim | Evidence | Status |
| --- | --- | --- |
| The cap does not make the battery discharge past its limit | 33048 = 500 W: the battery gave 499 W at a 20.00 kW cap and at 0.05 kW | watched by this repository, one run |
| It does not cut the house load either | import ~700 W under a 0.05 kW cap, the load ~1.1 kW less the battery's 499 W | one run |
| The discharge limit holds by itself | at 500 W the battery gave 499 W within the first sample | one run |

So with the load above what the battery may give, the grid supplies the rest whatever the cap.
Restored and read back: 32998 = 2000, 33048 = 330.
