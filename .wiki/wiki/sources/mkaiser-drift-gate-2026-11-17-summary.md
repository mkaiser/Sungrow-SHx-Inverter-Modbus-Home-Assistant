---
type: source
title: mkaiser-drift-gate-2026-11-17.md
source_path: raw/mkaiser-drift-gate-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, plausibility, battery, sh10rt, sapphire-h-b001-v000-p020, mkaiser]
---

# What a lived-in house costs the capability test, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-drift-gate-2026-11-17.md` records why two behavioural checks were lost in runs
3 and 4 of auto repeat at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), on a dull day with the battery between
12 % and 25 %.

| Claim | Evidence | Status |
| --- | --- | --- |
| A behavioural check is refused when the house drifts more than `max(150 W, 15 %)` | `effects.py`'s drift gate, `DRIFT_ABS_W = 150.0`, `DRIFT_FRACTION = 0.15` | the code |
| The floor dominates at low power, and loses checks there | run 4's discharging start threshold: 216 W of drift against a ~206 W signal, tolerance the 150 W floor | one run |
| It also loses checks at high power | run 3's export power limit: 2126 W of drift | one run |
| The start-threshold checks need 200 to 800 W **through the battery** | run 3 "-4282 W"; run 4 "-206 W with -9 W past the battery" | two runs |

Refusing to attribute is the right answer -- an unattributable change is not evidence -- so this
is not a defect in the rule. What it says is **when** the rule bites: the quantity under test in
run 4 was about 206 W, so the tolerance was roughly three quarters of the signal, and one
household appliance switching on inside the window was enough.

**The conditions fight each other at a lived-in house.** A battery moves 200-800 W when PV is
weak, which is when household load is the largest thing on the meter and staying inside 150 W is
hardest. These two checks are therefore not waiting for one condition that has not come, but for
two that tend to exclude each other: a quiet house with a gently moving battery.

## What the same runs said they needed

Useful for planning a day's testing: the **forced discharge** wants a battery above its minimum
(12.2 % against a 10 % floor was "nothing to discharge"); the **charge ceiling** wants the battery
high enough that `battery_max_soc`, which cannot go below 50 %, can be put under it; the **export
power limit** wants something to spend on making an export; and the **`battery_min_soc` upper
bound** wants a floor well below the battery's level. The **forced charge** passed in run 4 --
"the inverter did as it was told".
