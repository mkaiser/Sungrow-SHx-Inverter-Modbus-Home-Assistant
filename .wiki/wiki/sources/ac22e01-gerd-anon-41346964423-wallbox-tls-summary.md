---
type: source
title: ac22e01-gerd-anon-41346964423-wallbox-tls.json
source_path: ../device-survey/results/wallbox/ac22e01-gerd-anon-41346964423-wallbox-tls.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - wallbox
  - ac22e-01
  - gerd
  - tls
---

# AC22E-01 wallbox, gerd, at its own address over TLS

Wallbox document, read 2026-10-15. Source: `device-survey/results/wallbox/ac22e01-gerd-anon-41346964423-wallbox-tls.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Device | [wallbox](../entities/device-wallbox.md) |
| Stand-in serial | `anon-41346964423` |
| Path | Modbus TCP inside TLS, port 516, unit 248 |

| Reading | Register | Value | Held by |
| --- | --- | --- | --- |
| `model_name` | 21216 | AC22E-01 | two sources |
| `device_type_code` | 21224 | 0x3F80 | two sources |
| `phase_count` | 21225 | 3 | two sources |
| `version_string` | 21226 | LE-01.1E1.001.901.25 | measured here |
| `nominal_voltage` | 21262 | 230 V | three sources |
| `rated_current` | 21263 | 32.0 A | measured here |
| `phase_mode` | 21270 | 0 | three sources |
| `minimum_charging_power` | 21272 | 4140 W | named elsewhere |
| `maximum_charging_power` | 21273 | 22080 W | two sources |
| `lifetime_energy` | 21300 | 483828 Wh | measured here |
| `phase_a_voltage` | 21302 | 0.0 V | three sources |
| `phase_a_current` | 21303 | 0.0 A | three sources |
| `phase_b_voltage` | 21304 | 0.0 V | three sources |
| `phase_b_current` | 21305 | 0.0 A | three sources |
| `phase_c_voltage` | 21306 | 0.0 V | three sources |
| `phase_c_current` | 21307 | 0.0 A | three sources |
| `charging_power` | 21308 | 0 W | three sources |
| `session_energy` | 21310 | 0 Wh | three sources |
| `control_pilot_voltage` | 21312 | 11.9 V | two sources |
| `unnamed_register_21313` | 21313 | 0 | open |
| `start_mode` | 21314 | 0 | two sources |
| `power_request` | 21315 | 0 | named elsewhere |
| `power_control_allowed` | 21316 | 0 | named elsewhere |
| `charging_status` | 21317 | 1 | three sources |
| `charging_started` | 21318 | 0 | named elsewhere |
| `charging_ended` | 21320 | 0 | named elsewhere |
| `available_current` | 21322 | 16.1 A | measured here |
| `output_current_setting` | 21203 | 0.0 A | two sources |
| `phase_mode_setpoint` | 21204 | 0 | three sources |
| `charger_enabled` | 21211 | 1 | two sources |
| `start_stop` | 21212 | 1 | two sources |
| `mileage_per_kwh` | 21232 | 5.0 km/kWh | named elsewhere |
