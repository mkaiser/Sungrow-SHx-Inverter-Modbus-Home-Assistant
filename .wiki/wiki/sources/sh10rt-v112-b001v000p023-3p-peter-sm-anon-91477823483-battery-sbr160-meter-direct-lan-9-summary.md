---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-9.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-9.json
ingested: '2026-11-09'
created: '2026-11-09'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, eleventh reading

Read 2026-11-07 at 18:24 UTC from Home Assistant, posted by Korsberg to issue #786. Reads only:
no capability test, no register dump. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-9.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md) |

## What did not answer

Every component answered. The block read test, with this entry's polling held off, answered 33
blocks; `fast_holding`, `medium_input`, `slowest_input` and `pv_generation_history` answered
only some of the time.

## What it adds

Nothing new about the device: the same firmware, the same components answering, as the
[tenth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan-summary.md).
[Register 32998](../entities/register-32998.md) reads 9.9 kW.
