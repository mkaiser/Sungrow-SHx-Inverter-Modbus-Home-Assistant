---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-17.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-17.json
ingested: '2026-11-13'
created: '2026-11-13'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, nineteenth reading

Read 2026-11-11 at 20:33 UTC from Home Assistant (`command_line`: "home assistant diagnostics"),
posted by Korsberg to issue #786 as `...direct-lan (1).json`. A read-only reading: it carries no
capability test. Committed unchanged as `-17`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-17.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md), five modules, firmware `SBRBCU-S_22011.01.30` |
| At the time | after dark: PV 0 W, SoC 19.4 %, load 404 W, the battery discharging 640 W |

Every component answered. The block read test (Home Assistant's own connection, its polling held
off) had five blocks inconsistent in one round and whole in the other (input 5214, holding 33047,
input 2582, input 13265, input 6227), with no reconnects; 32 blocks answered in both rounds.
