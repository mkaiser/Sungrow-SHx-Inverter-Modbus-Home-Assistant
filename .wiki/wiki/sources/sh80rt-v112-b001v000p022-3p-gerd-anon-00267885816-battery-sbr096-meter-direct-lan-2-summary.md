---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2.json
source_path: ../device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - survey
  - sh80rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - direct_lan
  - control-test
---

# SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, second reading

Read by the maintainer over a VPN on 2026-11-01 around noon, the owner's Home Assistant stopped,
with the full control test on this tree's library (timed windows included). Source:
`device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Model | [SH8.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0E` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md), version 1 `SAPPHIRE-H_01011.95.13` |
| Transport | the inverter's own LAN port; 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md), SoC 21.2 % |
| Answered | 236 of 245 fields; 36 of 36 blocks (5115 and 5242 read inconsistently in one round) |

## Energy history

The whole block answered. Direct consumption's 2026 yearly slot equals the sum of its months
(1688.0 kWh). **PV generation's and export's do not: each yearly slot is 1610.3 kWh above the sum
of its months** (PV 11755.6 against 10145.3 kWh, export 8610.2 against 6999.9 kWh). The yearly PV
slots for 2024 and 2025 read 21429.6 and 28914.4 kWh, more than an 8 kW inverter makes in a year.
See [energy history](../concepts/energy-history.md).

Register 32998 reads 2000.

## Control test

Outcome **3**, 9 of 9 readbacks matched. See [the control test](../concepts/control-test.md).

- [13074](../entities/register-13074.md): the probe was refused three times, **times ten**; 600 W
  went out as raw 600.
- Behaviour, all did as they were told: forced charge (1533, 1248, 1580 W), forced discharge
  (1252 W for 1250 W), export limit (4904.5, 1256, 4554 W for 1250 W, export made by discharging
  3180 W), and the **PV cut** (2574.5, 0, 2597 W), its second confirmation on P022.
- **Forced-charging window: could not tell.** Charge power 2218 W before, 4399.5 W during,
  1875 W after: the window plainly raised charging, and the 343 W drift outweighed the rule's
  bracket.
- Discharge window: not checked, the battery was charging.
- No charge-ceiling check: SoC 21.2 %.
- Restart: stopped in 2.1 s, Running after 184.6 s, settings survived.
