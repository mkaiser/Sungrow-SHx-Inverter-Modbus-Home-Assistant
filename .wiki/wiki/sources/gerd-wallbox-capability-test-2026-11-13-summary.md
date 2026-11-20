---
type: source
title: gerd-wallbox-capability-test-2026-11-13.md
source_path: raw/gerd-wallbox-capability-test-2026-11-13.md
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - capability-test
  - tls
---

# gerd's wallbox, the first writing capability test, 2026-11-13

The wallbox capability test's first run that wrote, on [gerd](../entities/installation-gerd.md)'s
AC22E-01 at its own address (TLS 516, unit 248), from the maintainer's dev Home Assistant over a VPN,
with a car charging at 10.5 kW and the owner's consent. Highest charging current 16 A. It left the
wallbox disabled; the day's recovery and the search for why the car would not charge again are in the
same note. Source: `raw/gerd-wallbox-capability-test-2026-11-13.md`.

| Fact | Evidence |
| --- | --- |
| **No write of 21203 changed what the car drew**: 6 to 16 A in steps, 5 A and 0 were all taken and the car stayed at 16.1 A | run 1's output current, current follow and below-minimum steps, 10:00-10:14 |
| **A disable (21211 = 0) ends the session, and writing 1 back does not enable the wallbox again**: the app ends the session at 10:14, the minute of the write; ten writes of 1 over two runs and two terminal restores did not take | run 1's enable step at 10:14:06; the app at 10:32 (*Deaktiviert*) |
| **The disable survives a power cut**: 40 s at the breaker, still disabled | 11:47 |
| **One write of 21211 = 1 took**: on a fresh TLS session with no other client, after a VPN restart, status 8 → 2 (standby). Why that one and not the twenty before is not known | 11:47 |
| **Every read-back after a write on the run's session gave 0**, registers not written included, after a desync (duplicate frames with one transaction id discarded); not evidence of what the registers held | the restore table; the log at 10:17:22 |
| **Mileage per kWh (21232) read 55552** afterwards where 50 was written each time; the app showed 5555.2 until it was set back | the probe at 11:47; the write list |
| Status 8 is *disabled*; input 21268 read 8 and input 21314 read 1, "start with EMS", neither seen before | the read-only dump at 13:45 |
| **The inverter's EV charger block reads fast charge and 16.0 A**: the wallbox is managed by the inverter, consistent with 21203 having no effect | the block through the WiNet-S at 15:40 |
| The inverter in VPP mode with a forced charge (13050 = 4, 13051 = 0xAA) was the battery's *Schnellladung* switched on in iSolarCloud, re-applied by the cloud after each write | 13:56, 14:33, the owner at 15:10 |

## What it means

- On a wallbox the inverter manages, the wallbox's own current register is the inverter's to drive; the
  control is the inverter's block. Settled the next day:
  [gerd-wallbox-inverter-control-2026-11-14](gerd-wallbox-inverter-control-2026-11-14-summary.md).
- A run that writes the enable can leave a house without charging and the owner with no way back in the
  app. A run that cannot put everything back raises a Repairs issue naming each setting
  (`custom_components/sungrow_modbus/repairs.py`).
- The mileage check is removed from the capability test (`src/sungrow_modbus/wallbox/capability_test.py`);
  how 55552 came to be stored is still open (`plans/T003-T004-T020-T039-T040-T059-wallbox.md`, section 3.2).
- A read-back on a session that has desynced says nothing; a restore is checked on a fresh session.

## Not answered

- 21203's scale on a standalone wallbox: on a managed one the setting does nothing.
- Why one enable write took and twenty did not.
- Whether the cloud's *Schnellladung* also put the wallbox into "start with EMS".
