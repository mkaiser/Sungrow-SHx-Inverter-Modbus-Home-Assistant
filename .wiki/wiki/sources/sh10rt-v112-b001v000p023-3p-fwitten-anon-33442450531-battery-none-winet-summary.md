---
type: source
title: sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet.json
source_path: ../device-survey/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet.json
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

# SH10RT-V112, B001.V000.P023, fwitten slave, a WiNet-S (medium not reported)

Capability survey of one inverter, read 2026-10-29. Source: `device-survey/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet.json`.

| | |
| --- | --- |
| Installation | [fwitten](../entities/installation-fwitten.md) (slave) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-33442450531` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14` |
| Transport (owner) | a WiNet-S (medium not reported) |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | none |

> Read by the maintainer over a VPN on 2026-10-29, after the owner upgraded the firmware of both inverters, with nothing else polling the inverters, and no Modbus proxy in the path. This house has two inverters in a master/slave cluster, each reachable at two addresses. The slave through its WiNet-S; which medium the dongle uses is not established.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

## Export write scale

Register 13074 multiplies a written word by ten: `write_units_per_count` = **10**, probed at a held 11880 W. See [register 13074](../entities/register-13074.md).
