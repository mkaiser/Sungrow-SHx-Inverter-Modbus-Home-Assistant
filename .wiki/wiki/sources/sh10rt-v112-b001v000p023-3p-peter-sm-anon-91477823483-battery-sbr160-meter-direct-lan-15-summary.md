---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15.json
ingested: '2026-11-10'
created: '2026-11-10'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventeenth reading

Read 2026-11-10 at 08:07 UTC from Home Assistant with integration 0.1.0a34, posted by Korsberg to
issue #786. It carries five capability test runs: the four of the
[sixteenth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)
and a new one at 08:16 UTC. Committed as the contributor posted it. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-15.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md), firmware `SBRBCU-S_22011.01.30` |

Every component answered. The block read test had five blocks inconsistent in one round and
whole in the other (5008, 31211, 2582, 6227, 6417), with no reconnects.

## Capability test

The new run: outcome **3** (PV 0 W, SoC 82.7 %, in the morning), every word restored.

- Readback: nine of nine matched; [13074](../entities/register-13074.md) probed **times ten**.
- Forced discharge: **could not tell**. 1248 W for 1250 W, but the house was 320 W different
  afterwards, so the input drifted across the measurement.
- Export limit: did as it was told, 1261 W against 1250 W, made by discharging 4380 W (the pack
  accepted 4380 W of 4382 W asked).
- **Forced-charging window: could not tell.** The write of register 33213 (protocol address 33212,
  word 30) lost the connection, and the discharge-window write after it (33154, its end minute)
  too; [the 33213 query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- Write paths, each taken: backup mode, load control, the weekend discharge enable and the second
  forced-charging window, as in the sixteenth reading. EMS modes 2 and 4 were taken; **the write
  of mode 3 (register 13050, protocol address 13049) lost the connection**.
- Upper bounds: `battery_min_soc` refused 51 % and `battery_max_soc` 101 % (0x04). The 8200 W
  write of `battery_max_charge_power` **lost the connection**; `battery_max_discharge_power`,
  `battery_forced_charge_discharge_power` and both start thresholds took values above their
  maximum and stored them, as in the sixteenth reading.
- Restart: stopped in 2.0 s, Running after 271.1 s and generating 6.1 s later; settings survived.
- Not checked: the forced charge (`battery_max_charge_power` held at 10 W), the charge ceiling
  (the battery was discharging), the PV cut (PV 0 W) and both start thresholds (the battery
  moved 1578 W, past the 200-800 W they need).

Folded over the five runs: the forced-charging window, the discharge windows, the forced charge,
the charge ceiling, the PV cut and the charging threshold still missing. No contradictions.
