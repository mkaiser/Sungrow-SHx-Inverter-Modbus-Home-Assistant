---
type: source
title: sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt
  - sapphire-h-b001-v000-p020
  - mkaiser
  - direct_lan
  - control-test
---

# SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-16. Source: `device-survey/results/inverter/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [mkaiser](../entities/installation-mkaiser.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-37323352958` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Version strings | `SAPPHIRE-H_01011.95.12`, `SAPPHIRE-H_03011.95.12` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Battery | thirdparty |

## What did not answer

Every component answered.

## Control test

Outcome **0**: every planned check ran and every readback matched. See [the control test](../concepts/control-test.md).

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

- Behaviour, forced discharge: **the inverter did as it was told**.
- Behaviour, export power limit: **the inverter did as it was told**.
- Restart: stopped after 2 s, running after 187 s; the inverter did as it was told.
- Restore: every register back and read back.
