---
type: source
title: mkaiser-stop-mid-run-2026-11-17.md
source_path: raw/mkaiser-stop-mid-run-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, restore, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# Diagnosis: stop pressed mid part B, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-stop-mid-run-2026-11-17.md` records the first time *Diagnosis: stop* was
pressed on hardware while a [capability test](../concepts/capability-test.md) was writing, at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) over the cable. Only the simulator had
seen it before. Stop was pressed 60 seconds into part B, during the forced charge probe, after
six settings had been written.

| Claim | Evidence | Status |
| --- | --- | --- |
| A stop mid part B runs [the restore](../concepts/capability-test-restore.md) to completion | step went `stopping, putting everything back` → `stopped` in 50 s | one run |
| Every touched setting goes back | 17 settings read back at their pre-run values, zero mismatches | one run |
| No restart starts | running state `Running` at the press and after the restore | one run |
| The snapshot store is dropped on a clean restore | no `sungrow_modbus.snapshot*` file remains; only the unrelated `preview_release` repair | one run |
| The owner's controls are released | *Diagnosis: controls held by test* `off` afterwards | one run |
| An interrupted run says so | outcome "ran, but checks were skipped or inconclusive", 0 findings, no error | one run |

Part B had reached `battery_max_charge_power` (700 W), `battery_max_discharge_power` (60 W),
`export_power_limit` (900 then 90 W), `battery_forced_charge_discharge_power` (40 W),
`battery_discharging_start_power` (30 W) and was mid `forced charge at 1250 W` when stop was
pressed, so the restore had real work to do rather than none.
