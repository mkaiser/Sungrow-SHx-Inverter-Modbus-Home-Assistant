---
type: source
title: sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2.json
ingested: '2026-11-18'
created: '2026-11-18'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-01011-95-03
  - swo14
  - direct_lan
  - proxy
  - capability-test
  - third-party-battery
---

# SH10RT-20 on 01011.95.03, swo14's host inverter, 53 minutes later

A second diagnostics download of the same entry, read 2026-11-17 at 14:13 UTC, 53 minutes after
[the first](sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md).
It **carries the same two capability-test runs** (11:59 and 13:19 UTC) and the same probes,
features and connection verdict; what it adds is a second set of readings, taken while the car was
still charging. Source:
`device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2.json`.

Everything in the first reading's page holds here. What moved between the two:

| | First, 13:20 UTC | Second, 14:13 UTC |
| --- | --- | --- |
| PV | 268 W | 254 W |
| Load | 4303 W | 4353 W |
| Grid (export raw) | -4042 W | -4155 W |
| Battery level | 3.3 % | 3.3 % |
| Imported that day | 21.4 kWh | 24.3 kWh |
| Generated that day | 1.5 kWh | 1.8 kWh |
| Inverter temperature | 38.6 °C | 37.9 °C |

The house imported 2.9 kWh in 53 minutes against 0.3 kWh generated, with the battery pinned at
its floor: a car charging from the grid in November. The EV charger block reads the same
throughout -- mode "PV surplus", user current 16 A, charging false -- which is the inverter's own
view and not the charger's.
