---
type: source
title: mkaiser-charging-threshold-2026-11-17.md
source_path: raw/mkaiser-charging-threshold-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, battery, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The charging start threshold, settled, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-charging-threshold-2026-11-17.md` records the first time the charging start
threshold check has run anywhere, at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), in a run auto repeat started by itself
with the battery low and taking a trickle from a brightening sky. Its level read 10 %, which is
10 % of the **usable window** and about 19 % of the pack
([register 13023](../entities/register-13023.md)), not 10 % of the pack and not the floor.

| Claim | Evidence | Status |
| --- | --- | --- |
| The charging start threshold does what it says | commanded 1000 W; charging 230 W before, 0 W during, 309 W after; "the inverter did as it was told" | one run |
| The check needs PV, not a forced charge | it wants 200-800 W through the battery; a forced charge supplies kilowatts | two runs that skipped for this |
| The drift gate at low power is luck, not a wall | the discharging threshold failed at 216 W before / 0 during on drift; this one passed at 230 / 0 / 309 | two runs |
| Three V x I plausibility checks settle once the sky allows | battery, phase and tracker voltage times current all reached 20 observations; the tracker's had been stuck at 4 of 20 waiting for PV above 300 W, which reached 772 W | one afternoon |

## It corrects an earlier reading

[What a lived-in house costs the capability test](mkaiser-drift-gate-2026-11-17-summary.md)
reasoned that the two start thresholds might never settle at a house with people in it, because a
gently moving battery and a house quiet to within 150 W tend not to co-occur. **One of the two
has now settled**, with a before/after pair of 230 W and 309 W that stayed inside the gate. The
tension in that page is real -- it is why the discharging one is still open after several
attempts -- but it is a matter of catching the window rather than a wall. The claim there should
be read with this page beside it.
