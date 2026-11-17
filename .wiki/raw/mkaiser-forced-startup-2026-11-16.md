# The maintainer's SH10RT: the forced startup mode (13017) on P020, 2026-11-16

The capability test engine's own forced startup mode (`forced_startup`), run from Home Assistant
on the maintainer's SH10RT (`anon-37323352958`, SAPPHIRE-H_B001.V000.P020, third-party battery),
over its own LAN port, unit 1, after 23:00 local time, in the dark. The engine's mode had never
run on an inverter before this; earlier starts were watched by one-off scripts. The owner gave
leave for the run.

Before the run, read from the entry's entities at 23:02:

| What | Reading |
| --- | --- |
| Running state (13000) | Standby |
| Battery level (13023) | 0.0 % |
| Battery minimum SoC (13058) | 10.0 % |
| PV (total DC power) | 0 W |
| Load (13008) | 1924 W |
| Export power | 0 W |
| EMS mode | self-consumption |
| Forced startup under low SoC (13017) | off |
| Forced charge/discharge | stop |
| Battery ceiling (derived) | 7148 W |

The house's Home Assistant (this checkout's dev instance, `config-real`) kept polling throughout;
reads lose the connection and are retried a few times an hour on this link.

The inverter had started on its own earlier the same evening with 13017 off, from the entry's
recorder history: `Starting` at 22:48:55, `Stop` at 22:50:20, `Running` at 22:54:00, back to
`Standby` at 22:54:15 -- a 15-second running window. Nothing was written to the inverter that
evening before this run.

## The run

Started at 23:16:12 local through the `sungrow_modbus.run_capability_test` action with
`forced_startup: true`. The integration paused polling for the run ("a diagnosis or capability
test has the link"), the owner's controls were held (*Diagnosis: controls held by test* on from
23:16:35), part A read 253 fields, and part B ran the forced startup check alone.

The engine's own record of the check, from the capability ledger
(`config-real/.storage/sungrow_modbus.capability_ledger.*`, firmware key
`ARM_SAPPHIRE-H_V11_V01_B|MDSP_SAPPHIRE-H_V11_V01_B`):

| Field | Value |
| --- | --- |
| check | forced startup under low SoC |
| observable | running state word |
| commanded | 170 (0xAA) |
| before | 8 (0x0008, Standby) |
| during | 64 (0x0040, Running) |
| after | 8 (Standby) |
| verdict | the inverter did as it was told |
| detail | left standby after 123 s; running after 208 s; back in standby 16 s after 0x55 |

Run conditions as the engine recorded them: `direct_connection: true`, model SH10RT,
`soc_percent: 0.0`, `pv_w: 0`, `battery_ceiling_w: 7144`, `simulated: false`, `dry_run: false`;
`forced_startup` and `forced_startup_control` both among the capabilities.

The running state as the entry's recorder saw it, which is the same wake from outside the engine:
`Standby` until 23:18:30, `Starting` 23:18:30, `Running` 23:19:56, `Standby` again by 23:20:11.

Restore: 13017's snapshot held 85 (0x55), the value the 2026-11-08 run left, and the register read
back 85 after the check -- "already holding its original value", 0 attempts needed, because the
check's own last write is 0x55. Nothing else was written: the plan was the forced startup probe
alone.

Outcome 0, "every planned check ran and every readback matched", 0 findings. The run finished at
23:20:06 local and polling resumed.

## Against the 2026-11-08 run at the same house

The same inverter, firmware and cable, watched that time by a one-off script rather than by the
engine:

| | 2026-11-08 (script) | 2026-11-16 (engine) |
| --- | --- | --- |
| left Standby | 2 min 1 s (121 s) | 123 s |
| Running | 3 min 35 s (215 s) | 208 s |
| back to Standby after 0x55 | ~21 s | 16 s |

## Part A's plausibility checks

The same run's part A brought the house's plausibility checks on: five matched -- power balance,
meter against export power, meter phases add up, daily_imported_energy against power, and
total_imported_energy against daily_imported_energy -- for 6 of 24 established with the forced
startup check. The rest wait on PV, battery movement or export, none of which a November night
with an empty battery offers.

## The inverter's own state that day

The battery read 0.0 % against a 10 % minimum all day; the house generated 4.4 kWh of PV against
23.7 kWh imported. *Inverter self consumption (estimated)* read -1.9 W while the inverter was in
Standby: in Standby the inverter reports 0 for PV, battery, export and AC power, so the estimate
collapses to the noise of the load term rather than showing the standby draw.
