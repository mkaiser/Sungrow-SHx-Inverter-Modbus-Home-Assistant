---
type: source
title: sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-b001-v000-p023
  - bar12
  - winet
  - capability-test
---

# SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi, second reading

Read by the maintainer over a VPN on 2026-11-01 in the early afternoon, right after the
[cable reading](sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2-summary.md),
nothing else polling, with the full capability test on this tree's library. Source:
`device-diagnosis/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-2.json`.

| | |
| --- | --- |
| Installation | [bar12](../entities/installation-bar12.md) |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Battery firmware | `SBRBCU-S_22011.01.27` |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Transport | a [WiNet-S](../entities/device-winet-s.md) on WiFi; 6100 refused |
| Answered | 161 of 245 fields; 31 of 36 blocks: 2613, 2629 and the three [history](../concepts/energy-history.md) blocks refused every round; 13000, 5011 and 5115 dropped the connection in some rounds |

## Capability test

Outcome **3**. Through a WiNet-S only leg C is evidence: three readbacks reported the old word
(13058, 33047, 33048), the dongle's [stale readback](../entities/device-winet-s.md). See
[the capability test](../concepts/capability-test.md).

- [13074](../entities/register-13074.md): not asked; feed-in limitation was off.
- Behaviour, all did as they were told through the dongle: forced charge (1340, 1249, 1364 W),
  forced discharge (1251 W for 1250 W), the export limit (4174, 1285, 4074 W for 1250 W, export
  made by discharging 2930 W) and the **PV cut** (1587, 0, 1528 W).
- **Forced-charging window: could not tell.** Charge power 1216 W before, 4100 W during, and
  -1912 W ±1782 after: the battery swung into discharge once the window closed.
- Discharge window: not checked, the battery discharging only 426 W.
- Restart: stopped in 2.1 s, Running after 186.5 s.
