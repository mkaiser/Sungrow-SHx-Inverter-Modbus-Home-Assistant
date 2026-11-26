---
type: source
title: mkaiser-mppt-energy-day-2026-11-21.md
source_path: raw/mkaiser-mppt-energy-day-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - mkaiser
  - mppt-energy
  - home-assistant
---

# MPPT energy against Daily PV generation, one day, 2026-11-21

[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), two trackers, read over the cable (through a
modbus proxy) by the production Home Assistant's integration entry. Source:
`raw/mkaiser-mppt-energy-day-2026-11-21.md`.

| Fact | Evidence |
| --- | --- |
| **Over one day the trackers' integrated energy came to 0.984 of *Daily PV generation***: 22.93 against 23.3 kWh, from 08:42 UTC | the recorder's history of the three entities |
| Hourly ratios scatter 0.88-1.04, because 13002 is read on a slow tier and steps by 0.1 kWh | 38 state changes of *Daily PV generation* in the day |
| No update gap over 3 min in the integral through two extended tests and an inverter restart | *MPPT1 energy*'s history |

## What it means

- On a cable at the default polling, the integral is within a couple of percent of the inverter's own
  counter over a day: good enough for comparing trackers, not a substitute for 13002 in the Energy
  dashboard.
- One day, one house, one transport. [Six days at two houses](mppt-energy-days-2026-11-26-summary.md)
  settle that 13002 counts DC, so there is no conversion loss in the comparison; a WiNet-S house, whose
  stale reads turn trapezoids into rectangles, is still wanted.
