---
type: source
title: sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-2.json
source_path: ../device-diagnosis/results/inverter/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-2.json
ingested: '2026-11-09'
created: '2026-11-09'
tags:
  - diagnosis
  - sh60rt-20
  - sapphire-h-b001-v000-p023
  - anonymous
  - direct_lan
  - modbus-proxy
---

# SH6.0RT-20, B001.V000.P023, anonymous, through a Modbus proxy, SBR064, second reading

Read 2026-11-09 at 06:16 UTC from Home Assistant with integration 0.1.0a32, reads only (no
capability test, no register dump), issue #786. Published as `anonymous`. **Taken from a diagnostics download**: its `diagnosis` section is committed as it was, under the
library's own name for it (`custom_components/sungrow_modbus/diagnostics.py`). Source:
`device-diagnosis/results/inverter/sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-2.json`.

| | |
| --- | --- |
| Model | [SH6.0RT-20](../entities/device-sh-rt.md), type code `0x0E11` |
| Stand-in serial | `anon-43053121526` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md), version 1 `SAPPHIRE-H_01011.95.14` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Transport (owner) | the inverter's own LAN port, through a Modbus proxy, with EVCC polling as well |
| Transport (measured) | direct to the inverter's LAN port, a communication module fitted but not in the path; register 6100 answered |
| Battery | [SBR064](../entities/device-sbr-battery.md) at unit 200, modules 1 and 2 |

## What it adds

It repeats the [first reading](sh60rt-20-b001v000p023-3p-anonymous-anon-43053121526-battery-sbr064-meter-direct-lan-summary.md):
the same firmware, all 37 blocks answering with this entry's polling held off, none
intermittent, through the proxy and beside EVCC. Export limit 4300 W, on.

The battery again read nearly empty: the inverter's battery level 0.5 % against the pack's own
state of charge 5.5 % at unit 200, with the minimum SoC at 5 %. The first reading had 1.2 % against
6.3 %. Both gaps are about the minimum SoC. That suggests the inverter counts from the floor, but
two readings at one house do not establish it.
