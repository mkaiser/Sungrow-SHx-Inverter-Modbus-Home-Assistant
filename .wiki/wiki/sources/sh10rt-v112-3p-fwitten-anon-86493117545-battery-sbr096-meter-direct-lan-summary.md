---
type: source
title: sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json
source_path: ../device-survey/inverter/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json
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

# SH10RT-V112, pre-B001 firmware, fwitten master, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-16. Source: `device-survey/inverter/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [fwitten](../entities/installation-fwitten.md) (master) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-86493117545` |
| Inverter firmware | not in the document (13249 refused); the [older numbering](../entities/firmware-sapphire-h-01011-95-03.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Version strings | `SAPPHIRE-H_01011.95.03`, `SAPPHIRE-H_03011.95.03` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-16 with nothing else polling the inverters, and no Modbus proxy in the path. This house has two inverters in a master/slave cluster, each reachable at two addresses. The master, at its own LAN port, with the SBR096.

## What did not answer

- `firmware_block_battery`
- `firmware_block_communication_module`
- `firmware_block_inverter`
- `meter_channel_2`

## Control test

Outcome **3**: ran, but checks were skipped or inconclusive. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | matched -- one point only: no admissible second value a decade away |
| `battery_forced_charge_discharge_power` | 13052 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- Behaviour, forced discharge: **the inverter did as it was told**.
- Behaviour, export power limit: **nothing measurable happened** -- nothing moved by more than the house moves on its own.
- Restart: stopped after 2 s, running after 197 s; the inverter did as it was told.
- Restore: every register back and read back.
