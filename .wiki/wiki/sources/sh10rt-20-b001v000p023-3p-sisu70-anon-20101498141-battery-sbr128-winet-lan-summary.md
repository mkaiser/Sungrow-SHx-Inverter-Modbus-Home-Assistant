---
type: source
title: sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan.json
source_path: ../device-survey/results/inverter/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-20
  - sapphire-h-b001-v000-p023
  - sisu70
  - winet_lan
---

# SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-10-25. Source: `device-survey/results/inverter/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan.json`.

| | |
| --- | --- |
| Installation | [sisu70](../entities/installation-sisu70.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13` |
| Stand-in serial | `anon-20101498141` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14` |
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR128](../entities/device-sbr-battery.md) |

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

Of the battery pack (unit 2): `sbr_battery_cells (IllegalDataAddressError)`, `sbr_battery_modules (IllegalDataAddressError)`.

## Contention

Polled by this Home Assistant, throughout (14 components); block read test: not run: it reads every block of the poll three times plus narrowing, which the survey button affords and a diagnostics download does not. See [contention](../concepts/contention.md).
