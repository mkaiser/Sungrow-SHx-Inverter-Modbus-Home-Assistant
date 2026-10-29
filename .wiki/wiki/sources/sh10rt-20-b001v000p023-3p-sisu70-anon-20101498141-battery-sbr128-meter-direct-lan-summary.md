---
type: source
title: sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan.json
source_path: ../device-survey/inverter/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-20
  - sapphire-h-b001-v000-p023
  - sisu70
  - direct_lan
---

# SH10RT-20, B001.V000.P023, sisu70, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-25. Source: `device-survey/inverter/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan.json`.

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
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR128](../entities/device-sbr-battery.md) |

## What did not answer

Every component answered.

## Contention

Polled by this Home Assistant, throughout (14 components); block read test: not run: it reads every block of the poll three times plus narrowing, which the survey button affords and a diagnostics download does not. See [contention](../concepts/contention.md).
