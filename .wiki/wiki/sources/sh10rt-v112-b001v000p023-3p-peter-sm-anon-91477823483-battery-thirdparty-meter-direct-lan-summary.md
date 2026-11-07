---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan.json
ingested: '2026-11-07'
created: '2026-11-07'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - control-test
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, tenth reading, with a control test

Capability survey of one inverter, read 2026-11-07 around 08:24 UTC from Home Assistant 2026.11.0
with integration 0.1.0a27, posted by Korsberg to issue #786 with the
[ninth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-8-summary.md).
**Taken from a diagnostics download** whose `survey` section carries the control test the last
run made; that section is committed as it was, under the library's own name for it. Source:
`device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-thirdparty-meter-direct-lan.json`.

**The name says `battery-thirdparty`, and the battery is the SBR160.** The section has no
`battery_pack`, so `label_for` falls back to the battery registers answering on a direct path,
which is how it names a third-party pack. The BCU firmware `SBRBCU-S_22011.01.30` and the
installation's other nine readings say otherwise. Why the pack's section is missing is not in the
document: the survey publishes without a step it lost, and records no failure.

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
| Battery | [SBR160](../entities/device-sbr-battery.md), by the BCU and the owner; its own section missing |

## What did not answer

Every component answered.

## Contention

Polled by this Home Assistant throughout the download. See [contention](../concepts/contention.md).

## Control test

Outcome **3**: ran, with checks skipped or inconclusive. Over the cable, so leg B is evidence.
PV 440 W, SoC 82.6 %. See [the control test](../concepts/control-test.md).

All nine readbacks **matched**: 13059, 13058, 13100, 33047, 33048, 13074, 13052, 33149 and 33150.

- [13074](../entities/register-13074.md) write scale: **times ten**, by refusal: the held 9200 W
  written back was refused with 0x04 three times.
- **The forced-charging window could not be told: the connection was lost writing register
  33213** (window 1's end minute, word 36), the same write as in the
  [sixth](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-5-summary.md)
  and [seventh](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-6-summary.md)
  readings; [open](../queries/does-writing-33213-drop-the-link-at-peter-sm.md).
- **The discharge windows away from now could not be told**: a raw write refused with an
  exception, which the document does not name.
- The forced discharge **could not be told**: the house drifted 392 W across the measurement.
- Not checked: the forced charge (the house holds `battery_max_charge_power` at 10 W), the charge
  ceiling (the battery was not charging), the export limit (409 W of export, under the 1812 W a
  cap needs) and the PV cut (PV 437 W, under 500 W).
- **Restart: the inverter did as it was told.** Stopped 2.0 s after the stop command, running
  again 269 s after the start, every setting surviving, no poll refused.
- Restore: every register back and read back. Four words needed a restore write: window 1's start
  hour, start minute and end hour (33210-33212) and the weekday discharge window's end hour.
