---
type: source
title: sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan.json
source_path: ../device-survey/results/inverter/sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan.json
ingested: '2026-11-01'
created: '2026-11-01'
tags:
  - survey
  - sh10rs
  - sunstone-h-b000-v002-p059
  - anonymous
  - winet
---

# SH10RS, B000.V002.P059, anonymous, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-11-01 from the terminal survey, issue #786, reads
only (`--control-test no`), with the owner's other pollers running. Published as `anonymous`.
Source: `device-survey/results/inverter/sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan.json`.

| | |
| --- | --- |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-27241675299` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P059`](../entities/firmware-sunstone-h-b000-v002-p059.md) |
| ARM / DSP firmware | `ARM_SUNSTONE-H_V11_V01_A` / `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.02.61` / `SUNSTONE-H_03021.01.12` |
| Battery firmware | `SBRBCU-S_22011.01.27`, with bytes after its NUL |
| Communication module firmware | `WINET-SV300.001.03.P024` |
| Transport | a [WiNet-S](../entities/device-winet-s.md) on Ethernet; 6100 refused |
| Battery | [SBR](../entities/device-sbr-battery.md) at unit 2 (cell and module blocks refused with 0x02) |
| PV | four MPPTs answer |

## What did not answer

2613 and 2629 every round (0x02), and the meter phase registers 5741 and 5744, as through every
WiNet-S. 13018 reads the unavailable value. **With the owner's pollers running**, holding 13002,
13050, 33047, 33149, 31211 and 33208 were refused with an exception in some rounds and answered in
others: the pattern of a [busy WiNet-S](../queries/does-a-busy-winet-s-refuse-with-0x04.md). See
[contention](../concepts/contention.md).

## What the dump adds

- [Register 31211](../entities/register-31211.md) answers **0x55**.
- The forced-charging schedule answers (33208 = 0x55, off); the discharge schedules have the SH-RT
  layout, with weekend discharge off (33179 = 0x55).
- 13074 holds 10000 W with feed-in limitation off (13087 = 0x55); register 32998 reads 1300, as at
  [Jam3s97](sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan-summary.md)'s SH10RS.

## The pack's capacity does not fit its voltage

5639 reads **32.0 kWh**, more than any single SBR (the largest, SBR256, is 25.6 kWh in `src/sungrow_modbus/battery/power.py`), while the pack reports
331.9 V and SoC 79.4 %, about what six or seven modules give. Two packs, or a capacity the inverter
reports wrongly; the document cannot tell which.
