---
type: source
title: sg5-0rs-1p-bleughb-anon-85541281016.json
source_path: ../device-survey/results/string_inverter/sg5-0rs-1p-bleughb-anon-85541281016.json
ingested: '2026-11-04'
created: '2026-11-04'
tags: [survey, string-inverter, sg5-0rs, bleughb, winet_wlan]
---

# SG5.0RS, bleughb, "South", a WiNet-S on WiFi

The first string-inverter survey. A Home Assistant diagnostics download of 0.1.0a25, issue #786,
read 2026-11-04, its `data.survey` section committed unchanged. The first of
[bleughb](../entities/installation-bleughb.md)'s two [SG5.0RS](../entities/device-sg-rs.md); the
second is [anon-91627862515](sg5-0rs-1p-bleughb-anon-91627862515-summary.md).

| | |
| --- | --- |
| Model | [SG5.0RS](../entities/device-sg-rs.md), type code `0x2606`, single phase |
| Stand-in serial | `anon-85541281016` |
| ARM / DSP firmware | `ARM_SUNSTONE-S_V11_V01_A` / `MDSP_SUNSTONE-S_V11_V01_A` |
| Transport | a [WiNet-S](../entities/device-winet-s.md) on WiFi, unit 1, port 502; "other pollers: an energy meter DTSU66" |
| Read at | 13:14 on the inverter's clock, 5163 W on DC, 4815 W on AC, work state 0 (run) |

## What answered

- **The whole read block**: input 4949-5228 and 7012-7031 (300 words), holding 4999-5048. Only
  input 4989-4998, the serial, is blanked, and holding 5019 read nothing
  (`register_dump` in the document).
- **Two MPPTs**: 231.3 V at 11.2 A and 232.3 V at 11.0 A; MPPT3 to MPPT12 read 0.
- **The meter block (input 5083-5104) answers 0 throughout**: the DTSU66 is read by
  another poller, not by the inverter. Zero here is not evidence of a capability
  ([zero means absent](../concepts/zero-means-absent.md)).
- **The per-string block at input 7012-7031 reads 0** while MPPT1 carries 11.2 A: it answers
  but holds nothing usable on this machine.
- **Holding 5006 reads 170 (`0xAA`, power limitation on) and 5007 reads 1000 (100.0 %)**;
  5009 reads 85 (export limit off) and 5010 reads 500. See
  [the owner's note](bleughb-sg-power-limitation-registers-786-summary.md).
- Bus voltage 380.5 V, grid frequency 49.96 Hz, `total_pv_generation_precise` 21826.7 kWh.
- The inverter's clock is holding 4999-5004 (2026-11-04 13:14:21).

## What did not answer

Holding 5019, and input 4989-4998, blanked on purpose. No refusal pattern appeared through the
WiNet-S: every other block read in one round.
