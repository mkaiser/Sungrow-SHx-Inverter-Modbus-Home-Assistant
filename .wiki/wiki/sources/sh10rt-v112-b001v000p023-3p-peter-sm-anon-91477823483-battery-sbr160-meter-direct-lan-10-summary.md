---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10.json
ingested: '2026-11-09'
created: '2026-11-09'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twelfth reading

Read 2026-11-08 at 07:39 UTC from Home Assistant with a capability test, posted by Korsberg to
issue #786. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). No register dump. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-10.json`.

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

## Capability test

Outcome **3**, one run, before sunrise (PV 0 W, battery level 0.0 %); every word restored. See
[the capability test](../concepts/capability-test.md).

- Readback: seven matched, [13074](../entities/register-13074.md) among them, probed **times
  ten**; the minimum SoC and the backup reserve not written, the battery being too close to every
  admissible value.
- **Forced-charging window: could not tell.** Its write of register 33213 (protocol address 33212,
  word 59) lost the connection, as in the sixth, seventh and tenth readings; [the 33213 query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- No forced charge check: the house held `battery_max_charge_power` at 10 W. No forced
  discharge, export, charge-ceiling, discharge-window or PV cut check: the battery was empty and
  PV was 0 W.
- Restart: stopped in 2.0 s, Running after 271.0 s, settings survived.
