# Auto repeat's spacing on hardware, at the maintainer's SH10RT, 2026-11-26

The dev instance (`make dev-real`, :8125, `config-real/`) against the maintainer's SH10RT on
SAPPHIRE-H_B001.V000.P020, cable, this tree's integration; `time_zone: Europe/Berlin` set, so the
instance's times are CET. The ledger kept from 2026-11-20 (37 of 55 then), not cleared. Production's
auto repeat was stopped before this (shortly after 13:28 CET, its last run's end), so production only polls. Read over the dev
instance's API. Times CET.

## Observations

**15:49:05** auto repeat armed by the maintainer (*Diagnosis: start*); the same second it started
run 1 (`runs_started` 1), for the export power limit, discharge windows away from now, an upper
bound and more. Battery 83 %, running state Running.

**15:51** run in progress (`running_since` 15:49:05): step "capability test: discharge windows
moved away from now"; summary 43/60 established, 12 runs kept; *Diagnosis: next attempt* `unknown`,
`waiting_for` "a run is in progress"; controls held by the test. Outcomes: 40 passed, 0 failed,
1 inconclusive, 5 not supported, 14 not run yet.

**15:51:51** run 1 over ("Polling resumed"), about 2 min 46 s after its start. It settled two
checks: 43 → 45 of 60 established.

**15:57:05** run 2 started, for the export power limit alone (`runs_started` 2, 13 runs kept):
**5 min 14 s after run 1 ended**, the short wait that follows a run that settled something. During
the run *Diagnosis: next attempt* stays `unknown` with `waiting_for` "running for export power
limit". Battery 81 %, Running.

Between the runs the coordinator lost the connection now and then (15:53:27, 15:54:07 with one
failed poll, recovered 15:54:16; 15:55:05) and the test's own reads twice during run 1 (15:50:59,
15:51:32): production Home Assistant polls the same inverter through its proxy, so two clients.

**15:58:52** run 2 over (1 min 47 s), **nothing settled**: 45 of 60 still, 14 runs kept. At once
*Diagnosis: next attempt* showed **16:28:52**, 30 min on (the first wait after a vain run), and the
step read "auto repeat: the next run at 16:28". The time showed as soon as the run ended.

**15:59:32** 46 of 60: a check settled between runs, by observation alone, with no run.

**16:04:04** run 3 started, for the export power limit **and the discharging start threshold**,
**5 min 12 s after run 2 ended and 24 min before the 16:28:52 that *next attempt* still showed**.
This is the one shortening a newly possible check grants (the discharging threshold was not in
run 2's list); *next attempt* did not move before the run: it went from 16:28:52 straight to
`unknown` at the start.

**16:05:41** run 3 over (1 min 37 s), nothing settled (46 still, 15 runs kept, `runs_started` 3).
*Next attempt* showed 16:28:52 again for an instant, then, the same second, **17:05:41: 60 min on**,
the second vain run's wait. Step "auto repeat: the next run at 17:05". Controls released, battery
80 %, Running, 0 failed.

**16:41** quiet since run 3: no run, no shortening, nothing newly settled (46 of 60, 15 runs,
`runs_started` 3); *next attempt* still 17:05:41, unchanged since 16:05:41. Battery 78 %, Running.

**17:06:04** run 4 started, for the export power limit and the discharging start threshold:
**23 s after the 17:05:41 *next attempt* had shown**, so the full 60 min wait was kept (the house
is looked at once a minute). `runs_started` 4.

**17:09:09** run 4 over (3 min 5 s). It **settled the export power limit**: 47 of 60, 16 runs
kept, 0 failed. *Next attempt* at once **17:14:09, 5 min on**; step "auto repeat: the next run at
17:14". Controls released; battery 73 %, Running (running state changed 17:09:16, 7 s after the
run).

**17:14:31** *next attempt* turned `unknown` (attribute still "the next run at 17:14"), 22 s past
its 17:14:09 and 33 s before the run actually started.

**17:15:04** run 5 started, for the discharging start threshold alone: **4 min 55 s after the
17:14:09 shown, 5 min 55 s after run 4 ended**. `runs_started` 5.

**17:16:35** run 5 over (1 min 31 s). It **settled the discharging start threshold**: 48 of 60,
17 runs, 0 failed. *Next attempt* at once **17:21:35, 5 min on**.

**17:22:04** at the time shown no run started: *next attempt* went `unknown` with `waiting_for`
"waiting for charge ceiling: the battery charging, above 55 %", and the step read "auto repeat:
waiting for charge ceiling: the battery charging, above 55 %". After sunset nothing left on the
list could run (battery 71 % and discharging), so the house decides, not the clock: the sensor is
unknown and says what for, as designed.

**17:32:42** stopped by the maintainer's word, through *Diagnosis: stop*, between runs (no run in
flight): the log reads "continuous capability testing stopped: stopped by the owner"; step
`finished`, controls not held, *next attempt* `unknown` with no `waiting_for`. 48 of 60, 17 runs,
`runs_started` 5. Battery 69 %.

## What the afternoon showed

| Gap | After | Wait seen | Rule |
| --- | --- | --- | --- |
| run 1 → 2 | run 1 settled 2 | 5 min 14 s | 5 min after a run that settled a check |
| run 2 → 3 | run 2 vain | 30 min shown, run after 5 min 12 s | 30 min after a vain run; once shortened by a newly possible check (discharging start threshold) |
| run 3 → 4 | run 3 vain | 60 min shown, run 23 s after it | 60 min after the second vain run |
| run 4 → 5 | run 4 settled 1 | 5 min shown, run 33 s after it | 5 min |
| after run 5 | run 5 settled 1 | 5 min shown, then `unknown` with the condition | nothing left that the house allows |

Not seen: a 30 min wait running out without a shortening, and the two SoC readbacks' 15 % rule. The
one display gap: while a shortening was coming, *next attempt* kept the later clock time (16:28:52)
until the run started at 16:04:04.
