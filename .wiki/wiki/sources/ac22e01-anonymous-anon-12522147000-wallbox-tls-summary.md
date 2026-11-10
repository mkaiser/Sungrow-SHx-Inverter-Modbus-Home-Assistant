---
type: source
title: ac22e01-anonymous-anon-12522147000-wallbox-tls.json
source_path: ../device-diagnosis/results/wallbox/ac22e01-anonymous-anon-12522147000-wallbox-tls.json
ingested: '2026-11-10'
created: '2026-11-10'
tags:
  - diagnosis
  - wallbox
  - ac22e-01
  - anonymous
  - tls
---

# AC22E-01 wallbox, anonymous, at its own address over TLS, after a session

Wallbox document, read 2026-11-10 at 12:15 UTC by *Diagnosis: start* on a standalone wallbox
entry in Home Assistant, integration 0.1.0a35, posted to issue #786 and signed `anonymous`.
**The second wallbox in the corpus**, and the first read by a contributor. Source:
`device-diagnosis/results/wallbox/ac22e01-anonymous-anon-12522147000-wallbox-tls.json`.

| | |
| --- | --- |
| Device | [wallbox](../entities/device-wallbox.md), AC22E-01, type code `0x3F80`, three phase |
| Stand-in serial | `anon-12522147000` |
| Firmware | `LE-01.1E1.001.901.25` |
| Path | Modbus TCP inside TLS, port 516, unit 248; 279 raw addresses answered |

The same 279 addresses answered as on [gerd's](ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md)
AC22E-01, on the same firmware.

| Reading | Register | Value |
| --- | --- | --- |
| `charging_status` | 21317 | 6, completed |
| `charging_power` | 21308 | 0 W |
| phase voltages and currents | 21302-21307 | all 0 |
| `control_pilot_voltage` | 21312 | 8.85 V |
| `session_energy` | 21310 | 5451 Wh |
| `lifetime_energy` | 21300 | 447899 Wh |
| `unnamed_register_21313` | 21313 | 0 |
| `start_mode` | 21314 | 3 |
| `charging_started` | 21318 | 1794292226, 06:30:26 on the wallbox's clock |
| `charging_ended` | 21320 | 1794295800, 07:30:00 on the wallbox's clock |
| `output_current_setting` | 21203 | 0 A |
| `available_current` | 21322 | 16.1 A |
| `maximum_charging_power` | 21273 | 22080 W |
| `mileage_per_kwh` | 21232 | 6.0 km/kWh |

- **After a session, 21320 holds its end**: 07:30:00, hours before the reading, 3574 s after the
  start, and 5451 Wh in that time is 5.5 kW on average. During a session it holds the time of
  the reading instead ([gerd, TLS](ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md)).
- 21313 reads 0 and the start mode 3 with the session done, as at gerd after one.
- The phase voltages read 0 with no charge, where gerd's read about 226 V while charging.
- The output current setting reads 0 with no charge, as in gerd's
  [dry run](gerd-wallbox-dry-run-2026-11-06-summary.md), and 21322 holds 16.1 A beside it.
