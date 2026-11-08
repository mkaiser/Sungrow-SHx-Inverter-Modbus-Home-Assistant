---
type: source
title: gerd-import-limit-schedule-2026-11-08.md
source_path: raw/gerd-import-limit-schedule-2026-11-08.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-32998, import-limit, forced-charging-schedule, sh80rt-v112, sapphire-h-b001-v000-p022, gerd, winet-s, write]
---

# The site import limit against a scheduled charge on P022, gerd, 2026-11-08

`.wiki/raw/gerd-import-limit-schedule-2026-11-08.md` records two runs of
[register 32998](../entities/register-32998.md) during a charge commanded by the forced-charging
schedule (33208-33219), at [gerd](../entities/installation-gerd.md)'s
[SH8.0RT-V112](../entities/device-sh-rt.md) on [P022](../entities/firmware-sapphire-h-b001-v000-p022.md),
written through the [WiNet-S](../entities/device-winet-s.md) because the cable was held by the
house's Home Assistant.

| Claim | Evidence | Status |
| --- | --- | --- |
| On P022 the cap holds a scheduled charge | charge 4399 → 862 W within ~7 s; the one complete sample under the cap: import 994 W against 1.00 kW | watched through the dongle, one run, one complete sample |
| A charge stops at the schedule's target SoC | run 1 stopped at a reported 4.4 % against a 5 % target, before the cap | one run |
| Through a WiNet-S, 33208 reads back current and 33210-33214 stale | 0xAA and 0x55 read back; 33210-33214 read 0 though the window took effect | one run; the cable confirmed the restore |
| The schedule starts a charge within ~10 s on a running inverter | battery -4399 W at the first sample | two runs |

The evidence through the dongle is behavioural only. The cable read both restores back: nothing
was left changed.
