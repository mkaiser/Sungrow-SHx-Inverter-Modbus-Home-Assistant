---
type: source
title: mkaiser-forced-startup-2026-11-08.md
source_path: raw/mkaiser-forced-startup-2026-11-08.md
ingested: '2026-11-08'
created: '2026-11-08'
tags: [register-13017, register-13059, forced-startup, standby, sh10rt, sapphire-h-b001-v000-p020, mkaiser, write]
---

# Forced startup under low SoC, mkaiser, 2026-11-08

`.wiki/raw/mkaiser-forced-startup-2026-11-08.md` records watched writes of
[register 13017](../entities/register-13017.md) at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on [P020](../entities/firmware-sapphire-h-b001-v000-p020.md),
over the cable, after dark, with the battery below its minimum SoC.

| Claim | Evidence | Status |
| --- | --- | --- |
| 0xAA wakes an inverter in low-SoC Standby, with no other command | Starting after 2 min 1 s, Running after 3 min 35 s, battery idle | watched by this repository, one run |
| It stays: 0xAA reads back and keeps the inverter running | 0xAA and Running for the 6 minutes watched | one run |
| 0x55 is off | Standby within ~21 s, read back 0x55 | one run |
| Only 0xAA and 0x55 are taken | 0x01 refused with exception 0x04; 0 refused the same morning | one write each |
| A minimum SoC raised above the battery's SoC charges it from the grid at its charge limit | 13059 = 50 % at ~28 %: 0x8000 (Stop), battery -4499 W (33047 = 4500 W), ~5.75 kW imported | one run |
| Lowering the minimum below the SoC does not wake a low-SoC Standby at once | 13059 = 10 % at 28.8 %: still Standby 90 s later | one run |

As at [bar12](bar12-forced-startup-2026-11-07-summary.md) on P023. 13017 is left at 0x55, off;
13059 is back at 10 %.
