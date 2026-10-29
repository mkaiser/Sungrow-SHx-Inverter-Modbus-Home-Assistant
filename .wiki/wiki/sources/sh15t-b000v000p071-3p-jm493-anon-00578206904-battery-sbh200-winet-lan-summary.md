---
type: source
title: sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan.json
source_path: ../device-survey/inverter/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh15t
  - pearl-h-b000-v000-p071
  - jm493
  - winet_lan
---

# SH15T, B000.V000.P071, jm493, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-10-07. Source: `device-survey/inverter/sh15t-b000v000p071-3p-jm493-anon-00578206904-battery-sbh200-winet-lan.json`.

| | |
| --- | --- |
| Installation | [jm493](../entities/installation-jm493.md) |
| Model | [SH15T](../entities/device-sh-t.md), type code `0x0E25` |
| Stand-in serial | `anon-00578206904` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM firmware | `ARM_PEARL-H_V11_V01_A` |
| DSP firmware | `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Version strings | `PEARL-H_01011.01.45`, `PEARL-H_03011.01.45` |
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBH200](../entities/device-sbh-battery.md) |

> SBH200. All house circuits on Backup side.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

Of the battery pack (unit 2): `sbr_battery_cells`, `sbr_battery_modules`.
