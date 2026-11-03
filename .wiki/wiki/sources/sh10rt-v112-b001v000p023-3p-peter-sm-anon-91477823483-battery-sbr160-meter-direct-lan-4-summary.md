---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-4.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-4.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fifth reading

Capability survey of one inverter, read 2026-11-01 in the evening from Home Assistant on
0.1.0a24 (the owner's note in issue #786), with a control test that declined to run. The survey
derives the same name as the earlier readings, so the file carries the next number, `-4`.
Source: `device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-4.json`.

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
| Battery | [SBR160](../entities/device-sbr-battery.md) (unit 200), 4.2 % SoC |

## What did not answer

No block failed in every round. **Intermittent**, over three rounds: 5008 (1), 33179 (9), 2629
(15) and 6596 (42) read `inconsistent` in one round and `ok` in the others. The battery's
modules component failed its read with `ModbusConnectionError`, a lost connection rather than a
refusal, so it says nothing about the registers
([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)); every earlier cable
reading here read it.

## What the dump adds

The same settings as the fourth reading: [31211](../entities/register-31211.md) 0x55,
[13074](../entities/register-13074.md) 9200 W with feed-in limitation on, the forced-charging
schedule off, weekday discharge window 1 00:00-24:00, weekend discharge on with window 1
00:00-24:00, the history block whole. Register 32998 holds 990 (950 in the fourth reading).

## Contention

Polled by this Home Assistant, held off for the run (22 components). See
[contention](../concepts/contention.md).

## Control test

Outcome **2**: it did not run. The inverter reported Standby, and every check is about what it
does while it works. Nothing was written. See [the control test](../concepts/control-test.md).
