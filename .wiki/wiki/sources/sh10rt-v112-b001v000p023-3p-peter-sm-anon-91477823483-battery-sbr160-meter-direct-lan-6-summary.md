---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, seventh reading

Capability survey of one inverter, read 2026-11-02 around 12:37 UTC from Home Assistant, issue #786,
with the full control test. Two readings of this installation were posted together that day; by
their read times this is the seventh (`-6`). Source:
`device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6.json`.

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

No block failed in every round. **Intermittent**, over three rounds: 13002 (17), 33151 (8), 2582 (26) and 6227 (53).

## Contention

Polled by this Home Assistant, held off for the run (22 components). See
[contention](../concepts/contention.md).

## Control test

Outcome **3**: ran, with checks skipped. Over the cable, so leg B is evidence. See
[the control test](../concepts/control-test.md).

All nine readbacks **matched**: 13059, 13058, 13100, 33047, 33048, 13074, 13052, 33149 and 33150.

- [13074](../entities/register-13074.md) write scale: **times ten**, by refusal: the held 9200 W
  written back was refused with 0x04 three times.
- Behaviour, PV about 300 W, SoC about 47 %, before, during and after, for 1250 W commanded:
  - the forced charge **did as it was told** (-301, 1248, -307 W);
  - the forced discharge **did as it was told** (317, 1250, 300 W);
  - the export limit **did as it was told** (export 2851, 1248, 2850.5 W, the export made by a 3240 W discharge).
- **The forced-charging window could not be told: the connection was lost writing register
  33213** (window 1's end minute, word 1), after window 1's start hour, start minute and end hour (33210-33212) had been written and
  before the enable. The same write lost the connection in both of the day's readings; see [contention](../concepts/contention.md).
- Not checked: the charge ceiling (the battery is below the 50 % `battery_max_soc` can be set
  to), the PV cut (PV under 500 W), the discharge window (the battery discharging under 500 W);
  no restart (not asked).
- Restore: every register back and read back; the three window words needed a restore write.
