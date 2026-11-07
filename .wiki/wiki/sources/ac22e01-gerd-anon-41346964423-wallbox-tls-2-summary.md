---
type: source
title: ac22e01-gerd-anon-41346964423-wallbox-tls-2.json
source_path: ../device-diagnosis/results/wallbox/ac22e01-gerd-anon-41346964423-wallbox-tls-2.json
ingested: '2026-11-03'
created: '2026-11-03'
tags:
  - diagnosis
  - wallbox
  - ac22e-01
  - gerd
  - tls
---

# AC22E-01 wallbox, gerd, at its own address over TLS, while charging

Wallbox document, read 2026-11-03 at 11:53 UTC by the maintainer over a VPN while a car charged.
Source: `device-diagnosis/results/wallbox/ac22e01-gerd-anon-41346964423-wallbox-tls-2.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Device | [wallbox](../entities/device-wallbox.md) |
| Stand-in serial | `anon-41346964423` |
| Path | Modbus TCP inside TLS, port 516, unit 248; 279 raw addresses answered |

| Reading | Register | Value |
| --- | --- | --- |
| `charging_status` | 21317 | 3, charging |
| `charging_power` | 21308 | 10671 W |
| phase currents | 21303, 21305, 21307 | 15.5, 15.8, 16.2 A |
| phase voltages | 21302, 21304, 21306 | 226.4, 225.7, 226.0 V |
| `control_pilot_voltage` | 21312 | 5.94 V |
| `session_energy` | 21310 | 8163 Wh |
| `lifetime_energy` | 21300 | 686222 Wh |
| `unnamed_register_21313` | 21313 | 527 |
| `start_mode` | 21314 | 3 |
| `charging_started` | 21318 | 1793704038 |
| `charging_ended` | 21320 | 1793706793 |
| `available_current` | 21322 | 16.0 A |

The session began 2755 s before the value at 21320, and 8163 Wh at about 10.7 kW is about 2750 s
of charging: **while a session runs, 21320 holds the time of the reading**, not an end. The
[dongle reading](sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md)
26 minutes later has 21320 moved on by 1894 s and the same start.
