---
type: source
title: mppt-energy-days-2026-11-26.md
source_path: raw/mppt-energy-days-2026-11-26.md
ingested: '2026-11-26'
created: '2026-11-26'
tags:
  - mkaiser
  - gerd
  - mppt-energy
  - home-assistant
---

# MPPT energy against Daily PV generation, six days at two houses

[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) and [gerd](../entities/installation-gerd.md)'s
SH8.0RT-V112 on [P022](../entities/firmware-sapphire-h-b001-v000-p022.md), both read over the cable (through a
modbus proxy) by each house's integration entry, 2026-11-21 to 2026-11-26. Source:
`raw/mppt-energy-days-2026-11-26.md`.

| Fact | Evidence |
| --- | --- |
| **The trackers' integrated energy came to 0.992 of *Daily PV generation* at mkaiser's over five whole days, and 0.985 at gerd's over six**; single days 0.978-0.994 and 0.970-0.995 | the recorder's history of *MPPTn energy* and 13002 |
| The integral adds nothing measurable over the polls: the polled *MPPTn power* integrated afresh gives the same day within 0.04 kWh | mkaiser's history |
| The shortfall is in V x I, not in the polling: the same house's 5017 (*Total DC power*), integrated the same way, lands within 0.1-0.4 % of 13002 every day, while V x I sits 0.8-1.4 % under 5017 | mkaiser's history, 5017 from the YAML package beside the entry |
| **13002 counts on the DC side**: it follows 5017's integral even on a day 31 kWh of it went to load and grid, where a 2 % conversion loss would show as 0.6 kWh | mkaiser, 2026-11-23 |
| 13002 is exactly *Daily direct energy consumption* + *Daily battery charge from PV* + *Daily exported energy from PV*, every day at both houses | the recorder's history of the four counters |
| No daytime update gap over 150 s in *MPPTn energy* on any day at mkaiser's | the entity's history |

## What it means

- On a cable at the default polling, *MPPTn energy* runs about 1-2 % under the inverter's own counter: right for
  comparing trackers, not a substitute for 13002 in the Energy dashboard.
- Both houses on the cable; a house through a WiNet-S, whose stale reads would change the integral rather than
  V x I, is still wanted. Why V x I falls short of 5017 (the current's 0.1 A step, or 5017 being computed from
  finer readings) is not established.
