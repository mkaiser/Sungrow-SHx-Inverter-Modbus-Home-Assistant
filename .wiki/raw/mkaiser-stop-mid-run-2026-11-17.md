# The maintainer's SH10RT: Diagnosis: stop pressed mid part B, 2026-11-17

Until now only the simulator had seen *Diagnosis: stop* pressed while a capability test was
writing. This is the first run on hardware, at `anon-37323352958`
(SAPPHIRE-H_B001.V000.P020), over the inverter's own LAN port, from the repository's dev Home
Assistant. The owner gave leave for the run.

Before: the inverter `Running`, battery at 0.0 %, PV ~200 W, every control at the value the
previous night's run left. The run was started with the `sungrow_modbus.run_capability_test`
action (no `forced_startup`), and stop was pressed 60 seconds after part B began.

## What happened

| Time | Step |
| --- | --- |
| 08:28:41 | run requested; `block read test, round 1 of 3: realtime_input` |
| 08:28:46 | `reading raw registers: the 26xx firmware strings (3 of 77)` |
| 08:28:51 | part B begins: `capability test: reading the inverter` |
| 08:28:56 | `battery_max_charge_power, writing 700 W` |
| 08:29:01 | `battery_max_discharge_power, second point 60 W` |
| 08:29:06 | `export_power_limit, writing 900 W` |
| 08:29:11 | `export_power_limit, second point 90 W` |
| 08:29:16 | `battery_forced_charge_discharge_power, second point 40 W` |
| 08:29:21 | `battery_discharging_start_power, writing 30 W` |
| 08:29:26 | `forced charge at 1250 W` |
| 08:29:51 | **stop pressed**, mid forced charge; running state `Running` |
| 08:29:56 | `capability test: stopping, putting everything back` |
| 08:30:46 | `stopped` |

So the restore took about 50 seconds for the six settings part B had reached.

## What it settles

- **The restore runs on a stop and completes.** Every one of 17 settings read back at its
  pre-run value, checked against the values the previous night's run recorded: battery max
  charge 4500 W and max discharge 5000 W, charging start 200 W, discharging start 100 W, forced
  charge/discharge power 0 W, feed-in limit 10000 W, max SoC 100 %, min SoC 10 %, forced charging
  target SoC 100 %, EMS mode self-consumption, forced charge/discharge stop, forced startup off,
  feed-in limit mode off, forced charging days every day, forced charging schedule off, and both
  forced charging times. **Zero mismatches.**
- **No restart starts.** The running state read `Running` at the press and `Running` after the
  restore; nothing restarted the inverter.
- **The snapshot store is dropped.** No `sungrow_modbus.snapshot*` file remains in the config
  directory, which is the integration's own signal of a clean restore; only the unrelated
  `preview_release` repair is registered.
- **The owner's controls are released.** *Diagnosis: controls held by test* read `off` afterwards.
- The run reported outcome "ran, but checks were skipped or inconclusive" with 0 findings and no
  error, which is what a deliberately interrupted run should say.
