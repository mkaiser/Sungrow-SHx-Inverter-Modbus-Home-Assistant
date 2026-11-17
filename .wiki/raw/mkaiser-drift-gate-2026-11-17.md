# The maintainer's SH10RT: what a lived-in house costs the capability test, 2026-11-17

From runs 3 and 4 of *Extended test (auto repeat)* at `anon-37323352958`
(SAPPHIRE-H_B001.V000.P020), over the inverter's own LAN port, on a dull November day with the
battery between 12 % and 25 %.

Both runs lost a behavioural check to the same rule, and the reason is worth recording because it
is about houses, not about this inverter.

## The rule

A behavioural check compares the house before, during and after a write. Before anything else is
asked, it asks whether the house drifted (`src/sungrow_modbus/capability_test/effects.py`):

```text
if drift > max(DRIFT_ABS_W, DRIFT_FRACTION * abs(before_mid)):
    ... "not measured -- the house was {drift} W different afterwards,
         so the change cannot be attributed to the setting"
```

with `DRIFT_ABS_W = 150.0` and `DRIFT_FRACTION = 0.15`
(`src/sungrow_modbus/capability_test/procedure.py`). So the tolerance is 150 W, or 15 % of the
quantity being measured once that exceeds 1000 W.

Answering `INCONCLUSIVE` rather than a verdict is right: a change that cannot be attributed is not
evidence. What is worth noticing is **when** that happens.

## What it cost

| Run | Check | Drift | Tolerance | Outcome |
| --- | --- | --- | --- | --- |
| 3 | export power limit | 2126 W | 15 % of a multi-kW baseline | not measured |
| 4 | discharging start threshold | 216 W | 150 W, the floor | not measured |

Run 4's is the instructive one. The quantity under test was a battery flow of about **206 W**, so
the tolerance was the 150 W floor -- roughly **three quarters of the signal itself**. An ordinary
household load switching on inside the measurement window is then enough to lose the check, and
at a lived-in house that is not a rare event.

## Why the conditions fight each other here

The two start-threshold checks need the battery moving **200 to 800 W, all of it through the
battery** (run 3: "battery charge power was -4282 W"; run 4: "-206 W with -9 W past the
battery"). A battery moves that gently when PV is weak -- which is exactly when household load is
the largest thing on the meter and the 150 W floor is hardest to stay inside.

So these two checks are not merely waiting for a condition that has not come; at a house with
people in it they are waiting for two conditions that tend to exclude each other. A quiet house
with a gently moving battery is the combination to catch.

## Other reasons the same runs gave

Each names what it needs, which is the useful part for planning:

- **forced discharge**: "the battery is at or near its minimum state of charge, so there is
  nothing to discharge" (12.2 % against a 10 % floor).
- **charge ceiling**: "the battery is too low for the ceiling to be put under it, since
  battery_max_soc cannot go below 50 %".
- **export power limit**: "could not make the house export: the battery is at 12.2 % against a
  floor of 10 %, so there is nothing to spend on making one".
- **upper bound of battery_min_soc**: "51 % is not well below the battery's level, and a floor
  raised past it would charge from the grid".
- **restart**: "an earlier run measured it already".

What did pass in run 4: **the forced charge** -- "the inverter did as it was told".
