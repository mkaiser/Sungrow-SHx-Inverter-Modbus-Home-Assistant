---
type: source
title: mkaiser-day-of-polls-2026-11-18.md
source_path: raw/mkaiser-day-of-polls-2026-11-18.md
ingested: '2026-11-18'
created: '2026-11-18'
tags: [capability-test, plausibility, register-13000, sh10rt, sapphire-h-b001-v000-p020, mkaiser]
---

# The first day of polls anywhere, mkaiser, 2026-11-18

`.wiki/raw/mkaiser-day-of-polls-2026-11-18.md` records the two readings checks that wait for a day
of polls reaching their minimum at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) -- the first time either has anywhere.

| Claim | Evidence | Status |
| --- | --- | --- |
| `lifetime counters never fall` passed | 1464 judged steps across the eleven counters in `TOTALS`, no failure, against a minimum of 1440 | measured |
| `running states` passed | 1470 polls, four codes, none outside the decode table | measured |
| The codes seen are Standby 1013, Running 452, Stop 4, Starting 1 | the store's `seen` map | measured |
| An unknown code would have been the finding | `RunningStates.verdict` in `src/sungrow_modbus/capability_test/plausibility.py` | the code |
| This takes the house from 37 to 39 of 54 established | two checks moving from unanswered to passed | derived |

The span is 30 hours from 2026-11-16T17:27Z, taking in a full day, a night, a forced charge from
the grid, five hours of low-SoC standby and a six-minute burst of lost connections. **No lifetime
counter went backwards through any of it**, which is the first time that claim has been measured
over a day rather than inferred from a handful of runs.

The running-state counts say something about sampling as well as about the device: `Starting` was
caught **once in 1470 polls**. A transient state is seen by luck at a one-minute cadence, so the
absence of a code from such a listing is not evidence the inverter never entered it
([zero means absent](../concepts/zero-means-absent.md) makes the same point about a dongle's 0).

**The entities do not show the settle.** The summary sensor last reported at 16:00Z and still
reads `37/54`, because this instance predates the `async_notify()` fix and observing saves to the
store without waking the sensors. The store is the record.

What is still unanswered is mostly energy: an empty battery and a 1.6 kWh November day leave the
four `daily_* against power` checks and the seven `total_* against daily_*` checks short of their
trails, and `battery level follows its power` one kilowatt-hour short of its second event.
