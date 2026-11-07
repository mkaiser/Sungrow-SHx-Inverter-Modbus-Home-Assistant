---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, sixth reading

Capability diagnosis of one inverter, read 2026-11-02 around 12:25 UTC from Home Assistant, issue #786,
with the full capability test. Two readings of this installation were posted together that day; by
their read times this is the sixth (`-5`). Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | not determined: register 6100 got no answer, so the route could not be told. The owner names the cable, and the next reading, 13 minutes later, saw 6100 answer |
| Battery | [SBR160](../entities/device-sbr-battery.md) (unit 200, five modules) |

## What did not answer

No block failed in every round. **Intermittent**, over three rounds: 5601 (8), 5008 (1), 5622 (18) and 2629 (15).

## Contention

Polled by this Home Assistant, held off for the run (22 components). See
[contention](../concepts/contention.md).

## Capability test

Outcome **3**: ran, with checks skipped. Over the cable, so leg B is evidence. See
[the capability test](../concepts/capability-test.md).

All nine readbacks **matched**: 13059, 13058, 13100, 33047, 33048, 13074, 13052, 33149 and 33150.

- [13074](../entities/register-13074.md) write scale: **times ten**, by refusal: the held 9200 W
  written back was refused with 0x04 three times.
- Behaviour, PV about 300 W, SoC about 47 %, before, during and after, for 1250 W commanded:
  - the forced charge **did as it was told** (0, 1248, -123 W);
  - the forced discharge **did as it was told** (126, 1250, 53.5 W);
  - the export limit **did as it was told** (export 2926, 1257, 2937 W, the export made by a 3110 W discharge).
- **The forced-charging window could not be told: the connection was lost writing register
  33213** (window 1's end minute, word 49), after window 1's start hour, start minute and end hour (33210-33212) had been written and
  before the enable. The same write lost the connection in both of the day's readings; see [contention](../concepts/contention.md).
- Not checked: the charge ceiling (the battery is below the 50 % `battery_max_soc` can be set
  to), the PV cut (PV under 500 W), the discharge window (the battery discharging under 500 W);
  no restart (not asked).
- Restore: every register back and read back; the three window words needed a restore write.
