---
type: source
title: mkaiser-t096-recheck-2026-11-26.md
source_path: raw/mkaiser-t096-recheck-2026-11-26.md
ingested: '2026-11-26'
created: '2026-11-26'
tags: [capability-test, forced-discharge, charge-ceiling, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The forced discharge and the charge ceiling again, mkaiser, 2026-11-26

`.wiki/raw/mkaiser-t096-recheck-2026-11-26.md`: [mkaiser](../entities/installation-mkaiser.md)'s lone
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md), production Home
Assistant on 0.1.0a57, Pylontech Force H1. On 2026-11-25 both checks had read "nothing measurable happened" after
passing on 2026-11-23; two runs with the established checks included asked again.

| Claim | Evidence | Status |
| --- | --- | --- |
| **The forced discharge acts**; the 2026-11-25 miss was the pack's own floor | run 16: -4499 / **1252** / -4498.5 W for 1250 W at 71 %; run 14: 1250-1251 W at 59 % (the judge: could not tell, cloud). The miss: 0 / 0 / 0 W at 8.8 %, with the pack at 0 W under a 2 kW load before any write; the same at 8.0 % and 10.0 % | established; the cause inferred from the recorder |
| **The charge ceiling acts** | run 16: 69 % under 71 % stopped a 4499 W charge, 4499 / **0** / 4499 W | established |
| The forced charge acts | run 16: 4499 / 1247 / 4499 W for 1250 W | established |
| The 2026-11-25 ceiling miss | 53.5 % under 55.5 % left a 4499 W charge running (MAD 0), where 53 % stopped the same charge on 2026-11-23 | **unexplained**, one miss in three |
| The pack keeps a floor above `battery_min_soc` | 13058 at 0 %, the battery idle under load at 8.0-10.0 % | one house, one pack |
| Everything was put back | 45 of 45 (run 14), 15 of 15 (run 16) | |

Under passing cloud (run 14) every power check was refused as inconclusive and the ceiling stood down before
writing, because the house moved 1004 W on its own; run 16 waited for two minutes with battery and load each
within 300 W. The ledger then took run 16's verdicts over the old ones, not as disputed.

Changed in the code because of it: a check asks a pack to discharge only above `DISCHARGE_SOC_FLOOR` (15 %) as
well as above `battery_min_soc` + 5 % (`src/sungrow_modbus/capability_test/procedure.py`).
