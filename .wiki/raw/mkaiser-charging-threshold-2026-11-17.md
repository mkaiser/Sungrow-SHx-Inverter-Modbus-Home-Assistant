# The maintainer's SH10RT: the charging start threshold, settled, 2026-11-17

The charging start threshold check had never run on hardware anywhere: it needs a battery
charging a few hundred watts, which a forced charge cannot supply because it charges at
kilowatts. It settled at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020) at 11:37 local, in a run
auto repeat started by itself, with the battery at its 10 % floor taking a trickle from a
brightening sky.

From the capability ledger's sixth block:

| Field | Value |
| --- | --- |
| check | charging start threshold |
| commanded | 1000 W |
| before | 230.0 W |
| during | -0.0 W |
| after | 309.0 W |
| verdict | **the inverter did as it was told** |

So the battery was charging about 230 W from PV; the check raised the charging start threshold to
1000 W, above what was flowing; charging stopped; and when the threshold went back, charging
resumed at 309 W. That is the behaviour the YAML package's author predicted in a comment and
labelled a guess.

## Why it passed where the discharging one failed

Both thresholds want the same narrow window -- 200 to 800 W, all of it through the battery -- and
both are judged by a change that must be attributable, which fails if the house drifts more than
`max(150 W, 15 %)` across the measurement.

| Run | Check | before | during | after | Outcome |
| --- | --- | --- | --- | --- | --- |
| 09:40 | discharging start threshold | 216.5 W | 0.0 W | 0.0 W | could not tell: "the input drifted across the measurement" |
| 11:37 | charging start threshold | 230.0 W | -0.0 W | 309.0 W | the inverter did as it was told |

The two measurements are the same shape and nearly the same size. The difference is what the
house did meanwhile: the first drifted past the 150 W floor and the second did not.

**So the drift gate at low power is a matter of luck, not a wall.** An earlier note here reasoned
that the start thresholds might never settle at a lived-in house, because a gently moving battery
and a quiet house tend not to co-occur. One of the two has now settled, so the window is
reachable -- it just has to be caught. The discharging one is still open.

## Also settled the same hour

Three plausibility checks reached their twenty observations once auto repeat was running again and
the sky brightened: **battery voltage times current**, **phase voltage times current** and
**tracker voltage times current**, the last of which had been stuck at 4 of 20 waiting for PV
above 300 W. PV reached 772 W. The ledger stands at 36 of 54 established, 30 of them passed.
