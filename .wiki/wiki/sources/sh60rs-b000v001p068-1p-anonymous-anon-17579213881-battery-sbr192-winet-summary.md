---
type: source
title: sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet.json
source_path: ../device-survey/results/inverter/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet.json
ingested: '2026-10-31'
created: '2026-10-31'
tags:
  - survey
  - sh60rs
  - sunstone-h-b000-v001-p068
  - anonymous
  - winet
---

# SH6.0RS, B000.V001.P068, anonymous, a WiNet-S

Capability survey of one inverter, read 2026-10-31 from the terminal survey, issue #786, reads
only (`--control-test no`). Published as `anonymous`. The first [SH-RS](../entities/device-sh-rs.md)
in the corpus. The contributor's file carried `-2`, the survey's number for its own second run
("Repeat with Home Assistant and Node-RED Modbus polling stopped"); the first was not sent, so
this one is committed under the plain name. Source:
`device-survey/results/inverter/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet.json`.

| | |
| --- | --- |
| Model | [SH6.0RS](../entities/device-sh-rs.md), type code `0x0D10`, single phase |
| Stand-in serial | `anon-17579213881` |
| Inverter firmware | [`SUNSTONE-H_B000.V001.P068`](../entities/firmware-sunstone-h-b000-v001-p068.md) |
| ARM firmware | `ARM_SUNSTONE-H_V11_V01_A` |
| DSP firmware | `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.03.68` / `SUNSTONE-H_03011.02.48` |
| Battery firmware | `SBRBCU-S_22011.01.30` (see below) |
| Communication module firmware | `WINET-SV200.001.00.P044` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md), medium not given in the document; the issue says a LAN cable |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBR192](../entities/device-sbr-battery.md) (unit 2; the cell and module blocks refused with 0x02), 19.2 kWh |
| Meter | the owner reports an EnergyBridge; 5741 and 5744 refused, as through every WiNet-S |

## What did not answer

The sub-controller (2613) and battery (2629) firmware blocks, every round, refused with 0x02, as
through every WiNet-S. 13018 reads the unavailable value. The whole history block, inputs
6101-6826, did not answer: the dongle refuses it on an RS as on every SH-RT and SH-T.

**Dropped connections with the owner's pollers stopped**: twelve blocks of the block read test
(13000, 5011, 5115, 5242, 5601, 5631, 5720, 13010, 5214, 13200, 13050 and holding 13002) were
answered in some rounds and lost to a dropped connection in others, with no reconnects counted.
See [contention](../concepts/contention.md).

## The battery firmware string

Input 13280-13294 holds `SBRBCU-S_22011.01.30`, a NUL, and then `44` left over from a longer
string. `modbus_connection` strips only trailing NULs, so the reading kept the leftover; the
library now ends a string at its first NUL (`src/sungrow_modbus/model.py`,
`tests/test_text_field.py`). The committed document is as the survey wrote it.

## What the dump adds

- [Register 31211](../entities/register-31211.md) answers **0x55**: SUNSTONE-H joins the
  firmware where it does.
- The forced-charging schedule answers (33208 = 0x55, off).
- The discharge schedules read the same layout as on the SH-RT: weekday window 1 00:00-24:00,
  window 2 00:00-00:00 (33151-33158); weekend discharge 0xAA, window 1 00:00-24:00 (33179-33187).
