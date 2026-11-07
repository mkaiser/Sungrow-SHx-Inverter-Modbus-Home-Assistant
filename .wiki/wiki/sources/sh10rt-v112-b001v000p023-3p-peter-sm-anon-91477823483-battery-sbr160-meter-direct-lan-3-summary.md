---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3.json
ingested: '2026-10-31'
created: '2026-10-31'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, fourth reading

Capability diagnosis of one inverter, read 2026-10-31 from Home Assistant on 0.1.0a23 (the owner's
note in issue #785), with a capability test. The first reading of this installation whose register
dump covers the whole history block and the forced-charging schedule. The diagnosis derives the same
name as the second and third readings, so the file carries the next number, `-3`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3.json`.

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
| Battery | [SBR160](../entities/device-sbr-battery.md) (unit 200, five modules) |

## What did not answer

Nothing. **Intermittent**, over three rounds: 31213 (1), 2582 (26) and 13280 (15) read
`inconsistent` in one round and `ok` in the others. None of the three was intermittent in the
third reading, and 2629 and 13265, which were then, are not now.

## What the dump adds

- **The history block answers whole over the cable**: inputs 6100-6825 (registers 6101-6826),
  every address. Monthly PV generation (registers 6227-6238), direct consumption (6417-6428) and
  export (6596-6607) hold values up to October and 0 for November and December. See
  [WiNet-S, the history registers](../entities/device-winet-s.md).
- **The yearly history slots**: 2024-2026 hold totals, and each quantity's 2026 slot equals the
  sum of its monthly values, which places the first slot at 2015 (same page).
- **The forced-charging schedule**, registers 33208-33219: 0x55 (off), days 1, every window
  00:00-00:00, both target SoCs 0.
- **The discharge schedules** as in the earlier readings: weekday window 1 00:00-24:00, window 2
  00:00-00:00 (registers 33151-33158); weekend discharge 0xAA (on, register 33179), window 1
  00:00-24:00, window 2 00:00-00:00 (registers 33180-33187).
- [Register 32998](../entities/register-32998.md), which the owner uses as a site import power limit, holds **950**. No Sungrow
  document describes it; owners measure it in 0.01 kW, so 9.50 kW
  ([discussion #546](discussion-546-site-import-power-limit-summary.md)).

## Contention

Polled by this Home Assistant, held off for the run (16 components). No other client reported.
See [contention](../concepts/contention.md).

## Capability test

Outcome **3**: ran, with checks skipped. Over the cable, so leg B is evidence. See
[the capability test](../concepts/capability-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | matched |
| `battery_reserved_soc_for_backup` | 13100 | not run, too close to the battery's level |
| `battery_max_charge_power` | 33047 | matched |
| `battery_max_discharge_power` | 33048 | matched |
| `export_power_limit` | 13074 | matched |
| `battery_forced_charge_discharge_power` | 13052 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- [13074](../entities/register-13074.md) write scale: **times ten**, by refusal: the held 9500 W
  written back was refused with 0x04 three times. Fourth reading, the same answer.
- Behaviour, PV 0 W, SoC 8.7 %: the forced charge **did as it was told** (before -542 W, during
  1248 W, after -535.5 W, for 1250 W commanded).
- Not checked, all because of the evening and an empty battery: the forced discharge and the
  export limit (8.7 % against a 5 % floor), the charge ceiling, the PV cut (PV 0 W); no restart
  (not asked).
- Restore: every register back and read back.
