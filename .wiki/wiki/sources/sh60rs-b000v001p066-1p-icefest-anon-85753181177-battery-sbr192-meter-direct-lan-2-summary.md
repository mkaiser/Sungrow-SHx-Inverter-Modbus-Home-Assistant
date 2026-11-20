---
type: source
title: sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2.json
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - diagnosis
  - sh60rs
  - sunstone-h-b000-v001-p066
  - icefest
  - rs485
  - capability-test
---

# SH6.0RS, B000.V001.P066, icefest, RS485 again: the PV cut and the import limit watched

The same inverter as [the first RS485 reading](sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md),
two weeks later (2026-11-20 around 00:16-01:07 UTC, midday in the house), **over the RS485 port through
the Waveshare converter**, as the owner's comment says. A diagnostics download from Home Assistant
2026.11 and 0.1.0a44, posted on #786; its `diagnosis` section committed unchanged (schema 28), with no
register dump or block read test, which a download does not carry. Source:
`device-diagnosis/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Installation | [icefest](../entities/installation-icefest.md) |
| Model | [SH6.0RS](../entities/device-sh-rs.md), `0x0D10` |
| Stand-in serial | `anon-85753181177` |
| Inverter firmware | [`SUNSTONE-H_B000.V001.P066`](../entities/firmware-sunstone-h-b000-v001-p066.md); communication module `WINET-SV200.001.00.P044` (fitted, not in the path) |
| Transport (owner) | RS485 through a Waveshare RS485-to-Ethernet converter |
| Transport (measured) | "direct to the inverter's LAN port": register 6100 answered, as before |
| Battery | [SBR192](../entities/device-sbr-battery.md) at unit 200, modules 1 to 6 fitted, firmware `SBRBCU-S_22011.01.30` |
| Polled meanwhile | by this Home Assistant throughout, 24 components |

## Capability test

Three runs, each outcome **3** (ran, some checks skipped or inconclusive), every register restored or
already holding its original value. Over a direct link, so the readbacks are evidence.

| Check | Before | During | After | Verdict |
| --- | --- | --- | --- | --- |
| **PV generation cut** ([31211](../entities/register-31211.md)), total DC power | 811 W | 0 W | 576 W | did as told |
| **Site import limit** ([32998](../entities/register-32998.md)), 520 W commanded, grid import | 1040 W | 528 W | 1029 W | did as told |
| Export power limit, 1250 W commanded | 3537 W | 1245 W | 3480 W | did as told (export made by discharging 3030 W) |
| Forced discharge, 1250 W | 0 W | 1253 W | 0 W | did as told |
| Forced charge | -5226 W | 1253 W | 0 W | could not tell: the input drifted |

- **The PV cut is watched on P066**: PV was 811 W this time, where it had been under 500 W on
  2026-11-06. Both 31211 and the import limit read back their originals (0x55, 10.0 kW) after every run.
- **The forced-charging window refuses again**: its days word, holding 33209 (protocol 33208 in the
  document's error text), refused with 0x04, as on both earlier readings, and the second window's
  words with it.
- The write paths of backup mode (13075), load control (13011, 13002) and the weekend discharge enable
  (33179) took their words; the discharge window itself was not checked (the battery discharging 0 W).
- The SoC and power maxima refused a word above their bound (50 % minimum SoC, 100 % maximum, 9720 W).
- A restart: stopped after 4.1 s, running again after 162 s, the settings kept.
- EMS modes 0, 3 and 4 taken; 2 held before the run.

## Plausibility

44 observations from 11:00 to 12:07 local. The trackers (median ratio 0.973) and the meter against
export power (0.998) matched. The energy counters' checks, the daily import's among them, needed
three kilowatt-hours of flow and had none: this midday reading says nothing about a daily import that
stays at 0 at night ([#797](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/issues/797)).
