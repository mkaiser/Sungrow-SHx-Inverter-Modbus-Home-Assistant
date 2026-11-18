---
type: source
title: sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20.json
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

# SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port, twenty-second reading

Read 2026-11-16 at 13:23 UTC from Home Assistant on integration 0.1.0a43 (`command_line`: "home
assistant diagnostics", schema 28), with a capability test run at 13:35 UTC, 79 minutes after the
[twenty-first reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md);
posted by Korsberg to issue #786 under the first reading's file name. Committed unchanged as
`-20`. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20.json`.

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
| At the time | early afternoon, overcast: PV 291 W, load 1329 W, SoC 50.6 %, 2.1 kWh generated that day |

The block read test answered 33 blocks in every round and 5 intermittently, with no block
narrowed.

## The first schema-28 document

The first committed diagnosis written by schema 28. Beside schema 27 its `network_names` section
adds two fields: **`services_heard`**, 15 here against the one service that belongs to this
machine, and **`on_device_segment`**, true -- Home Assistant and the inverter share a subnet, which
is what makes a multicast browse possible at all. The dongle's TXT record is unchanged from the
[twentieth reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md).

## The site import limit holds a second time

[Register 32998](../entities/register-32998.md) obeyed again, at a different size: under a forced
charge the house drew 2359 W, a cap of 1730 W brought import to **1702 W**, and it went to 2423 W
when the cap came off. With the
[twenty-first reading](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md)
that is two caps on one SH10RT-V112, two sizes, both held. The range words answered as before: 0
refused with 0x04, 5000 taken, 5001 lost the connection.

## The capability test (outcome 3)

Ran, with checks skipped or inconclusive; nothing is left changed, and nothing contradicts an
earlier run. The document carries three runs: the twentieth reading's, the twenty-first's and
this one's.

- **All nine readbacks matched**, and [13074](../entities/register-13074.md)'s write scale was
  answered by refusal again (the held 9200, exception 0x04 three times): multiplied by ten.
- **Forced charge 1248 W and forced discharge 1249 W against 1250 W commanded**, both obeyed.
- **The export limit acted through the ratio** again: 92.0 % to 12.5 % for a 1250 W cap, export
  2784 W before, 1253 W during, 2843 W after, made by discharging 4040 W (the pack clamped the
  asked 4047 W).
- **EMS mode 3's write lost the connection this run** (register 13050), where the twenty-first
  reading took it. Modes 2 and 4 were taken. The merged `effects` row carries the earlier run's
  result, so the run's own `conditions` is where this failure shows -- the third time mode 3 has
  dropped the link here.
- **Write paths and upper bounds** repeated exactly: backup mode, load control, the weekend
  discharge enable and the second forced-charging window took their own words; 13059 refuses 51 %
  and 13058 101 %; 33047, 33048, 13052, 33149 and 33150 store values above their maxima.
- **The charge window's write of 33213 lost the connection**, a twelfth time, and the
  discharge-window write after it lost it on 33154
  ([the query](../queries/does-writing-33213-drop-the-link-at-peter-sm.md)).
- **A Modbus restart did as it was told**: stopped in 2.0 s, running 271 s after the start
  command, generating 10.2 s later; settings survived. The eleventh restart measured here, and the
  sixth to come back at 271 s.
- Not measured: the charge ceiling (the battery is too low for it, since `battery_max_soc` will
  not go below 50 %), the PV cut (258 W, under 500 W) and both start thresholds.
- **Restore**: eleven settings written back, each read back on the first attempt; 127 were
  already at their original word.
