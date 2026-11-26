---
type: source
title: mkaiser-t007-spacing-2026-11-26.md
source_path: raw/mkaiser-t007-spacing-2026-11-26.md
ingested: '2026-11-26'
created: '2026-11-26'
tags: [capability-test, auto-repeat, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# Auto repeat's spacing on hardware, mkaiser, 2026-11-26

`.wiki/raw/mkaiser-t007-spacing-2026-11-26.md`: [mkaiser](../entities/installation-mkaiser.md)'s lone
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md), the dev instance on
this tree, cable, an afternoon into dusk (15:49 to 17:32 CET, battery 83 % falling to 69 %). Five runs of
*Extended test (auto repeat)*, started on the ledger kept from 2026-11-20; production's auto repeat stopped,
its polling not. The question was the spacing of [the capability test](../concepts/capability-test.md)'s auto
repeat, not the checks: production had settled those on this firmware.

| Claim | Evidence | Status |
| --- | --- | --- |
| **5 min after a run that settled a check** | after run 1 (2 settled) the next started 5 min 14 s later; after runs 4 and 5 (1 each) *next attempt* showed end + 5 min at once, run 5 starting 33 s after it | established |
| **30 min after a vain run** | after run 2 *next attempt* showed end + 30 min (16:28:52) the moment the run ended | established, the wait itself cut short (next row) |
| **A newly possible check shortens it once** | the discharging start threshold, not in run 2's list, started run 3 at end + 5 min 12 s, 24 min before the time shown | established |
| **60 min after the second vain run** | run 3 vain: 17:05:41 shown, run 4 started 23 s after it | established |
| **The house decides once nothing is due** | after sunset, at run 5's 5 min, no run: *next attempt* `unknown`, `waiting_for` "charge ceiling: the battery charging, above 55 %" | established |
| *Next attempt* during a run | `unknown`, `waiting_for` "running for …" | as designed |
| The shown time and the shortening | *next attempt* kept 16:28:52 until run 3 started at 16:04:04; at run 3's end it showed the old 16:28:52 for an instant before 17:05:41 | **changed in the code** (below) |
| *Diagnosis: stop* between runs | log "stopped by the owner", step `finished`, controls not held, nothing in flight | as designed |
| Everything was put back | controls released after every run, 0 failed | |

Not seen: a 30 min wait running out without a shortening, and the two SoC readbacks' 15 % rule. Checks
went 43 → 48 of 60 on this instance's ledger. Between runs the connection dropped now and then (two
clients: production polled through its proxy), each time recovered within seconds.

Changed in the code because of it (`custom_components/sungrow_modbus/continuous.py`): while a check
that may shorten the wait is due, *next attempt* and the step name the earlier start; a run that has
ended but is not yet judged shows no time rather than the previous one.
