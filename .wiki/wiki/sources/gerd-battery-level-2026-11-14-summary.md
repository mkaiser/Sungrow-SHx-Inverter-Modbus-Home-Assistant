---
type: source
title: gerd-battery-level-2026-11-14.md
source_path: raw/gerd-battery-level-2026-11-14.md
ingested: '2026-11-14'
created: '2026-11-14'
tags: [register-13023, battery-level, soc, sbr096, gerd, read-only]
---

# gerd's battery level against the pack's own SoC, 2026-11-14

`.wiki/raw/gerd-battery-level-2026-11-14.md` records three read-only pairs at
[gerd](../entities/installation-gerd.md)'s [SBR096](../entities/device-sbr-battery.md) on a nearly
empty morning, through the WiNet-S, beside iSolarCloud's battery page and the maintainer's
statement of what the two readings mean.

| Claim | Evidence | Status |
| --- | --- | --- |
| The inverter's battery level ([13023](../entities/register-13023.md)) is the SoC within the window between minimum and maximum SoC | 1.5 % against (11.4 - 10) / 90 = 1.6 %; 2.5 % against 2.6 % | the maintainer's statement, two pairs |
| The pack's own SoC (10744) is the absolute charge iSolarCloud shows | 11.4 % at 09:05, the app 11.1 % at 09:01 | one pair |
| The scale is not in question | voltage, current, temperature and health agree between 13020-13025, 10741-10745 and the app | one reading |
| The battery was at its minimum, not below it | the pack at 11.4 % against a 10 % minimum after a night's discharge | one reading |
| Max SoC reads 100 %, where gerd's diagnoses until 2026-11-03 read 90 % | holding 13058 = 1000 | one reading; who changed it is unknown |
