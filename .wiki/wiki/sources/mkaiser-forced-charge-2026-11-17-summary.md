---
type: source
title: mkaiser-forced-charge-2026-11-17.md
source_path: raw/mkaiser-forced-charge-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [battery, forced-charge, scenes, plausibility, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# A forced charge from the grid, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-forced-charge-2026-11-17.md` records a 48-minute forced charge from the grid at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) over the cable, started from the
*Battery Forced Charge* scene of `doc/scenes.md` and ended with the *Self-Consumption Mode*
scene, with the battery going from 0.0 % to 25.5 %.

| Claim | Evidence | Status |
| --- | --- | --- |
| A scene sets both selects, which a pasted one could not | EMS mode `forced` and battery command `charge`, inverter in "Running in compulsory (forced) mode" | one activation |
| The forced charge scene moves no energy by itself | charge power at its factory 0 W, battery flat at 0 W for the minute watched; the charge began only when the power was set by hand | one activation |
| `state_attr(number..., 'max')` renders on hardware | the companion automation set `battery_max_discharging_power` to 7420.0 W | one activation |
| The derived battery ceiling moves with the battery's state | the same `max` read 7148 W empty, 7420 W at ~25 %, 7318 W a minute later | three readings |
| The state of charge advances in ~1.1 point steps | distinct readings 0.0, 1.1, 2.2 ... 15.5; about 160 Wh per step on this pack | one charge |
| SoC and energy agree | 30 min at 4501 W is 2.25 kWh; the SoC rise implies 2.07 kWh | one charge |
| The daily charge counter lags its tier | register 13040 on the 600 s tier read 0.00 kWh nine minutes into a 4.5 kW charge, then moved in 0.5-0.8 kWh steps | one charge |
| The charge is steady | -4500 to -4502 W for 48 minutes, ~4.9 kW imported across three phases | one charge |

The ceiling reading is the argument for the automation rather than a fixed figure in the scene:
the pack's own limit falls back to what the BMS will take at that moment
(`src/sungrow_modbus/battery/power.py`), so a stored watt figure is wrong at almost every moment.

## The plausibility checks recorded none of it

Thirty minutes of a 4.5 kW charge added no observations at all -- *battery voltage times current*
stayed at "4 of 20" -- because the readings reach
[the plausibility checks](../concepts/capability-test.md) only through *Extended test (auto
repeat)*'s tick (`custom_components/sungrow_modbus/continuous.py`), which was switched off for
another test. A house whose owner never turns auto repeat on accumulates none of them, although
they write nothing.
