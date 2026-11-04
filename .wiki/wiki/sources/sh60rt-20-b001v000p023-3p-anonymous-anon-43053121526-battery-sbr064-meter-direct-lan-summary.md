---
type: source
title: sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan.json
ingested: '2026-11-04'
created: '2026-11-04'
tags:
  - survey
  - sh60rt-20
  - sapphire-h-b001-v000-p023
  - anonymous
  - direct_lan
  - modbus-proxy
---

# SH6.0RT-20, B001.V000.P023, anonymous, through a Modbus proxy, SBR064

Capability survey of one inverter, read 2026-11-04 from Home Assistant's survey button, issue
#786, reads only (no control test). Published as `anonymous`. **The first SH6.0RT-20 in the
corpus.** Source: `device-survey/results/inverter/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan.json`.

| | |
| --- | --- |
| Model | [SH6.0RT-20](../entities/device-sh-rt.md), type code `0x0E11`, three phase 3P4L |
| Stand-in serial | `anon-43053121526` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Version 1 / 2 / 3 | `SAPPHIRE-H_01011.95.14` / `SAPPHIRE-H_03011.95.14` / `SUBCTL-S_04011.01.01` |
| ARM / DSP firmware | `ARM_SAPPHIRE-H_V11_V01_B` / `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P045` |
| Transport (owner) | the inverter's own LAN port, **through a Modbus proxy**, with EVCC polling as well |
| Transport (measured) | direct to the inverter's LAN port, a communication module fitted but not in the path; register 6100 answered |
| Battery | [SBR064](../entities/device-sbr-battery.md) at unit 200, two modules, 6.4 kWh |

## What did not answer

Nothing: every block of the block read test answered in all three rounds, none intermittent, no
reconnects, through the proxy and beside EVCC. MPPT3, MPPT4 and 13018 read the specification's
unavailable value, as on every SH-RT. 31211 and the forced-charging and discharge schedules
(33208, 33151, 33179) answered.

## The battery

`cell_type_module_1` and `_2` are 68 and the rest 0: two modules, the smallest SBR in the corpus.
The [position words](../entities/device-sbr-battery.md) decode consistently: `max_cell_position`
522 = `0x20A`, module 2 cell 10; `min_cell_position` 531 = `0x213`, module 2 cell 19.

Read nearly empty, at 18 °C: **the inverter's battery level reads 1.2 % where the pack's own state
of charge at unit 200 reads 6.3 %**, with the minimum SoC set to 5 %. Other houses' pairs differ by
up to 13 points (14.5 against 27.3 at one); what the inverter's figure is relative to is
not established.

## Settings read

Export limit 4300 W, switched on (0xAA). Active power limitation on at 100 %.
