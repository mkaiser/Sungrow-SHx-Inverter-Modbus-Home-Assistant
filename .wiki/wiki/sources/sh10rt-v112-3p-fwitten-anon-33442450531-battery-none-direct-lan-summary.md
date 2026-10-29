---
type: source
title: sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan.json
source_path: ../device-survey/inverter/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-01011-95-03
  - fwitten
  - direct_lan
  - control-test
---

# SH10RT-V112, pre-B001 firmware, fwitten slave, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-16. Source: `device-survey/inverter/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan.json`.

| | |
| --- | --- |
| Installation | [fwitten](../entities/installation-fwitten.md) (slave) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-33442450531` |
| Inverter firmware | not in the document (13249 refused); the [older numbering](../entities/firmware-sapphire-h-01011-95-03.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Version strings | `SAPPHIRE-H_01011.95.03`, `SAPPHIRE-H_03011.95.03` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Battery | none |

> Read by the maintainer over a VPN on 2026-10-16 with nothing else polling the inverters, and no Modbus proxy in the path. This house has two inverters in a master/slave cluster, each reachable at two addresses. The slave, at its own LAN port, where it answers on device address 2.

## What did not answer

- `firmware_block_battery`
- `firmware_block_communication_module`
- `firmware_block_inverter`
- `meter_channel_2`

## Control test

Outcome **0**: every planned check ran and every readback matched. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `export_power_limit` | 13074 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- Restart: stopped after 2 s, running after 170 s; the inverter did as it was told.
- Restore: every register back and read back.
