---
type: source
title: sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - fwitten
  - winet
  - export-scale
---

# SH10RT-V112, B001.V000.P023, fwitten master, a WiNet-S (medium not reported)

Capability survey of one inverter, read 2026-10-29. Source: `device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet.json`.

| | |
| --- | --- |
| Installation | [fwitten](../entities/installation-fwitten.md) (master) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-86493117545` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14` |
| Transport (owner) | a WiNet-S (medium not reported) |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-29, after the owner upgraded the firmware of both inverters, with nothing else polling the inverters, and no Modbus proxy in the path. This house has two inverters in a master/slave cluster, each reachable at two addresses. The master through its WiNet-S; which medium the dongle uses is not established.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

Of the battery pack (unit 2): `sbr_battery_cells (IllegalDataAddressError)`, `sbr_battery_modules (IllegalDataAddressError)`.

## Export write scale

Register 13074 multiplies a written word by ten: `write_units_per_count` = **10**, probed at a held 24990 W. See [register 13074](../entities/register-13074.md).
