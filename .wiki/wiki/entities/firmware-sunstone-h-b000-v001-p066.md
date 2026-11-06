---
type: entity
title: SUNSTONE-H_B000.V001.P066
tags: [firmware, sunstone-h-b000-v001-p066]
created: '2026-11-06'
---

# SUNSTONE-H_B000.V001.P066

[SH-RS](device-sh-rs.md) firmware. Version 1 reads `SUNSTONE-H_01011.03.66`. Read at
[icefest](installation-icefest.md) through a [WiNet-S](device-winet-s.md) and over RS485.

- [Register 13074](register-13074.md) stores a written word as handed (1:1).
- [Register 31211](register-31211.md) answers 0x55; the PV cut has not been watched here (PV
  under 500 W).
- The forced-charging window's days word, holding 33209, refuses a write with 0x04, on both paths.
- The forced charge acts as commanded; a restart takes about 2 s to stop and 150-165 s to run.
- The charging start powers do not answer.

## Surveys

- [SH6.0RS, B000.V001.P066, icefest, a WiNet-S on Ethernet](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-winet-lan-summary.md)
- [SH6.0RS, B000.V001.P066, icefest, RS485 through a Waveshare converter](../sources/sh60rs-b000v001p066-1p-icefest-anon-85753181177-battery-sbr192-meter-direct-lan-summary.md)
