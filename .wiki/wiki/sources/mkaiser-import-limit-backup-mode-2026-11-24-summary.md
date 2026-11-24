---
type: source
title: mkaiser-import-limit-backup-mode-2026-11-24.md
source_path: raw/mkaiser-import-limit-backup-mode-2026-11-24.md
ingested: '2026-11-24'
created: '2026-11-24'
tags: [register-32998, import-limit, backup-mode, forced-charge, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The import limit with backup mode on, mkaiser, 2026-11-24

`.wiki/raw/mkaiser-import-limit-backup-mode-2026-11-24.md`: [mkaiser](../entities/installation-mkaiser.md)'s lone [SH10RT](../entities/device-sh-rt.md)
over the cable, after dark, under a 2500 W forced charge.

| Claim | Evidence | Status |
| --- | --- | --- |
| **Backup mode does not stop [register 32998](../entities/register-32998.md) here** | 13075 = 0xAA: import 4656 / 3437 / 4698 W against 3460 W; off before and after: 4648 / 3478 / 4655 and 4699 / 3477 / 4698 W | three clean brackets, one house |
| 33000 follows 13075 | equal in every sample, on and off | |
| Everything was put back | the script's readback and a separate client's | |

Not established: the same on P023 or at fwitten, where backup mode is on and the cap fails.
