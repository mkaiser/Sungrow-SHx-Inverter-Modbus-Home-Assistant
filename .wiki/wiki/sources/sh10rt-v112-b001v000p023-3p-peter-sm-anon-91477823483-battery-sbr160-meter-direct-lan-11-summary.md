---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11.json
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

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, thirteenth reading

Read 2026-11-08 at 14:58 UTC from Home Assistant with integration 0.1.0a30 and a capability test,
posted by Korsberg to issue #786. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-11.json`.

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

Outcome **3**, one run at 15:12 UTC (PV 0 W, SoC 57.6 %); every word restored. See
[the capability test](../concepts/capability-test.md).

- Readback: nine of nine matched; [13074](../entities/register-13074.md) probed **times ten**
  (9200 W written back refused with 0x04 three times).
- Forced discharge: did as it was told, 1250 W for 1250 W commanded.
- Export limit: did as it was told, export held at 1249 W against 1250 W, made by discharging
  3220 W.
- **Forced-charging window: could not tell.** The write of register 33213 (protocol address 33212,
  word 21) lost the connection again; [the 33213 query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md). The discharge-window check that followed could not
  write either, reported then as a refusal.
- No forced charge check (`battery_max_charge_power` held at 10 W), no charge ceiling (the
  battery was discharging), no PV cut (PV 0 W).
- Restart: stopped in 2.0 s, Running after 301.3 s, settings survived.
