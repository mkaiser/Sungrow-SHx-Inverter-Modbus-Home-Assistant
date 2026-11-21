# gerd's own Home Assistant, 2026-11-21: the diagnosis in extended auto repeat

Raw note, written as found. The integration (0.1.0a46) on gerd's production Home Assistant, the inverter
entry through the modbus proxy on the inverter's own LAN port (a cable path), the wallbox entry over TLS;
both entries with *Diagnosis: mode* set to extended auto repeat by the maintainer. Watched read-only from
the devcontainer's tunnel through Home Assistant's API. Times are CET unless marked UTC. No address,
serial or lifetime figure is in this note.

## Run 1 (09:07-09:20)

- SH8.0RT-V112, `SAPPHIRE-H_B001.V000.P022`, SBR096 at 2.8 % against a 10 % floor, about 0.85 kW of PV,
  EMS self-consumption.
- 55 checks: 23 passed, 0 failed, 0 inconclusive, 5 not supported, 27 not run yet (most wait for a battery
  with charge in it, flowing kilowatt-hours or a midnight).
- **The five "not supported" are upper bounds the firmware does not enforce**: one step past the maximum
  was stored at `battery_max_charge_power`, `battery_max_discharge_power`,
  `battery_forced_charge_discharge_power`, `battery_charging_start_power` and
  `battery_discharging_start_power` (33047, 33048, 13052, 33149, 33150). The same five stored it on
  peter-sm's P023; P022 joins it. `battery_max_soc`'s upper bound was refused (passed).
- **The run ended with exit 5**: "something was not restored, or the inverter may still be stopped".
  Home Assistant's history of every control, before (08:30) and after: all back where they were except
  **`battery_forced_charge_discharge_power` (13052): 10000 W before, 20 W written at 09:08:22, and 4960 W
  from 09:17:02 on**. The entity's live maximum is 4860 W, so 4960 is exactly the upper-bound probe's
  value (maximum + 100 W step): the probe's write was stored, and the write back to the owner's 10000 W
  did not take. The inverter was running (13000 0x0040) and no other control moved.
- What it costs the house: nothing measurable now. 13052 acts only in forced mode, the house is in
  self-consumption, and 10000 W was already above what the battery accepts.
- **No repair was raised.** The integration keeps the snapshot on a failed restore and turns it into a
  repair only at the next setup (`_async_raise_leftover`); during the session the only trace is the log
  line and the summary's exit 5.
- **Auto repeat goes on after an exit 5**, and the next run's `keep()` saves its own snapshot over the
  kept one, so the test's 4960 W becomes "the owner's value" and the 10000 W leaves the store. Run 2 was
  due at 09:37; pressing Stop from here was not possible in time.

## Run 2 (09:37-09:39)

- Short (skip completed tests on): exit 3. `battery voltage times current` passed (24/55),
  `charging start threshold` inconclusive ("the house was 306 W different afterwards"). 13052 not touched.
  The export limit's write scale was not asked: feed-in limitation is off (13087 holds 0x55), and then
  13074 ignores every write without an exception.

## 13052 put back by hand (09:40-09:41), with the maintainer's leave

Written through the proxy on the cable path, one session, EMS mode 0 (self-consumption) checked first,
13000 0x0040 (running). Each write read back after 2 s and 10 s.

| Written | Answer | 13052 after |
| --- | --- | --- |
| 10000 | exception 4 (function 0x86) | 4960, unchanged |
| 8000 | stored | 8000 |
| 9000 | exception 4 | 8000 |
| 8100 | exception 4 | 8000 |

- **13052's hard limit is the inverter's rated power**: 8000 W on this SH8.0RT (an SH10RT's is
  10000 W, the maintainer confirms). Above it the inverter refuses with exception 4; at or under it, it
  stores. The battery-derived maximum the integration shows (4860 W) is **not** that limit: one step over
  it (4960) was stored.
- So run 1's exit 5 was a restore the firmware cannot do: the owner's 10000 W, held before the
  integration first wrote anything (read 09:07:32), is above what P022 accepts on an 8 kW model. Some
  other path stored it (iSolarCloud, the YAML package, an older firmware: not known).
- Left at **8000 W**, the nearest value it accepts; with the house in self-consumption it acts on
  nothing, and as a forced power it means the same as 10000 (both above what the battery takes).

## What changes in the integration because of run 1

- A capability run now **refuses to start while a snapshot from an earlier run is kept**: it raises the
  repair, writes nothing, and leaves the kept snapshot as it was (`UnfinishedRestoreError`). Before, the
  next run saved its own snapshot over it, which is what made the test's 4960 W "the owner's" here.
- A run that could not put something back **raises the repair at once**, not only at the next setup.
- **Auto repeat stops** after such a run, or when a run is refused over a kept snapshot, with "a run could
  not put everything back; see Settings -> Repairs, then start again".
