---
type: source
title: sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - fwitten
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-29. Source: `device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan.json`.

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
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN on 2026-10-29, after the owner upgraded the firmware of both inverters, with nothing else polling the inverters, and no Modbus proxy in the path. This house has two inverters in a master/slave cluster, each reachable at two addresses. The master, at its own LAN port, with the SBR096.

## What did not answer

Every component answered.

## Control test

Outcome **3**: ran, but checks were skipped or inconclusive. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | matched |
| `battery_forced_charge_discharge_power` | 13052 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- Behaviour, forced charge: **the inverter did as it was told**.
- Behaviour, forced discharge: **could not tell** -- the input drifted across the measurement.
- Behaviour, export power limit: **could not tell** -- something changed, but not to the value that was commanded; export was made by discharging 3200 W.
- Behaviour, PV generation cut: **the inverter did as it was told**.
- Restart: stopped after 2 s, running after 197 s; the inverter did as it was told.
- Restore: every register back and read back.
