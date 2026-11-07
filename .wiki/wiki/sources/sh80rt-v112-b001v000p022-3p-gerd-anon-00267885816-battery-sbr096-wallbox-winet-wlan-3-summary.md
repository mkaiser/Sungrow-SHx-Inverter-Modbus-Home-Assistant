---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3.json
source_path: ../device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3.json
ingested: '2026-11-03'
created: '2026-11-03'
tags:
  - diagnosis
  - sh80rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - winet
  - wallbox
  - capability-test
---

# SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, third reading

Read by the maintainer over a VPN on 2026-11-03, right after the
[cable reading](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md),
the owner's Home Assistant stopped, with the full capability test, while a car charged. Read on the
library at commit `85c9784`. Source:
`device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| Communication module firmware | `WINET-SV200.001.00.P043` |
| Transport | a [WiNet-S](../entities/device-winet-s.md) on WiFi; 6100 refused |
| Answered | 161 of 245 fields; 31 of 36 blocks: 2613, 2629 and the three [history](../concepts/energy-history.md) blocks refused every round |
| Battery | SBR at unit 2: 7 values; the cell and module blocks refused with 0x02 |
| Wallbox | the [AC22E-01](../entities/device-wallbox.md) at unit 3, **charging** |

## The wallbox during a session

The first reading of the wallbox while a car charges: 10646 W (input 21308), 15.5/15.8/16.2 A on
three phases at 5.93 V control pilot (input 21312), status 3 charging (input 21317), session energy
13784 Wh (input 21310), start mode 3 (input 21314), and **input 21313 at 527** where it reads 0
with no session. Every value the
[TLS reading](ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md) 26 minutes earlier shares
with this one agrees, apart from the counters (energy, and the time at 21320).

## Capability test

Outcome **3**. Through a WiNet-S only leg C is evidence: three readbacks reported the old word
(13058, 33047, 33048), the dongle's [stale readback](../entities/device-winet-s.md). See
[the capability test](../concepts/capability-test.md).

- [13074](../entities/register-13074.md): not asked; feed-in limitation was off.
- Behaviour: forced charge (-3800, 1249, -3800 W) and the **PV cut** (1208.5, 0, 1466 W) did as
  they were told.
- **Forced-charging window: refused**, 0x04 on the write of 33211.
- **Restart: not run**, the stop refused with an exception.
- Not checked: forced discharge, the discharge window and export, the battery at 10.3 % against
  a 10 % floor (the car drew it down); 13100 was not written, every admissible value being too
  close to the battery's level.
- Every restore row reads "already holding its original value", read through the dongle's cache.
  That is the restore behaviour [the restore](../concepts/capability-test-restore.md) no longer has.
