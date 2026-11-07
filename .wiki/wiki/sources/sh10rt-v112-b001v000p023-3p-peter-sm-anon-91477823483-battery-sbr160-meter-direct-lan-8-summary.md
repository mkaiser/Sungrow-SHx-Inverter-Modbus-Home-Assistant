---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8.json
ingested: '2026-11-07'
created: '2026-11-07'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, ninth reading

Capability diagnosis of one inverter, read 2026-11-07 around 08:10 UTC from Home Assistant 2026.11.0
with integration 0.1.0a27, posted by Korsberg to issue #786. **Taken from a diagnostics
download**: its `diagnosis` section is committed as it was, under the library's own name for it
(`custom_components/sungrow_modbus/diagnostics.py`). No register dump, no block read test, no
capability test. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md) (unit 200, modules 1-5 fitted) |

## What did not answer

Every component answered.

## Contention

Polled by this Home Assistant, held off for the run (22 components). See
[contention](../concepts/contention.md).

## What it adds

Nothing new about the device: every probe in the same state as the
[eighth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7-summary.md),
the same firmware, the same components answering. The first reading on integration 0.1.0a27.
