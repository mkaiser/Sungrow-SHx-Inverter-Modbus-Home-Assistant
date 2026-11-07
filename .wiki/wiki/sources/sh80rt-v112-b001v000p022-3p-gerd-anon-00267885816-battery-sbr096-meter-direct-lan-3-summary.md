---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3.json
source_path: ../device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3.json
ingested: '2026-11-03'
created: '2026-11-03'
tags:
  - diagnosis
  - sh80rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - direct_lan
  - capability-test
---

# SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, third reading

Read by the maintainer over a VPN on 2026-11-03 around noon, the owner's Home Assistant stopped,
while a car charged on the [wallbox](../entities/device-wallbox.md) at about 10.7 kW, with the full
capability test on this tree's library. Schema 23. Source:
`device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Model | [SH8.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0E` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| Transport | the inverter's own LAN port; 6100 answered; no link drops |
| Battery | [SBR096](../entities/device-sbr-battery.md), SoC 24.1 % |
| Answered | 236 of 245 fields; 36 of 36 blocks (33046 and 33148 read inconsistently in one round) |

## Capability test

Outcome **0**, 9 of 9 readbacks matched. See [the capability test](../concepts/capability-test.md).

- [13074](../entities/register-13074.md): the probe was refused three times, **times ten**; 600 W
  went out as raw 600.
- Behaviour, all did as they were told: forced charge (-3800, 1249, -3800 W), forced discharge
  (3800, 1249, 3799 W), the **PV cut** (2381, 0, 1976 W), the forced-charging window (-3800,
  4399, -3799 W) and the discharge windows moved away from now (3799, 0, 3800 W).
- Could not make the house export: discharge is capped at 3800 W against an 11184 W house (the car).
- Restart: stopped in 2.1 s, Running after 180.8 s, settings survived.
- The snapshot's forced-charging window was 12:42-13:07, target 37 %, where the
  [second reading](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)
  found 00:00-00:00, target 0: the window the
  [dongle run of 2026-11-01](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)
  wrote, left behind by a restore that trusted the dongle's readback. See
  [the restore](../concepts/capability-test-restore.md).
