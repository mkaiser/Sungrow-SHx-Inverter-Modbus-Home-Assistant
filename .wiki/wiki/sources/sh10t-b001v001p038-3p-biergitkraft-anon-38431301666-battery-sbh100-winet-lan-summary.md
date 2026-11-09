---
type: source
title: sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan.json
source_path: ../device-diagnosis/results/inverter/sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan.json
ingested: '2026-11-09'
created: '2026-11-09'
tags:
  - diagnosis
  - sh10t
  - pearl-h-b001-v001-p038
  - biergitkraft
  - winet_lan
---

# SH10T, B001.V001.P038, BiergitKraft, a WiNet-S2 on Ethernet, SBH100

Read 2026-11-08 at 19:09 UTC with `sungrow_diagnosis.py`, posted by BiergitKraft as issue #792.
Two capability test attempts at 19:44 and 19:47 UTC, both refused before writing anything.
**The first SH10T and the first `PEARL-H_B001` firmware in the corpus.** Source:
`device-diagnosis/results/inverter/sh10t-b001v001p038-3p-biergitkraft-anon-38431301666-battery-sbh100-winet-lan.json`.

| | |
| --- | --- |
| Installation | [BiergitKraft](../entities/installation-biergitkraft.md) |
| Model | [SH10T](../entities/device-sh-t.md), type code `0x0E23`, three phase 3P4L, 10 kW |
| Stand-in serial | `anon-38431301666` |
| Inverter firmware | [`PEARL-H_B001.V001.P038`](../entities/firmware-pearl-h-b001-v001-p038.md) |
| Version 1 / 2 | `PEARL-H_01011.01.42` / `PEARL-H_03011.01.42` |
| ARM / DSP firmware | `ARM_PEARL-H_V11_V01_A` / `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.09` |
| Communication module firmware | `WINET-SV300.001.03.P031` (a WiNet-S2, by the owner) |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused; no link drops |
| Battery | [SBH100](../entities/device-sbh-battery.md) at unit 2, capacity 10.13 kWh |
| Meter | DTSU666-20, by the owner |

## What did not answer

What a WiNet-S refuses, as at every other T: 6100, the PV generation and export-from-PV history,
the meter's phase voltages and currents (5741, 5744), Version 3 and Version 4, and the battery and
sub-controller firmware blocks inside the poll. The pack's `sbr_battery_cells` and
`sbr_battery_modules` were refused with 0x02 at unit 2, as at jm493. Units 3 and 248 (wallbox)
and unit 200 did not answer.

All 33 blocks of the poll answered in the block read test, none intermittent, among them
[31211](../entities/register-31211.md) (reads 0x55), 32998, both discharge schedules, the
forced-charging schedule and **33149-33150, the battery start powers**, which the capability table
marks absent on the T.

## Settings read

Minimum SoC 15 %, maximum 90 %, backup reserve 5 %. Export limit 10000 W, on (0xAA). 13018
(PV power limitation) reads 0x55, off. Load adjustment off (0x55). The battery read 15 % on its
own gauge and 0 % as the inverter's battery level, at a minimum SoC of 15 %.

## Capability test

Outcome **2** twice: the inverter reported Standby, PV 0 W after dark,
the battery at its floor, so nothing was written. Through a WiNet-S only the behavioural leg would
have been evidence.
