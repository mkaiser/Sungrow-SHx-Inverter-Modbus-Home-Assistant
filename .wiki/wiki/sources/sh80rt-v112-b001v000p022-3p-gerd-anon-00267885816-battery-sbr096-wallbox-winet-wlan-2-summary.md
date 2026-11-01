---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2.json
source_path: ../device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - survey
  - sh80rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - winet
  - wallbox
  - control-test
---

# SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, second reading

Read by the maintainer over a VPN on 2026-11-01 around noon, right after the
[cable reading](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md),
the owner's Home Assistant stopped, with the full control test on this tree's library. Source:
`device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| Communication module firmware | `WINET-SV200.001.00.P043` |
| Transport | a [WiNet-S](../entities/device-winet-s.md) on WiFi; 6100 refused |
| Answered | 161 of 245 fields; 31 of 36 blocks: 2613, 2629 and the three [history](../concepts/energy-history.md) blocks refused every round, nothing intermittent |
| Wallbox | the [AC22E-01](../entities/device-wallbox.md) at unit 3 |

## The wallbox after a session

A car charged this morning: start 09:37:23 and end 11:33:15 local (21318, 21320), session energy
7854 Wh (input 21310), status idle, charging power 0. Read after the session, so it does not
answer how 21313 behaves during one; it reads 0 here, as it did before any session. The start
mode (input 21314) reads 3 where the earlier dongle reading had 0, and holding 21312 reads 2
where it had 0.

## Control test

Outcome **3**. Through a WiNet-S only leg C is evidence: three readbacks reported the old word
(13058, 33047, 33048), which is the dongle's [stale readback](../entities/device-winet-s.md).
See [the control test](../concepts/control-test.md).

- [13074](../entities/register-13074.md): not asked; feed-in limitation was off, and the run had
  no leave to lift it through this path.
- Behaviour: forced charge (1878, 1247, 1780 W) and forced discharge (1251 W for 1250 W) did as
  they were told; the export limit could not tell (the house moved 730 W).
- **PV cut: did as it was told through the dongle** (2169, 0, 2219 W).
- **Forced-charging window: did as it was told** (1656 W, 4400 W, 1681.5 W).
- Discharge window: not checked, the battery was charging.
- Restart: stopped in 4.1 s, Running after 181.3 s.
