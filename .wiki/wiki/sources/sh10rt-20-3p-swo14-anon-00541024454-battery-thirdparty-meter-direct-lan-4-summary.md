---
type: source
title: sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4.json
ingested: '2026-11-24'
created: '2026-11-24'
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

# SH10RT-20 on 01011.95.03, swo14's host, battery 92 %, the car charging

Read 2026-11-24 at 14:13 UTC, 35 minutes after the [reading without the car](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md),
from a Home Assistant diagnostics download on integration 0.1.0a54 (schema 29; the `diagnosis` section, committed unchanged, with no register dump or block read test). Posted to issue #786. Source: `device-diagnosis/results/inverter/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4.json`. It carries that document's run and one more, ended 14:11 UTC. The comment says
"slave/client" here too; the document is the host's.

| | |
| --- | --- |
| Installation | [swo14](../entities/installation-swo14.md), host |
| Firmware | [`SAPPHIRE-H_01011.95.03`](../entities/firmware-sapphire-h-01011-95-03.md) |
| Stand-in serial | `anon-00541024454` |
| At the time | PV 2352 W, load 4132 W, grid 0 W, battery discharging 1909 W at 92.2 % |

## The second run (outcome 3)

Established checks were skipped; nothing left changed.

- **Discharge windows: did as they were told**: 1726, 0, 1758.5 W, the first on this firmware.
- **Export limit: could not tell**, and not a repeat of the first run. Export, made by discharging 6920 W,
  went 3748, 3496.5, 3703 W. The run wrote the limit **divided by ten**: with the 13074 readback already
  established, the mode was not lifted before the scale was asked, so the scale was "not determined"
  though the first run had measured 1:1. The word was therefore 125, and this firmware stores that as 125 W. So
  the missing effect is against a 125 W limit, not 1250 W, and neither figure held.
- **The same shape at [fwitten](../entities/installation-fwitten.md)'s master** on P023: 5533.5, 4281.5,
  5813 W against 1250 W, its export made by discharging too
  ([its reading](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md)).
  Single inverters held the limit under a manufactured discharge (bar12, peter-sm).
- Forced-charging window: not measured, the house moved by 632 W on its own. Forced charge and 32998: battery too full.

## 13022 is signed here

At the first run's start [5214](../queries/is-battery-power-firmware-dependent.md) read -3171 W, the battery
charging (13001 = 147, bit 0x02), and **13022 read 62365, which is 65536 - 3171**. Discharging, both read 1909.
