# The maintainer's SH10RT: the midnight-reset check fails on a clock, not on the inverter, 2026-11-17

Read at 14:40 UTC on 2026-11-17 out of the development instance's plausibility store, written by
*Extended test (auto repeat)* at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020), over the
inverter's own LAN port. The run that produced it is not a run at all: the readings checks observe
between runs, and this one answered overnight.

## What the store holds

After 932 observations, from 2026-11-16T17:27:44Z to 2026-11-17T14:40:04Z, one readings check has
failed:

```text
daily counters reset at midnight   {"passes": 0,
                                    "failures": ["daily_pv_generation fell from 4.4 to 0 at 23:04"]}
```

That is the single `1/54` standing against this house. Everything else that has answered has
passed: `lifetime counters never fall` at 926 passes and no failure, `battery level follows its
power` at 1, and the six ratio checks (power balance, battery V*I, tracker V*I, phase V*I, meter
phases add up, meter against export power) all with ratios in hand.

## Why it is not the inverter

The time in that message is Home Assistant's, and this Home Assistant is on **UTC**:

- `/api/config` reports `time_zone: UTC`;
- the inverter's own clock is an hour ahead of it. The capability test records the clock it read
  in each run's conditions: run 2 recorded `inverter_clock: 2026-11-17T08:30:39` against a
  `read_at` of `2026-11-17T07:30:41Z`, two seconds short of exactly +01:00. The inverter is set to
  German local time; the development instance is not.

So `23:04` in that message is **00:04 on the inverter's own clock**, four minutes past its own
midnight, and the counter went to a clean `0`. On the inverter's clock this is a textbook pass.

## Where the clock enters the code

The observation is stamped with Home Assistant's local time and judged against it:

```text
self.plausibility.observe(values, dt_util.as_local(now))
```

(`custom_components/sungrow_modbus/diagnosis.py`), and the check's window is half an hour either
side of that local midnight:

```text
def _near_midnight(at: datetime) -> bool:
    minutes = at.hour * 60 + at.minute
    return minutes >= 23 * 60 + 30 or minutes <= 30
```

(`src/sungrow_modbus/capability_test/plausibility.py`). 23:04 falls outside both ends, so the fall
is reported as happening away from midnight. Judged on the inverter's clock, 00:04 is inside the
window and `now > 0.5` does not trip either.

## What this is evidence of

A daily counter resets on the **inverter's** clock, and nothing says that clock agrees with the
Home Assistant polling it. Here they are an hour apart and a correct reset is recorded as a
failure. The engine already reads the inverter's clock -- it is in each run's `conditions` as
`inverter_clock` -- so the information needed to judge this correctly is already collected; the
check does not use it.

The failure is also sticky: a readings check that has failed is an answer, so auto repeat will not
wait for a second midnight to overturn it, and the row stays at `1/54` until the ledger is cleared
or the check's revision is raised.

## Not evidence of

- Anything about this inverter's counters. They reset cleanly and on time.
- Anything about a house whose Home Assistant shares the inverter's timezone, which is the ordinary
  case and is what the maintainer's production instance does.
