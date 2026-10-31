---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2.json
ingested: '2026-10-31'
created: '2026-10-31'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, third reading

Capability survey of one inverter, read 2026-10-30 from Home Assistant on 0.1.0a19, issue #785,
with a control test. The survey derives the same name as this installation's second reading, so
the file carries the survey's number for a taken name, `-2`. Source:
`device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-2.json`.

The issue carried a second run 14 minutes earlier, from an older release (14 components, no PV
cut capability), not committed: same readbacks, 13074 times ten, forced discharge and export
limit did as told, forced charge inconclusive (the house moved 804 W across it). This run
covers all of it.

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

Nothing: every component answered, and no block went unanswered. **Intermittent**, over three
rounds: 5008 (1), 2629 (15) and 13265 (15) read `inconsistent` in one round and `ok` in the
others. 2629 and 13265 were intermittent in the second reading as well; 4952 was then, and is
not now.

New against the second reading: [31211](../entities/register-31211.md) is read (the
`pv_generation_cut` component, raw 85 = 0x55), and the pack is granted `sungrow_battery`.

## Contention

Polled by this Home Assistant, held off for the run (15 components). No other client reported.
See [contention](../concepts/contention.md).

## Control test

Outcome **0**: every planned check ran and every readback matched. Over the cable, so leg B is
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
  written back was refused with 0x04 three times, as 95000 W would be. Feed-in limitation on
  (13087 = 0xAA). Third reading, third time the same answer.
- The house's battery limits were back at **10000 W** each, where the second reading had 10 W.
  So this is the run the second reading could not be.
- Behaviour, all three checks **did as they were told**, PV 0 W, SoC 24 %:

  | Check | Before | During | After | Commanded |
  | --- | --- | --- | --- | --- |
  | forced charge (battery charge power) | -507.5 W | 1248 W | -510.5 W | 1250 W |
  | forced discharge (battery discharge power) | 510.5 W | 1250 W | 487 W | 1250 W |
  | export power limit (export power) | 2597 W | 1250 W | 2598.5 W | 1250 W |

  The export was manufactured by discharging 3140 W; the pack accepted 3140 of the 3142 W asked.
  An export cap held at 1250 W with 13074 written at times ten.
- Not checked: the charge ceiling (SoC 24 %, and `battery_max_soc` cannot go below 50 %); the PV
  cut (no leave to cut PV, so 31211 was read and never written); a restart (not asked).
- Restore: every register back and read back, `pv_generation_cut_raw` included.
