---
type: source
title: sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json
source_path: ../device-survey/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-20
  - sapphire-h-b001-v000-p023
  - bar12
  - winet_wlan
---

# SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi

Capability survey of one inverter, read 2026-10-13. Source: `device-survey/results/inverter/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [bar12](../entities/installation-bar12.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13` |
| Stand-in serial | `anon-81257679535` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.27` |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-13 with nothing else polling and no Modbus proxy in the path. One inverter reached two ways: a LAN cable in the inverter's own port, and the WiNet-S on WiFi. This is the WiNet-S.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

Of the battery pack (unit 2): `sbr_battery_cells (IllegalDataAddressError)`, `sbr_battery_modules (IllegalDataAddressError)`.
