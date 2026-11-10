---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14.json
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

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixteenth reading

Read 2026-11-09 at 16:40 UTC from Home Assistant with integration 0.1.0a33, posted by Korsberg to
issue #786. It carries four capability test runs: the three of the
[fifteenth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-13-summary.md)
and a new one at 16:57 UTC, **the first ingested run with the write-path checks and the upper
bounds** ([the capability test](../concepts/capability-test.md)). Committed as the contributor
posted it. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14.json`.

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

Every component answered. The block read test had three blocks inconsistent in one round and
whole in the other (13000, 33047, 2582), with no reconnects.

## Capability test

The new run: outcome **3** (PV 0 W, SoC 26.3 %, after dark), every word restored.

- Readback: eight of nine matched; [13074](../entities/register-13074.md) probed **times ten**.
  `battery_min_soc`'s write (register 13059, protocol address 13058) **lost the connection**.
- Forced discharge: did as it was told, 1250 W for 1250 W.
- Export limit: did as it was told, 1250.5 W against 1250 W, made by discharging 3410 W. The
  feed-in limitation ratio read 92.0 % before and 12.5 % during, 1250 W of the 10000 W rating.
- Discharging start threshold: did as it was told, 1000 W commanded against a 720 W discharge,
  which went to 0 W and back to 718 W.
- **Forced-charging window: could not tell.** The write of register 33213 (protocol address 33212,
  word 3) lost the connection, and the discharge-window write after it too;
  [the 33213 query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- Write paths, each taken: backup mode (13075, its own word 0x55), load control (13011 0x55,
  13002 3), the weekend discharge enable (33179, 0xAA), and the second forced-charging window
  (six registers read back as written, schedule off). EMS modes 2, 3 and 4 were taken; 0 was the
  mode held.
- Upper bounds: `battery_max_soc` refused 101 % (0x04). **Five bounds are not enforced**:
  `battery_max_charge_power`, `battery_max_discharge_power` and
  `battery_forced_charge_discharge_power` took and stored 8200 W above their 8100 W maximum,
  and the two start thresholds took and stored 1010 W above 1000 W.
- Restart: stopped in 2.0 s, Running after 363.4 s; settings survived.
- Not checked: the forced charge (`battery_max_charge_power` held at 10 W), the charge ceiling
  (the battery too low), the PV cut (PV 0 W), the charging threshold (the battery was
  discharging), and the upper bound of `battery_min_soc` (51 % was not well below the level).

Folded over the four runs: the forced-charging window, the discharge windows, the forced charge,
the charge ceiling, the PV cut, the charging threshold and `battery_min_soc`'s upper bound still
missing. No contradictions.
