---
type: source
title: sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan.json
ingested: '2026-11-04'
created: '2026-11-04'
tags:
  - survey
  - sh5.0rt-v112
  - sapphire-h-b001-v000-p023
  - mahagon
  - direct_lan
---

# SH5.0RT-V112, B001.V000.P023, mahagon, the inverter's own LAN port

Capability survey of one inverter, read 2026-11-04 around 10:15 UTC, read only (no control
test), issue #786, with the owner's YAML package polling during the run. **The first SH5.0RT-V112
in the corpus**, and the first 5 kW machine on `.95.14`. Source:
`device-survey/results/inverter/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [mahagon](../entities/installation-mahagon.md) |
| Model | [SH5.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0C`, three phase 3P4L |
| Stand-in serial | `anon-11187075801` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Version 1 / 2 / 3 | `SAPPHIRE-H_01011.95.14` / `SAPPHIRE-H_03011.95.14` / `SUBCTL-S_04011.01.01` |
| ARM / DSP firmware | `ARM_SAPPHIRE-H_V11_V01_B` / `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.21` |
| Communication module firmware | `WINET-SV200.001.00.P038` (a WiNet-S2, fitted but not in the path) |
| Transport | the inverter's own LAN port; 6100 answered; one link drop |
| Battery | [SBR096](../entities/device-sbr-battery.md) at unit 200, three modules, 9.6 kWh |
| Answered | 236 of 245 fields |

## What did not answer

Nothing was refused or lost for good. In three rounds 30 blocks were read **inconsistently** in
one round and fine in another (among them 13000, 5011, 13002, 33047, 31213, 33208), and 5242
and 31211 only in the inconsistent outcome; the owner's YAML package was polling. See
[contention](../concepts/contention.md). MPPT3 and MPPT4 and 13018 read the specification's
unavailable value, as on every SH-RT cable survey.

## Settings and readings

- Rated output 5000 W; nominal power register 5001 reads 50. The export limit reads 6020 W with
  a maximum of 6020 W (the register's own maximum, on a 5 kW machine), minimum 0, switched on
  (0xAA).
- [31211](../entities/register-31211.md) reads 0x55: the PV cut is available on P023.
- Battery: SoC 42.8 % at the inverter against 45.9 % in the pack at unit 200, SoH 98 %,
  19.5 degrees C; three modules (`cell_type_module_1` to `_3` read **1**, the rest 0). The cell
  spread is 7.6 mV. The pack is the [SBR](../entities/device-sbr-battery.md) layout seen at
  other SBR096 houses.
- The history block answers whole (yearly PV 4486.9, 21774.7 and 7578.8 kWh for 2024, 2025,
  2026).

## Export scale

The one-write probe ([register 13074](../entities/register-13074.md)) was **refused with
exception 0x04 three times**: this firmware multiplies a written word, so writing the held 6020
back would be 60200 W. The refusal separates "stored as handed" from "multiplied", **not ten
from another factor**: 0.1 % of the 5000 W rating, a step of 5 W, would give 30100 W, also above
the 6020 W maximum, so it is refused too. That distinction waits for a control test on this size.
