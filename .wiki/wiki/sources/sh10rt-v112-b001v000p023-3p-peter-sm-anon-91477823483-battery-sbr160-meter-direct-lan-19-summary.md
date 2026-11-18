---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19.json
ingested: '2026-11-18'
created: '2026-11-18'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - peter-sm
  - direct_lan
  - capability-test
  - import-limit
---

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-first reading

Read 2026-11-16 at 12:04 UTC from Home Assistant (`command_line`: "home assistant diagnostics",
schema 27), with a capability test run at 12:16 UTC; posted by Korsberg to issue #786 under the
first reading's file name. Committed unchanged as `-19`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19.json`.

| | |
| --- | --- |
| Installation | [peter-sm](../entities/installation-peter-sm.md) |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F`, three phase 3P4L |
| Stand-in serial | `anon-91477823483` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Version 1 / 2 | `SAPPHIRE-H_01011.95.14` / `SAPPHIRE-H_03011.95.14` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR160](../entities/device-sbr-battery.md) at unit 200, five modules, firmware `SBRBCU-S_22011.01.30` |
| At the time | midday, overcast: PV 468 W, load 490 W, SoC 58.4 %, 1.6 kWh generated that day |

The block read test answered 34 blocks in every round and 4 intermittently, with no block
narrowed. The mDNS browse answered again, with the dongle's one `_http._tcp` service and the TXT
layout of the [twentieth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md).
The battery level probe got **no answer** this once, where every other reading here has it
present; the pack's own block at unit 200 answered in the same document, so this is the link's
turn rather than the pack ([a failed read is not a refusal](../concepts/failed-read-is-not-refusal.md)).

## The first site import limit check here (it holds)

The capability test's `--import-limit` check ran at this house for the first time, and
[register 32998](../entities/register-32998.md) **did as it was told on an
[SH10RT-V112](../entities/device-sh-rt.md)**: under a forced charge the house drew 1438 W from
the grid, a cap of 800 W brought import to **768 W**, and it returned to 1450 W when the cap came
off. That is the model of the open report in
[does the import limit hold during a forced charge](../queries/does-the-import-limit-hold-during-a-forced-charge.md),
on the same firmware family, over a cable, with the charge commanded through 13050 and 13051.

The words around the register's range answered almost as at [mkaiser](../entities/installation-mkaiser.md):
**0 refused with exception 0x04**, 5000 taken, and the write of **5001 lost the connection** rather
than drawing a refusal -- this house's recurring answer to a write it will not take.

## The capability test (outcome 3)

Ran, with checks skipped or inconclusive; nothing is left changed, and nothing contradicts an
earlier run.

- **All nine readbacks matched.** [13074](../entities/register-13074.md)'s write scale was
  answered by refusal again: the held 9200 written back drew exception 0x04 three times, so it is
  multiplied by ten.
- **Forced charge 1248 W and forced discharge 1251 W against 1250 W commanded**, both obeyed. The
  house held `battery_max_charge_power` at 10 W through the twelfth to twentieth readings, so this
  is the first forced charge measured here since the third.
- **The export limit acted through the ratio**, not through 13074: feed-in limitation moved from
  92.0 % to 12.5 % of 10000 W rated for a 1250 W cap, and export fell from 2955 W to 1249.5 W and
  back to 2951 W. The export was manufactured by discharging 3270 W; the pack clamped the asked
  3277 W to that, and the check went ahead against what it accepted.
- **EMS mode options 2, 3 and 4 were all taken**, mode 3 included.
- **Write paths**: backup mode (13075), load control (13011, 13002), the weekend discharge enable
  (33179) and the second forced-charging window each took their own words.
- **Upper bounds**: 13059 refuses 51 % and 13058 101 % (exception 0x04); 33047, 33048, 13052,
  33149 and 33150 store a value above their maximum (8200 W over 8100 W, 1010 W over 1000 W), as
  in every reading here since the sixteenth.
- **The charge window's write of 33213 lost the connection**, an eleventh time, and the
  discharge-window write after it lost it on 33154, as in every run since the sixteenth reading
  ([the query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md)).
- **A Modbus restart did as it was told**: stopped in 2.0 s, running 271 s after the start
  command, generating 8.1 s later; settings survived.
- Not measured: the discharge window (the battery was discharging 194 W, under the 500 W a stop
  needs), the charge ceiling (nothing was charging), the PV cut (437 W, under 500 W) and both
  start thresholds (nothing past the battery).
- **Restore**: seven settings written back, each read back on the first attempt; 85 were already
  at their original word.
