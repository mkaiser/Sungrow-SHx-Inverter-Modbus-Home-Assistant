# The maintainer's SH10RT: the midnight reset repeats, and so does the false failure, 2026-11-18

Read at 00:09 CET (23:09 UTC) on 2026-11-18 out of the development instance's plausibility store,
written by *Extended test (auto repeat)* at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020), over
the inverter's own LAN port. A second night of observing, after
`.wiki/raw/mkaiser-midnight-reset-2026-11-17.md` recorded the first.

## Two nights, the same minute

```text
daily counters reset at midnight
  {"passes": 0,
   "failures": ["daily_pv_generation fell from 4.4 to 0 at 23:04",
                "daily_pv_generation fell from 1.6 to 0 at 23:03"]}
```

| Night | Fell | Home Assistant's clock (UTC) | The inverter's clock (CET) |
| --- | --- | --- | --- |
| 16 -> 17 Nov | 4.4 -> 0 | 23:04 | 00:04 |
| 17 -> 18 Nov | 1.6 -> 0 | 23:03 | 00:03 |

Different days, different daily totals, the same minute of the inverter's own clock. The counter
went to a clean `0` both times.

## What the second night settles

**The inverter is well behaved, measured twice.** Its daily counters reset within four minutes of
its own midnight, to zero, on two consecutive nights. That is now a measured property of this
device rather than one night's reading.

**The false failure is systematic, not an accident.** It will recur every night for as long as the
Home Assistant polling this inverter keeps a timezone an hour from the inverter's own. Nothing
about it is particular to these two nights.

**The failure list grows.** `EventCheck.observe` in
`src/sungrow_modbus/capability_test/plausibility.py` keeps judging after a failure and appends each
*distinct* sentence, keeping the last five:

```text
if ok:
    self.passes += 1
elif sentence not in self.failures:
    self.failures.append(sentence)
    del self.failures[:-5]
```

Because the sentence carries the day's kWh figure, each night produces a new distinct sentence, so
the row accumulates one more every night until five are kept and the oldest is dropped. The verdict
cannot recover: `verdict()` returns the failure whenever `failures` is non-empty, whatever `passes`
reaches.

The check's `minimum` is 1 -- one midnight answers it -- so a single night was always enough to
decide it. The second night adds no new verdict; it adds the evidence that the first was not a
fluke.

## The rest of the store at the same reading

After 1440 observations, from 2026-11-16T17:27:44Z to 2026-11-17T23:08:01Z:

| Check | State |
| --- | --- |
| `lifetime counters never fall` | 1434 passes, no failure (needs 1440) |
| `running states` | 1440 seen: Standby 983, Running 452, Stop 4, Starting 1 (needs 1440) |
| `battery level follows its power` | 1 pass (needs 2) |
| `daily counters reset at midnight` | failed, twice over |

## Not evidence of

- Anything wrong with this inverter's counters.
- Anything about a house whose Home Assistant shares the inverter's timezone, where neither night
  would have failed.
