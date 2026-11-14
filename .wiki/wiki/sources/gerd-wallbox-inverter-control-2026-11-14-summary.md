---
type: source
title: gerd-wallbox-inverter-control-2026-11-14.md
source_path: raw/gerd-wallbox-inverter-control-2026-11-14.md
ingested: '2026-11-14'
created: '2026-11-14'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - capability-test
  - ems
---

# gerd's wallbox, controlled through the inverter, 2026-11-14

On site at [gerd](../entities/installation-gerd.md), with a car charging (three phase, at most
16 A) and the owner's consent: the [wallbox](../entities/device-wallbox.md) read over TLS, the
inverter at unit 1 over its LAN cable or through the [WiNet-S](../entities/device-winet-s.md),
the owner switching modes in iSolarCloud, then writes to the inverter. Source:
`raw/gerd-wallbox-inverter-control-2026-11-14.md`. Register numbers here; the raw note gives
protocol addresses, one lower.

| Fact | Evidence |
| --- | --- |
| **The inverter manages this wallbox, and drives its output current (holding 21203)** | 21203 ramps about 1.4 A every 5 s after a start and keeps climbing towards the rating in fast charge, with nothing else writing; two writes of 6 A to it read 160 for about 6 s, then the inverter's value again; the car never moved |
| **21203 is 0.1 A per count**, settled by behaviour | after a replug the car followed the ramp one step behind: 7.3 A offered, 6.1-6.5 A drawn; 12.4 / 10.5-11.1; 15.2 / 13.8-14.7 |
| **Inverter holding 33540 is charging on/off**: 0xAA on, 0x55 off | the app's Stop and Start flipped it; written 0x55 the car stopped within a second, written 0xAA it charged within 7-15 s and ramped to 16 A in about 40 s, no replug |
| **Inverter holding 33541 is the charging mode**: 160 fast, 161 PV surplus, 163 user defined | each change in the app showed there within 6 s; written over Modbus, 163 brought the car to the user current within 13 s |
| **Inverter holding 33545 is the user-defined current, 0.1 A per count**, effective only in user-defined mode | set to 10 A in the app, the car drew 9.1-9.6 A; written 8 A and 12 A, it drew 7.2-7.6 and 10.9-11.6 A; 21203 followed (a lower value at once, a higher one ramped) |
| **33545 is writable only while 33541 is 163** | in fast charge every write was refused with exception 0x04, 37 times |
| **6 A is the floor; the rating is not a ceiling** | 5 A refused (0x04), 6 A taken (car 5.7-6.0 A), 32 A and 33 A taken on a 32 A wallbox |
| **A mode change has side effects** | to 163 switched charging on by itself (even from off); 163 to 160 and 160 to 161 ended the session (status completed); charging on written after brought it back |
| The WiNet-S takes these writes as the cable does | the 16 A restore, test 4 and test 5 went through it, judged by what the car did |
| **In PV surplus the inverter dropped every start** with 1.7 kW of sun and the battery at its minimum SoC | 6 A offered for about 10 s, then charging off; with "surplus from the grid" (33550) set to yes, the same |
| A stopped car falls asleep | a start 7 minutes after a stop gave *suspended by the vehicle* with up to 21 A offered; a replug woke it; a start 2.5 minutes after a stop did not need one |
| The app's enable is wallbox holding 21211, its Start/Stop wallbox holding 21212 (0 start) | 21211 0 → 1 when switched on in the app; 21212 1 → 0 on Start |
| Wallbox input 21314 read 1 idle and 3 during a session | every reading of the day |

What did not answer: what 33550 does (a minimum charge from the grid was not kept up), and the
quantity-and-time mode (162), not tried.

Two writes of 21203 on the wallbox itself were made in breach of
`plans/wallbox_recovery_and_retest.md`'s stop (only 21203, nothing under 6 A, no enable and no
start/stop); both were overwritten by the inverter and put back.

What it changed: the wallbox [capability test](../concepts/capability-test.md) now writes nothing
unless the wallbox is declared standalone, and never disables or offers under 6 A
(`src/sungrow_modbus/wallbox/capability_test.py`); the inverter's block is
`src/sungrow_modbus/hybrid_inverter/ev_charger.py`, held to these readings by
`tests/test_ev_charger_control.py`.
