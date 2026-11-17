# The maintainer's SH10RT: a forced charge from the grid, 2026-11-17

A forced charge at `anon-37323352958` (SAPPHIRE-H_B001.V000.P020, third-party battery
configured as a Pylontech Force H1 14.4 kWh), over the inverter's own LAN port, from the
repository's dev Home Assistant, begun 08:39 local with the battery empty and the owner's leave.
Written as found, while the charge runs.

The charge was started by activating the *Battery Forced Charge* scene from `doc/scenes.md` and
then setting the forced charge power by hand (the scene does not carry it -- see below).

## The scene

Activating `scene.battery_forced_charge` set **both selects**: EMS mode to `forced` and the
battery command to `charge`, and the inverter went to "Running in compulsory (forced) mode". This
is what a scene pasted from the YAML package could not do.

**It moved no energy.** With the forced charge power at 0 W -- its factory value, and what a
capability test's restore leaves -- the battery stayed at 0 W for the full minute it was watched,
while the inverter reported forced mode. The charge began only once
`battery_forced_charge_discharge_power` was set to 4500 W by hand.

## The charge

Steady at **-4500 to -4502 W** for the whole run, the meter reading ~1620-1643 W on each of the
three phases (~4.9 kW imported).

| Minutes | SoC | Daily battery charge counter |
| --- | --- | --- |
| 0 | 0.0 % | 0.00 kWh |
| 9 | 3.3 % | 0.50 kWh |
| 18 | 8.8 % | 1.20 kWh |
| 28 | 13.3 % | 2.00 kWh |
| 30 | 14.4 % | 2.00 kWh |

- **The state of charge advances in steps of about 1.1 percentage points**, not the 0.1 % its
  register's scale suggests: the distinct readings were 0.0, 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7,
  8.8, 10.0, 11.1, 12.2, 13.3, 14.4, 15.5. On a 14.4 kWh pack a step is about 160 Wh, so the
  register's resolution is effectively one percent on this third-party battery. Anything that
  compares an SoC delta with an energy figure has to allow for that.
- **SoC and energy agree.** Thirty minutes at 4501 W is 2.25 kWh delivered; the SoC rose 14.4
  points, which on a 14.4 kWh pack is 2.07 kWh -- the difference is about what charging losses
  would cost.
- **The daily charge counter lags and jumps.** Register 13040 sits on the slowest (600 s) polling
  tier, so it stood at 0.00 kWh nine minutes into a 4.5 kW charge and then moved in steps of
  0.5-0.8 kWh rather than its 0.1 kWh resolution. Nothing is wrong with the register; it is the
  tier. It matters because the plausibility checks that want "three trails of 1 kWh" are fed from
  these polled readings, so their trails are necessarily coarse.

## The plausibility checks saw none of it

Thirty minutes of a 4.5 kW charge added **no** plausibility observations: *battery voltage times
current* still read "4 of 20 observations" throughout, and *battery level follows its power* "0 of
2 events".

The reason is in the code, not the hardware: `DiagnosisRunner.async_observe` is called from one
place only, `custom_components/sungrow_modbus/continuous.py`'s tick, so the readings reach the
plausibility checks **only while *Extended test (auto repeat)* is on**. It had been switched off
for the 13017 watch that morning and did not survive the Home Assistant restart that followed.

So the rarest condition of the day -- a battery moving kilowatts -- was not recorded, and a house
whose owner never turns auto repeat on never accumulates these observations at all, although they
write nothing and need only polled readings.

## How it ended

Forty-eight minutes, steady at -4500 to -4502 W throughout, stopped when the daily counter passed
3 kWh (it jumped to 3.50). Final state of charge **25.5 %**, from 0.0 %.

Returning the house was done by activating the *Self-Consumption Mode (max battery discharge)*
scene, which is also how the companion automation in `doc/scenes.md` was tested:

| Step | Result |
| --- | --- |
| scene activated | EMS mode `self_consumption`, battery command `stop`, first attempt |
| the automation's template | set `battery_max_discharging_power` to **7420.0 W** |
| settings put back by hand | max discharge 5000 W, forced charge power 0 W, read back |

- **`state_attr(number..., 'max')` renders a real figure on hardware**: 7420.0, not `None` and
  not 0. The automation pattern in `doc/scenes.md` works, which had never been seen on a device.
- **The derived battery ceiling moves with the battery's state.** The same `max` attribute read
  **7148 W** with the pack empty, **7420 W** at the moment the automation fired (~25 %), and
  **7318 W** a minute later. That is the designed behaviour -- the pack's own limit falls back to
  "what the BMS says it will take right now" (`src/sungrow_modbus/battery/power.py`) -- and it is
  the argument for the automation: a scene storing a fixed watt figure would be wrong at almost
  every moment, while reading the entity's `max` at activation gets the live one.

## The dev instance runs in UTC

`config-real/configuration.yaml` sets no `homeassistant: time_zone:`, so Home Assistant reports
`UTC` while the house and the container are on CET. Every time the integration displays is then
an hour behind: *Diagnosis: test summary* said "the next run not before 08:37" when the quiet
window actually ended at 09:37 local. Nothing is written wrongly -- the schedule registers carry
raw hour and minute -- but anything read off a dev instance's clock is an hour out, which is
worth knowing before it is mistaken for a bug in the slot schedule.
