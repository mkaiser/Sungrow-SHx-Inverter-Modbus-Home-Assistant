---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16.json
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

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eighteenth reading

Read 2026-11-10 at 14:56 UTC from Home Assistant with integration 0.1.0a36, posted by Korsberg to
issue #786. It carries **one** capability test run, at 15:12 UTC: the runs of the earlier
readings are not in it, so its folded summary is this run alone. Committed as the contributor
posted it. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-16.json`.

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
whole in the other (5720, 33149, 33179, 13250, 6417), with no reconnects.

## Capability test

Outcome **3** (PV 0 W, SoC 59.2 %, in the afternoon), every word restored.

- Readback: nine of nine matched; [13074](../entities/register-13074.md) probed **times ten**.
- Forced discharge: **could not tell**, 1250 W for 1250 W but the house 178 W different
  afterwards.
- Export limit: did as it was told, 1251 W against 1250 W, made by discharging 3440 W (the pack
  accepted 3440 W of 3444 W asked).
- Discharging start threshold: did as it was told, a 798 W discharge went to 0 W and back to
  791 W under a 1000 W threshold.
- **Forced-charging window: could not tell.** The write of register 33213 (protocol address 33212,
  word 19) lost the connection, and the discharge-window write after it (33155, window 2's start
  hour) too; [the 33213 query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- Write paths as in the seventeenth reading, **mode 3's write of 13050 lost the connection
  again**, and so did the 8200 W write of `battery_max_charge_power`. `battery_min_soc` refused
  51 % and `battery_max_soc` 101 %; the other four bounds took values above their maximum and
  stored them.
- Restart: stopped in 2.0 s, Running after 303.3 s; settings survived.
- Not checked: the forced charge (`battery_max_charge_power` held at 10 W), the charge ceiling
  (the battery was discharging), the PV cut (PV 0 W) and the charging threshold.
