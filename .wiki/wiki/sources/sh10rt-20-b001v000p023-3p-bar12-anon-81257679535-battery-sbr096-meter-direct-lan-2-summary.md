---
type: source
title: sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - diagnosis
  - sh10rt-20
  - sapphire-h-b001-v000-p023
  - bar12
  - direct_lan
  - capability-test
---

# SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port, second reading

Read by the maintainer over a VPN on 2026-11-01 in the early afternoon, nothing else polling, with
the full capability test on this tree's library (timed windows included). Source:
`device-diagnosis/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Installation | [bar12](../entities/installation-bar12.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md), version 1 `SAPPHIRE-H_01011.95.14` |
| Transport | the inverter's own LAN port; 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md), SoC 48.6 % |
| Answered | 240 of 245 fields; 36 of 36 blocks, nothing intermittent |

## Energy history

The whole block answered, and each 2026 yearly slot equals the sum of its months exactly: PV
10684.5 kWh, direct consumption 1396.5 kWh, export from PV 8235.8 kWh. Slots from 2024 on are
non-zero. See [energy history](../concepts/energy-history.md).

Register 32998 reads 2000.

## Capability test

Outcome **3**, 9 of 9 readbacks matched. See [the capability test](../concepts/capability-test.md).

- [13074](../entities/register-13074.md): the probe was refused three times, **times ten**; 600 W
  went out as raw 600.
- Behaviour: forced charge did as it was told (1279, 1249, 1155 W); the **PV cut** did as it was
  told (1342, 0, 1286 W); the export limit could not tell (3939, 1246, 3173 W for 1250 W, the
  house moving 766 W afterwards).
- **The house would not hold still**: the battery moved by about 1000 W on its own before the
  forced discharge and before the forced-charging window, so neither was measured.
- Discharge window: not checked, the battery was charging.
- Restart: stopped in 2.1 s, Running after 187.4 s, settings survived.
