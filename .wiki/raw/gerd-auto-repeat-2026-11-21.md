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
- Still open: a restore the firmware refuses because the owner's value is out of its range (10000 W on an
  8 kW model) still ends as exit 5 and a repair whose fix will fail the same way.
