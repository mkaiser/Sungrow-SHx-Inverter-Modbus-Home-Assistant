---
type: source
title: fwitten-import-limit-engine-2026-11-22.md
source_path: raw/fwitten-import-limit-engine-2026-11-22.md
ingested: '2026-11-22'
created: '2026-11-22'
tags: [register-32998, import-limit, capability-test, sh10rt-v112, sapphire-h-b001-v000-p023, fwitten, cluster, write]
---

# The capability test's import limit check, fwitten's cluster master, 2026-11-22

`.wiki/raw/fwitten-import-limit-engine-2026-11-22.md` records the
[capability test](../concepts/capability-test.md)'s `--import-limit` check at
[fwitten](../entities/installation-fwitten.md)'s master [SH10RT-V112](../entities/device-sh-rt.md)
(`anon-86493117545`) on [P023](../entities/firmware-sapphire-h-b001-v000-p023.md), over the cable,
after dark, with the owner's Home Assistant polling. The master leads a cluster whose slave has no
battery.

| Claim | Evidence | Status |
| --- | --- | --- |
| [Register 32998](../entities/register-32998.md) **did not cap a forced charge here** | 1250 W forced charge, import 1715 W; cap 1090 W (word 109): import 1724 → 1718 → 1710 W, drift 14 W, "nothing measurable happened" | one run; contradicts [peter-sm](../entities/installation-peter-sm.md)'s two on the same model and firmware |
| The forced charge itself obeyed | the same run's forced charge check: 1250 W ±0 during | one run |
| The battery had room to give | SoC 15.2 % against a 7 % floor, PV 0 W | one run |
| 0 and 5001 are refused with 0x04, 5000 is taken | the check's word probe | as at mkaiser, swo14 and the others |
| Everything was put back | the report; 32998 = 2000 on master and slave read raw after it | one run |
| 13074 multiplies by ten here | the export-scale probe: the held 24990 written back refused with 0x04 | agrees with this house's earlier P023 readings |
| The battery power bounds are not enforced | 4960 W stored against a 4860 W maximum on 33047, 33048, 13052; 1010 W on 33149, 33150; 101 % refused on 13058 | one run |

Not established: whether word 109 read back during the cap (the report does not say), and why the
cap did nothing. Both houses where it failed, this one and [swo14](../entities/installation-swo14.md)'s,
are **cluster masters**; every house where it held is a single inverter. That is a pattern of two,
not a cause.

Over the cable, so the run says nothing about a WiNet-S.
