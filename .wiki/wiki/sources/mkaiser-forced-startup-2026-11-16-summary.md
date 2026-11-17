---
type: source
title: mkaiser-forced-startup-2026-11-16.md
source_path: raw/mkaiser-forced-startup-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags: [register-13017, forced-startup, standby, capability-test, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The capability test's forced startup mode, mkaiser, 2026-11-16

`.wiki/raw/mkaiser-forced-startup-2026-11-16.md` records the **first run of the capability test
engine's own forced startup mode** on an inverter, at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the cable, from Home Assistant
through the `run_capability_test` action with `forced_startup: true`, at 23:16-23:20 local, in the
dark with the battery at 0.0 % against its 10 % minimum. Earlier starts at this house and at
[bar12](../entities/installation-bar12.md) were watched by one-off scripts
([2026-11-08](mkaiser-forced-startup-2026-11-08-summary.md),
[2026-11-07](bar12-forced-startup-2026-11-07-summary.md)).

| Claim | Evidence | Status |
| --- | --- | --- |
| The engine's forced startup mode does on hardware what it does on the simulator | verdict "the inverter did as it was told", outcome 0, 0 findings | first run on hardware |
| The guard admits low-SoC Standby and nothing else is needed | conditions `soc_percent: 0.0`, `pv_w: 0`, running state 0x0008; the run was neither refused nor deferred | one run |
| 0xAA wakes the inverter from low-SoC Standby | before 0x0008, during 0x0040; left standby after 123 s, Running after 208 s | one run |
| 0x55 sends it back | after 0x0008, back in standby 16 s after 0x55 | one run |
| The wake timing repeats at one house | 123 s / 208 s / 16 s against 121 s / 215 s / ~21 s eight days earlier, same inverter, firmware and cable | two runs |
| The restore has nothing to put back | the snapshot held 85 (0x55), the register read back 85, "already holding its original value", 0 attempts | one run |
| Part B wrote the one probe and no other | the plan was the forced startup probe alone; `restored` carries only `forced_startup_under_low_soc_raw` | one run |

The snapshot's original was `0x55` and not the factory 0 the diagnoses read on B001 firmware,
because the 2026-11-08 run left it there: once a run has written 13017, the register holds `0x55`
at that house ([the restore](../concepts/capability-test-restore.md)).

## The same evening, unprompted

From the entry's recorder, with 13017 at `0x55` and nothing written to the inverter that evening:
`Starting` at 22:48:55, `Stop` at 22:50:20, `Running` at 22:54:00, `Standby` again at 22:54:15 --
a fifteen-second running window the house took by itself, 22 minutes before the run. So an
inverter in low-SoC Standby here does stir at night without 13017, which bears on the report of
`0xAA` being flipped back by itself (issue #444): a state change after a write at this house is
not on its own evidence that the register was undone.

## Part A, the same run

Part A read 253 fields and brought five [plausibility](../concepts/capability-test.md) checks to a
match -- power balance, meter against export power, meter phases add up, daily_imported_energy
against power, total_imported_energy against daily_imported_energy -- 6 of 24 established with the
forced startup check. The other eighteen wait on PV, battery movement or export.

*Inverter self consumption (estimated)* read -1.9 W with the inverter in Standby: the inverter
reports 0 for PV, battery, export and AC power there, so the estimate collapses rather than
showing the standby draw.
