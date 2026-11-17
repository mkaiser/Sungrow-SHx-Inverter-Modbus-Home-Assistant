---
type: source
title: mkaiser-discharging-threshold-2026-11-17.md
source_path: raw/mkaiser-discharging-threshold-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [capability-test, battery, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# The discharging start threshold, settled, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-discharging-threshold-2026-11-17.md` records the second of the two start
thresholds settling at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), an hour after
[the charging one](mkaiser-charging-threshold-2026-11-17-summary.md), in a run auto repeat
started by itself, with the battery reading 11 % of its usable window
([register 13023](../entities/register-13023.md)) and discharging a couple of hundred watts.

| Claim | Evidence | Status |
| --- | --- | --- |
| The discharging start threshold does what it says | commanded 1000 W; discharging 205 W before, 0 W during, 221 W after; "the inverter did as it was told" | one run |
| Both start thresholds are established on P020 | the charging one at 11:37, this one at 12:05 | two runs |
| The drift gate costs attempts, not results | the same check failed at 09:40 (216.5 / 0 / **0.0**) and passed at 12:05 (205.0 / 0 / **221.0**) | two attempts, one check, one day |
| The owner's ceiling holds across runs | `battery_ceiling_w = 5000` for the third consecutive run, against 7096-7274 before the option reached the test | three runs |

## It finishes the correction

[What a lived-in house costs the capability test](mkaiser-drift-gate-2026-11-17-summary.md)
reasoned that these two checks might never settle at a house with people in it. Both have now
settled, within three hours of each other, on the day that note was written. The same check
failing and then passing -- same register, same commanded value, same inverter, starting from
216.5 W and 205.0 W -- is the cleanest evidence available that the gate at low power costs
**attempts** rather than outcomes. What settles them is leaving auto repeat running so it keeps
trying, which is exactly what it is for.
