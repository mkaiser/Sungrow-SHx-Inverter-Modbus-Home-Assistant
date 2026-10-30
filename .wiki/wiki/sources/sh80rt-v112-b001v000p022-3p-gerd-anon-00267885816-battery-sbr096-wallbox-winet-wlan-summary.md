---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan.json
source_path: ../device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh8-0rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - winet_wlan
  - export-scale
  - wallbox
---

# SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi

Capability survey of one inverter, read 2026-10-14. Source: `device-survey/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Model | [SH8.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0E` |
| Stand-in serial | `anon-00267885816` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P043` |
| Version strings | `SAPPHIRE-H_01011.95.13`, `SAPPHIRE-H_03011.95.13` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-14 with Home Assistant stopped and nothing else polling, and no Modbus proxy in the path. The owner reports the wiring: a LAN cable directly into the inverter, the WiNet-S on WLAN, and the wallbox on a LAN cable of its own. This is the WiNet-S dongle.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

Of the battery pack (unit 2): `sbr_battery_cells (IllegalDataAddressError)`, `sbr_battery_modules (IllegalDataAddressError)`.

## Export write scale

Register 13074 multiplies a written word by ten: `write_units_per_count` = **10**, probed at a held 8000 W. See [register 13074](../entities/register-13074.md).

This dongle also carried the [wallbox](../entities/device-wallbox.md) at unit 3.
