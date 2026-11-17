# The maintainer's SH10RT: the first day of polls anywhere, 2026-11-18

Read at 00:39 CET (23:39 UTC) on 2026-11-18 out of the development instance's plausibility store,
written by *Extended test (auto repeat)* at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020), over
the inverter's own LAN port. The two readings checks that wait for **a day of polls** have reached
their minimum of 1440 -- the first time either has anywhere.

## What settled

After 1470 observations, from 2026-11-16T17:27:44Z to 2026-11-17T23:38:01Z, a span of 30 hours
with one restart of the polling instance in it:

| Check | Needs | Holds | Verdict |
| --- | --- | --- | --- |
| `lifetime counters never fall` | 1440 events | 1464 passes, no failure | passed |
| `running states` | 1440 polls | 1470 polls, four codes | passed |

**No lifetime counter ever fell.** 1464 judged steps from one poll to the next, across the eleven
counters in `TOTALS`, and not one of them went backwards. That covers a full day, a night, a
forced charge from the grid, five hours of low-SoC standby and a six-minute burst of lost
connections.

**Only four running-state codes appeared, and every one is in the table:**

```text
running states  {"seen": {"0x0008": 1013, "0x0040": 452, "0x8000": 4, "0x0020": 1}}
```

| Code | Name | Polls |
| --- | --- | --- |
| 0x0008 | Standby | 1013 |
| 0x0040 | Running | 452 |
| 0x8000 | Stop | 4 |
| 0x0020 | Starting | 1 |

`RunningStates.verdict` in `src/sungrow_modbus/capability_test/plausibility.py` makes an unknown
code the finding; there was none, so a day of polling this inverter produced nothing outside the
decode table. The counts also show how lopsided a November day is here: the inverter stood in
standby more than twice as long as it ran, and `Starting` was caught exactly once in 1470 polls --
a reminder that a transient state is seen by luck at a one-minute cadence, not by design.

## What this takes the house to

Two checks move from unanswered to established, so the ledger goes from **37 to 39 of 54**.

The entities do not show it. The summary sensor last reported at 16:00:04Z and still reads
`37/54` with `lifetime counters never fall: 1006 of 1440`: this instance predates the
`async_notify()` fix, so observing saves to the store without waking the sensors. **The store is
the record; the entities lag.**

## Still unanswered, and why

| Check | Waiting for |
| --- | --- |
| `battery level follows its power` | 1 of 2 events: a second kilowatt-hour through the battery |
| the four `daily_* against power` checks | kilowatt-hours of flow the house has not moved |
| the seven `total_* against daily_*` checks | 2 kWh on each daily counter |
| `daily counters reset at midnight` | nothing: it failed, on a clock |

An empty battery and a 1.6 kWh November day leave almost every energy check short of its trail.
