---
type: source
title: mkaiser-forced-startup-left-on-2026-11-17.md
source_path: raw/mkaiser-forced-startup-left-on-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [register-13017, forced-startup, standby, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# 13017 left on for 90 minutes, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-forced-startup-left-on-2026-11-17.md` records a watch of
[register 13017](../entities/register-13017.md) left at `0xAA` at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the cable, from a plain write of
the owner's switch rather than from the capability test. It answers whether the inverter undoes
the write by itself or when PV arrives (issue #444 reports ~20 minutes; at
[bar12](../entities/installation-bar12.md) it had not after 23). The register was read back throughout: the
running state is not evidence here, because this house wakes by itself at night
([2026-11-16](mkaiser-forced-startup-2026-11-16-summary.md)).

| Claim | Evidence | Status |
| --- | --- | --- |
| The inverter does not flip `0xAA` back by itself | 13017 read `0xAA` continuously for 90 min 48 s, from Standby with the battery at 0 % | one run, the longest watch on record |
| PV arriving does not flip it back | PV first above 0 W at 59 min 39 s; still `0xAA` 31 minutes later | one run, 31 minutes of PV |
| `0xAA` keeps the inverter running in the dark | 56 minutes of `Running` between the wake and the first PV, battery at 0 % throughout | one run |
| The wake timing repeats across nine days and three methods | `Starting` at 121, 123 and 122 s; `Running` at 215, 208 and 207 s | three runs |
| `0x55` ends it | written back at 90 min 55 s, reads off | one run |

So #444's flip-back is **not reproduced** on P020. What would still explain that report: other
firmware, or iSolarCloud rewriting the register at a house that is connected to it.

## The wake timing, three runs

| Run | How watched | to `Starting` | to `Running` |
| --- | --- | --- | --- |
| [2026-11-08](mkaiser-forced-startup-2026-11-08-summary.md) | one-off script | 121 s | 215 s |
| [2026-11-16](mkaiser-forced-startup-2026-11-16-summary.md) | the capability test engine | 123 s | 208 s |
| 2026-11-17 | this watch | 122 s | 207 s |

## The restore was late, and why

The watcher's restore was written to run in a `finally` block after 40 minutes. The Home Assistant
access token it held expired 29 minutes in, so all five restore attempts returned HTTP 401 and it
ended saying the register had been left on. It was put back by hand 50 minutes later and read back
off; no other register was touched. The lesson belongs with
[the restore](../concepts/capability-test-restore.md): **a restore that depends on a credential
which can expire mid-run is not a restore** -- the credential has to be obtained at the moment of
restoring, not held from the start.
