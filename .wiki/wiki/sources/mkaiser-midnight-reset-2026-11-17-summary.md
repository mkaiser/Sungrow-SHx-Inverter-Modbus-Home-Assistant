---
type: source
title: mkaiser-midnight-reset-2026-11-17.md
source_path: raw/mkaiser-midnight-reset-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, plausibility, energy-history, clock, sh10rt, sapphire-h-b001-v000-p020, mkaiser]
---

# The midnight-reset check fails on a clock, not on the inverter, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-midnight-reset-2026-11-17.md` records the first **failure** of a readings check
on hardware, at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), read out of the development instance's
plausibility store after 932 observations spanning 2026-11-16T17:27Z to 2026-11-17T14:40Z.

| Claim | Evidence | Status |
| --- | --- | --- |
| `daily counters reset at midnight` failed: `daily_pv_generation fell from 4.4 to 0 at 23:04` | the plausibility store, 0 passes and that one failure | measured |
| The development Home Assistant is on **UTC** | its `/api/config` reports `time_zone: UTC` | measured |
| The inverter's clock is an hour ahead of it | run 2's conditions: `inverter_clock: 2026-11-17T08:30:39` against `read_at` `2026-11-17T07:30:41Z` | measured |
| So the fall happened at **00:04 on the inverter's clock**, and the counter went to a clean `0` | the two above | derived |
| The check judges the fall by Home Assistant's local midnight, not the inverter's | `observe(values, dt_util.as_local(now))` in `custom_components/sungrow_modbus/diagnosis.py`; `_near_midnight` in `src/sungrow_modbus/capability_test/plausibility.py` spans 23:30 to 00:30 | the code |
| The clock needed to judge it correctly is already collected | `inverter_clock` sits in every run's `conditions` | the code |
| Everything else that answered, passed | `lifetime counters never fall` 926 passes and no failure; `battery level follows its power` 1; six ratio checks with ratios in hand | measured |

**The inverter is not at fault.** Its daily counters reset on its own clock, within minutes of its
own midnight, to zero. What failed is the comparison: the observation is stamped with the Home
Assistant instance's local time and the window is half an hour either side of *that* midnight, so
an hour of timezone difference puts a correct reset outside it.

This matters past the development container. Nothing requires a Home Assistant to share its
inverter's timezone, and an inverter whose clock has simply been set wrong is a real condition --
one worth reporting as itself rather than as a counter that misbehaves.

**The failure is sticky.** A readings check that has failed counts as answered, so auto repeat
will not wait for a second midnight to overturn it; the row stays as the house's one `1/54` until
the ledger is cleared or the check's revision is raised
([the capability test](../concepts/capability-test.md)).
