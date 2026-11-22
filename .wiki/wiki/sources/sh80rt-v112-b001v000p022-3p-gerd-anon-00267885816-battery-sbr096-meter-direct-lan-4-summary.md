---
type: source
title: sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4.json
source_path: ../device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4.json
ingested: '2026-11-22'
created: '2026-11-22'
tags:
  - diagnosis
  - sh80rt-v112
  - sapphire-h-b001-v000-p022
  - gerd
  - direct_lan
  - plausibility
  - capability-test
---

# SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, fourth reading

Downloaded from gerd's own Home Assistant on 2026-11-22 (a read-only *Diagnosis: start* on the
branch build, through the Modbus proxy on his host), so it carries the integration's kept state
beside the reading: the one capability-test run left in the ledger, from 2026-11-21 evening, and
the plausibility checks over 1706 polls from 2026-11-21 00:46 to 2026-11-22 08:58 CET. Schema 28.
Source: `device-diagnosis/results/inverter/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4.json`.

| | |
| --- | --- |
| Installation | [gerd](../entities/installation-gerd.md) |
| Firmware | [P022](../entities/firmware-sapphire-h-b001-v000-p022.md), WiNet-S `WINET-SV200.001.00.P043`, battery `SBRBCU-S_22011.01.30` |
| Transport | direct LAN through a Modbus proxy |

| Claim | Evidence | Status |
| --- | --- | --- |
| The kept capability run is the evening run of 2026-11-21 | outcome 0; 25 of 31 rows established, 11 "did as it was told", 9 readbacks matched, 5 nothing measurable, no contradiction | already described in [the evening](gerd-t076-2026-11-21-summary.md) |
| Every established plausibility check matches | power balance 1.000, battery V x I 0.985, tracker V x I 0.963, phase V x I 1.002, meter phases 0.998, meter against export 1.000 (240 observations each, phases 141) | 1706 polls |
| The daily counters follow power | PV 1.003, import 0.979 over 7 trails; battery charge 1.008, discharge 0.986 over 4 | trails |
| Lifetime counters agree with the daily ones | PV and import 1.000 | 2-3 trails |
| Lifetime counters never fall and contain each other; the daily counters reset at 00:01 | 1697 events, none against; one midnight | 1706 polls |
| Running states over a day and a half | Standby 929, Starting 3, Running 774 polls, nothing else | 1706 polls |
| Export and the PV/battery lifetime pairs are not established | 0-1 of the 2-3 trails needed: a November house exports little | waiting |

The running-state tally fits [the night of 2026-11-22](gerd-forced-startup-and-restart-2026-11-22-summary.md):
the battery at its minimum keeps this inverter in Standby through the dark.
