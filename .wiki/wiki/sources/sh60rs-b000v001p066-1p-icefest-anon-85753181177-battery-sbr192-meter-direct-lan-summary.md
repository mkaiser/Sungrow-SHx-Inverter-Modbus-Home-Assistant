---
type: source
title: sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan.json
ingested: '2026-11-06'
created: '2026-11-06'
tags:
  - survey
  - sh60rs
  - sunstone-h-b000-v001-p066
  - icefest
  - rs485
  - control-test
---

# SH6.0RS, B000.V001.P066, icefest, RS485 through a Waveshare converter

The same inverter as [the WiNet-S reading](sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan-summary.md), read ten minutes later, around
20:17 UTC, **over its RS485 port through a Waveshare RS485-to-Ethernet converter**, as the owner
wrote in issue #786. A diagnostics download from Home Assistant 2026.11.0 and 0.1.0a27, with the
control test and a restart, committed as it was. Source:
`device-survey/results/inverter/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [icefest](../entities/installation-icefest.md) |
| Model | [SH6.0RS](../entities/device-sh-rs.md), `0x0D10` |
| Stand-in serial | `anon-85753181177` |
| Inverter firmware | [`SUNSTONE-H_B000.V001.P066`](../entities/firmware-sunstone-h-b000-v001-p066.md); versions 1-3 `SUNSTONE-H_01011.03.66`, `_03011.02.47`, `_04011.02.03` |
| Transport (owner) | RS485 through a Waveshare converter (the issue's text; the document's own answer is empty) |
| Transport (measured) | "direct to the inverter's LAN port": register 6100 answered |
| Battery | [SBR192](../entities/device-sbr-battery.md) at unit 200, modules 1 to 6 fitted |

**The measurement cannot tell RS485 from the LAN port.** Register 6100 answers on both, so the
verdict, and with it the filename's `direct-lan`, say LAN port for what was an RS485 converter
([transport detection](../concepts/transport-detection.md)). Every component answered, the
battery firmware, the sub-controller and the history included, as on a cable.

**The first SBR192 read on a direct link**: its cell and module blocks answer at unit 200, which
no dongle reading of an SBR192 could show.

## Control test

Outcome **3**: ran, with checks skipped. Over a direct link, so the readbacks are evidence.

- [13074](../entities/register-13074.md) stores a written word as handed, as through the dongle.
- All five readbacks it wrote **matched**: the maximum SoC, the charge and discharge maxima, the
  export limit and the forced power.
- The forced charge **did as it was told**: 1250 W for 1250 W.
- **The forced-charging window's days word (holding 33209) refused with 0x04 here too**, so the
  refusal is the firmware's, not the dongle's.
- Every register restored or already holding its original value, the window's included.
- A restart: 2.1 s to stop, 151 s to run again, generating 14 s after that.
- Not checked: the PV cut (PV under 500 W), the minimum and backup SoC; the charging start powers
  do not answer on this firmware.
