---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan.json
ingested: '2026-10-30'
created: '2026-10-30'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-29 from Home Assistant, issue #785, with a
control test. The issue carried two files a minute apart; this is the second, which holds the
first's reading plus the control test. Source: `device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md) (unit 200, five modules) |

## What did not answer

Every component answered, 25 of 25 blocks. **Intermittent**, over three rounds: 4952 (54),
2629 (15) and 13265 (15) read `inconsistent` in one round and `ok` in the others, as 13002 and
13280 did in this installation's first reading.

## Contention

Polled by this Home Assistant, held off for the run (14 components). No other client reported.
See [contention](../concepts/contention.md).

## Control test

Outcome **3**: ran, but checks were skipped or inconclusive. Over the cable, so leg B is
evidence. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | matched, two points |
| `battery_max_discharge_power` | 33048 | matched, two points |
| `export_power_limit` | 13074 | matched, two points |
| `battery_forced_charge_discharge_power` | 13052 | matched, two points |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- [13074](../entities/register-13074.md) write scale: **times ten**, by refusal: the held 9500 W
  written back was refused with 0x04, as 95000 W would be. Feed-in limitation was on (13087 =
  0xAA), and the readback of 600 W written as word 60 matched. Same answer as the first reading.
- Behaviour, forced charge and forced discharge: **nothing measurable happened**, 0 W before,
  during and after. Not evidence about the inverter: before the run the house held
  `battery_max_charge_power` and `battery_max_discharge_power` at **10 W** (the first reading had
  10000 W), and the forced checks commanded 1250 W under those caps. PV was 0 W. The control
  test now skips such a check and names the limit
  ([the control test](../concepts/control-test.md)).
- Export limit and charge ceiling: not checked (SoC 26.3 %, and a 3010 W discharge still
  imported 328 W, short of the 1812 W a cap needs to bind against).
- Restore: every register back and read back.