- **A control whose own value lies outside its bounds is written back to itself before the run touches
  it** (library, preflight). Refused, as 13052's 10000 W would be here, the control is left out of the
  run with "not written: the house's own value is one the device does not take back now", every later
  write of it is refused before it reaches the wire, and the forced checks and the manufactured export,
  which command through it, are skipped. Taken (8000 W here), the run goes on as before. Through a
  dongle such a control is left out without asking, since its write cannot be checked.

## Run 3 (10:07-10:08)

- Exit 0, every planned check ran and every readback matched. With the battery at 13.3 % (floor 10 %),
  `battery_min_soc` and `battery_reserved_soc_for_backup` read back their probes: 26/55 passed, 31/55
  established, 0 failed. 13052 untouched, still 8000 W.

## Run 4 (10:37-10:43): the discharge window marked "not supported", wrongly

- 27/55 passed (`phase voltage times current` added), 3 inconclusive (forced discharge and export power
  limit, each "the house was 179 W / 1001 W different afterwards"; the charging start threshold), 6 not
  supported: **`discharge windows away from now`, "nothing measurable happened"**, against this same
  inverter's cable diagnosis, where moving the windows stopped a 3799 W discharge to 0 W.
- The run's own numbers (diagnostics download): battery discharge power before **-549.5 W**, during
  -617.5 W, after -544 W. Negative is charging: there was no discharge to stop. The precheck had sampled
  1339 W of discharge, the tail of the run's own manufactured export (the pack accepted 3220 W of a 3224 W
  ask) moments before.
- **A procedure bug, not a finding**: the stop verdict compared `abs(before)` with its floor, so 550 W of
  charge counted as 550 W of discharge to stop, and "carried on at -618 W" came out as the windows being
  ignored. Fixed (signed comparison, both the bracketed-stop branch and the floor); a replay of these
  numbers now reads "nothing to stop".
- The wrong `NO_EFFECT` is in gerd's ledger now and counts as established, so auto repeat will not ask
  again on this firmware until the runs are cleared (*Diagnosis: tests: clear history*) or the fix is
  installed and the history cleared. Readings history is unaffected.
- Run 4's other numbers: forced discharge commanded 1250 W read before -448, during 816, after -627 W
  (drift); the export limit at 1250 W held export at 1248 W during, from 3006 W before and 2005 W after
  (drift 1001 W, so "could not tell", though the during figure sits on the cap). 13087 feed-in limitation
  off (0x55), so the export limit's write scale was again not asked. Inverter clock 10:40:36 at 09:40 UTC:
  CET, as known.

## Runs 5-7 (11:07, 11:37-11:51, 12:15)

- Run 5: exit 0, nothing new (battery 14 %, floor 10 %). Auto repeat then waited on conditions, not slots.
- **Run 6 (battery 22 %): forced discharge and the export power limit confirmed.** Forced discharge
  commanded 1250 W: discharge -788 W before, **1251 W** during, -752.5 W after (ratio 1.0008). Export limit
  at 1250 W, export made by a manufactured 3280 W discharge (asked 3281 W): export 3973.5 W before,
  **1243 W** during, 3437.5 W after (ratio 0.994). The cap went in as the feed-in ratio, 100 % to 15.6 %
  (1250 of 8000 W rated); 13074's write scale was still not asked, since 13087 holds 0x55 (off).
- Run 7: exit 0, nothing new. `daily_pv_generation against power` passed on the readings side.
- At 12:32: 30/55 passed, 36/55 established, 0 failed; battery 27.6 %.

## Run 8 (12:37-12:39)

- **The charging start threshold (33149) confirmed**: raised to 1000 W over a 660 W charge, charge power
  went to 0 W and came back to 683 W. Exit 0. `battery level follows its power` passed on the readings
  side. 32/55 passed, 38/55 established, 0 inconclusive, battery 36 %.

## Readings at 14:02, run 9 (14:37-14:39)

- 14:02: `daily_battery_charge against power` and `total_pv_generation against daily_pv_generation`
  passed on the readings side (34/55).
- **Run 9, battery about 56 %: the charge ceiling confirmed.** `battery_max_soc` lowered to 53.2 %, under
  the battery: a 2069.5 W charge went to 0 W and came back to 1980 W. Exit 0. 35/55 passed, 41/55
  established, 0 failed.
- **Run 10 (15:07): the upper bound of `battery_min_soc` (13059) is enforced**: one step past its maximum
  was refused, with the battery at 57 % well above the probed floor. With `battery_max_soc`'s, refused in
  run 1, the two SoC limits enforce their bounds on P022 while the five power limits do not, the same
  split as peter-sm's P023. Exit 0; 36/55 passed, 42/55 established, 0 failed.

## Stopped (15:25)

- Auto repeat stopped on the maintainer's word with *Diagnosis: stop*, between runs (none in flight;
  the controls were not held). Left: 13 checks, all readings-side or the discharging start threshold
  (needs the battery discharging 200-800 W through itself). The wallbox entry's auto repeat still waits
  for a car.
- Readings after the stop, to 17:45: `daily_battery_discharge against power` passed as the battery
  discharged into the evening (37/55 passed, 43/55 established). The watch ended at 17:45 with the
  tunnel taken down; 13052 left at 8000 W.
