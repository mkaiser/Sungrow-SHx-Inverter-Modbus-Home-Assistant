---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21.json
ingested: '2026-11-22'
created: '2026-11-22'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
  - restart
  - plausibility
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-third reading

Read 2026-11-21 at 20:33 UTC from Home Assistant (`command_line`: "home assistant diagnostics",
schema 28; the integration's version is not recorded), posted by Korsberg to issue #786 under the
first reading's file name. Committed unchanged as `-21`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-21.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F`, three phase 3P4L |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Version 1 / 2 | `SAPPHIRE-H_01011.95.14` / `SAPPHIRE-H_03011.95.14` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path |
| Battery | [SBR160](../entities/device-sbr-battery.md) at unit 200, five modules, firmware `SBRBCU-S_22011.01.30` |
| At the time | evening, dark: PV 0 W, load 423 W, SoC 0.0 %, running state `0x0008` Standby; that day 0.0 kWh generated, 26.4 kWh imported |

The block read test answered 32 blocks in every round and 6 intermittently, with no block
narrowed and no reconnect.

## Five runs, two of them new

The document carries five capability runs. The first three are the twentieth to twenty-second
readings' ([the twenty-second](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20-summary.md)
has the last of them). New here:

- **Run 4, 2026-11-18 at 18:42 UTC, outcome 5**, after dark with PV 0 W and the pack at 1.0 %,
  under its 5 % minimum. Before it the inverter was still running, discharging 2045 W.
- **Run 5, 2026-11-21 at 20:33 UTC, outcome 2**: refused, the inverter in Standby.

## Outcome 5 was the restart, and the house was not left changed

Every one of run 4's 46 restore writes read back on the first attempt. The 5 is the restart's:
the stop was answered within 0.002 s with the word `0x0008` (Standby), and after the start command
the inverter never reported Running within the deadline. The result reads "the link dropped",
"the inverter did not come back; run --start-only", but **no poll was refused**
(`polls_refused_connection` 0): the link did not drop.

What the inverter did instead is what an SH10RT does with an empty battery after dark: it waits in
Standby, because there is nothing to run on. It would have gone there within minutes without the
test. The [restart](../concepts/capability-test.md) cannot be told from a lost start in this
state, and labels it a dropped link and a house left changed.

**The inverter ran again afterwards.** The document's plausibility section covers
2026-11-18 14:37 to 2026-11-21 21:32 local time, 211 observations, about one every 22 minutes.
Its running states are `0x0040` Running 154 times and `0x0008` Standby 57 times, and the
*phase voltage times current* check matched over the same 154 observations with the inverter
delivering at least 1000 W. About 14 of the observations fall before run 4, so most of the
Running ones come after it. On 2026-11-21 the word is Standby, not the key stop `0x0002` a
Modbus stop leaves ([register 13000](../entities/register-13000.md)).

PV in those days was slight: lifetime PV generation rose from 24869.6 kWh (the twenty-second
reading, 2026-11-16) to 24872.7 kWh, November's month counter (6237) from 76.1 to 79.2 kWh, and
the plausibility section never saw PV above 300 W.

## The rest of run 4

- **All nine readbacks matched**; [13074](../entities/register-13074.md)'s write scale answered
  again: multiplied by ten.
- **The charge window's write of 33213 lost the connection**, a thirteenth time, with word 51
  ([the query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md)).
- **EMS mode 3's write lost the connection** (13050), a fourth time; mode 2 was taken.
- **Write paths and upper bounds** as before: backup mode, load control, the weekend discharge
  enable and the second forced-charging window took their own words; 13058 refuses 101 %;
  33047, 33048, 13052, 33149 and 33150 store values above their maxima.
- Not measured, for want of sun or charge: the PV cut, the charge ceiling, both start thresholds
  and the discharge windows.

## Plausibility, the first from this house

Over the 211 observations: the power balance matched (median ratio 0.945 over 208), battery
voltage times current 0.984 and phase voltage times current 0.985 (154 each), the meter's phases
add up (0.999) and agree with export power (1.000, 57 each). Every check that needs PV or a few
kilowatt-hours on a daily counter waits, as does every check that needs a day of polls.
