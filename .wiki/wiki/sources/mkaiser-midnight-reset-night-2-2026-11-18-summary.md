---
type: source
title: mkaiser-midnight-reset-night-2-2026-11-18.md
source_path: raw/mkaiser-midnight-reset-night-2-2026-11-18.md
ingested: '2026-11-18'
created: '2026-11-18'
tags: [capability-test, plausibility, energy-history, clock, sh10rt, sapphire-h-b001-v000-p020, mkaiser]
---

# The midnight reset repeats, and so does the false failure, mkaiser, 2026-11-18

`.wiki/raw/mkaiser-midnight-reset-night-2-2026-11-18.md` records a second night of observing at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), read at 1440 observations, after
[the first night](mkaiser-midnight-reset-2026-11-17-summary.md) found the check failing on a clock.

| Claim | Evidence | Status |
| --- | --- | --- |
| The inverter reset its daily counters again, to a clean `0` | `daily_pv_generation fell from 1.6 to 0 at 23:03` beside the previous night's `4.4 to 0 at 23:04` | measured, two nights |
| Both resets fell within four minutes of the **inverter's own midnight** | 23:04 and 23:03 UTC are 00:04 and 00:03 CET; the inverter keeps German local time | derived |
| The false failure recurs every night, not once | two nights, two sentences, different daily totals | measured |
| A failed check keeps judging, and accumulates distinct failures | `EventCheck.observe` appends each new sentence and keeps the last five (`src/sungrow_modbus/capability_test/plausibility.py`) | the code |
| The verdict cannot recover once a failure is recorded | `verdict()` returns the failure whenever `failures` is non-empty, whatever `passes` reaches | the code |
| One midnight was always enough to decide it | the check's `minimum` is 1 | the code |

**The inverter comes out of this better, not worse.** Its daily counters resetting on time and to
zero is now measured on two consecutive nights, so it is a property of the device rather than one
night's reading.

**What the second night changes is the status of the defect.** The clock mismatch does not produce
an occasional artefact; it produces one failure per night, for as long as the Home Assistant
polling the inverter keeps a timezone an hour from the inverter's own. Each night's sentence
carries that day's kWh figure, so it is distinct and is appended rather than deduplicated: the row
grows until five are kept. Raising the check's revision clears the row, but it will refill nightly
until the clock itself is fixed ([the capability test](../concepts/capability-test.md)).
