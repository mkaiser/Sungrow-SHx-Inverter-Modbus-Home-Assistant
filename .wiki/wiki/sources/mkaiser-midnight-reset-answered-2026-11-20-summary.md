---
type: source
title: mkaiser-midnight-reset-answered-2026-11-20.md
source_path: raw/mkaiser-midnight-reset-answered-2026-11-20.md
ingested: '2026-11-20'
created: '2026-11-20'
tags: [capability-test, plausibility, energy-history, clock, sh10rt, sapphire-h-b001-v000-p020, mkaiser]
---

# Eight daily counters reset in one poll, mkaiser, 2026-11-20

`.wiki/raw/mkaiser-midnight-reset-answered-2026-11-20.md` records the third night of observing at
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), the first on the corrected check, read
at 4337 observations. It answers what [the first night](mkaiser-midnight-reset-2026-11-17-summary.md)
and [the second](mkaiser-midnight-reset-night-2-2026-11-18-summary.md) could not: whether this
inverter zeroes its daily counters together.

| Claim | Evidence | Status |
| --- | --- | --- |
| **The reset is atomic on this device**: eight daily counters fell to 0 in the same one-minute poll | the check's note names `pv_generation` 4.9, `imported_energy` 12, `exported_energy` 0.2, `battery_charge` 1.8, `battery_discharge` 1.6, `exported_energy_from_pv` 0.2, `battery_charge_from_pv` 1.5 and `direct_energy_consumption` 3.2, each `->0` | measured, one reset |
| No counter was left standing after it | the same note ends "the rest at zero", and a standing counter above 0.5 kWh would be named | measured |
| The check passes where it failed three nights running | `{"passes": 1, "failures": [], "revision": 2}` | measured |
| It is judged on the inverter's clock, and names both where they differ | "reset at 00:09 by the inverter's clock, where Home Assistant read 23:09" | measured |
| The two earlier nights could not answer it | their sentences named only `daily_pv_generation`: the house had no other non-zero daily counter to lose | the two source pages |
| Raising a check's revision clears its row without touching the ledger | the restart dropped this check's state, revision 1 against 2, and left the other rows standing (`src/sungrow_modbus/capability_test/plausibility.py`) | measured |
| `lifetime battery counters contain each other` holds here: 175 passes, no failure | the same store; established for the first time anywhere | measured |
| `lifetime counters never fall`: 4330 passes, `running states`: five codes, all in the table | the same store | measured |
| A second night of auto repeat in low-SoC Standby starts **zero** runs | `continuous_runs_started` 0 from 21:30 to 00:25 CET, battery 0 %, *waiting for the inverter to run* | measured, two nights |

**The device comes out of this with a property worth stating.** An inverter that zeroed its eight
daily counters across several polls would make `daily_consumed_energy`, which adds five of them,
read a day's energy as a deep negative -- what the YAML package put in people's history
([#708](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/708),
[#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797)). This
one does not: one poll, eight counters, nothing standing. The clamp in
`src/sungrow_modbus/hybrid_inverter/derived.py` stays, because it is the floor under that sum at
every house, including the ones nobody has observed.

**What the night says about auto repeat** is the other half of the slot schedule, measured twice
now: in low-SoC Standby it starts nothing at all, correctly, and says so in *Diagnosis: current
step*. *Diagnosis: next attempt* stays `unknown` with the reason in its `waiting_for` attribute,
which is the wording still to settle ([the capability test](../concepts/capability-test.md)).
