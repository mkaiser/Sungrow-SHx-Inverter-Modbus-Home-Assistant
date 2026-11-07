---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7.json
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighth reading

Capability diagnosis of one inverter, read 2026-11-06 around 17:44 UTC from Home Assistant 2026.11.0
(Home Assistant OS) with integration 0.1.0a26, posted by Korsberg to issue #786. **Taken from a
diagnostics download**: the owner attached the integration's diagnostics, whose `diagnosis` section
is the publishable diagnosis (`custom_components/sungrow_modbus/diagnostics.py`); that section is
committed as it was, under the library's own name for it. A diagnostics download takes no
register dump, no block read test and no capability test. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-7.json`.

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

Every component answered. No block read test was taken, so intermittent blocks cannot be told.

## Contention

Polled by this Home Assistant, held off for the run (22 components). See
[contention](../concepts/contention.md).

## What it adds

Nothing new about the device: the type code, firmware, capability probes (every probe in the
same state as the [seventh reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6-summary.md))
and answering components are the same, and only the live values differ. It is the installation's
first reading from a diagnostics download, and the first on Home Assistant 2026.11.0 and
integration 0.1.0a26; nothing in it differs on that account. No capability test ran, so
[13074](../entities/register-13074.md)'s scale and the charge window's write of 33213 are not
measured here.
