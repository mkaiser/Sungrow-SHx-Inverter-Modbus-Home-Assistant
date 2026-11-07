---
type: source
title: sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-winet-wlan.json
source_path: ../device-diagnosis/results/inverter/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-winet-wlan.json
ingested: '2026-11-04'
created: '2026-11-04'
tags:
  - diagnosis
  - sh5.0rt-v112
  - sapphire-h-b001-v000-p023
  - mahagon
  - winet_wlan
---

# SH5.0RT-V112, B001.V000.P023, mahagon, a WiNet-S2 on WiFi

The same inverter as the [cable reading](sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md),
read through its WiNet-S2 (`WINET-SV200.001.00.P038`) eight minutes later, 2026-11-04 around
10:23 UTC, read only, issue #786, the owner's YAML package polling the cable meanwhile. Source:
`device-diagnosis/results/inverter/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [mahagon](../entities/installation-mahagon.md) |
| Model | [SH5.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0C` |
| Stand-in serial | `anon-11187075801` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md), version 1 `SAPPHIRE-H_01011.95.14` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md)-family module (WiNet-S2) over WiFi |
| Transport (measured) | through a communication module; **6100 refused** |
| Battery | [SBR096](../entities/device-sbr-battery.md) at unit 2; the cell and module blocks refused |
| Answered | 161 of 245 fields; no link drop, nothing intermittent |

## What did not answer

Refused with an exception in all three rounds: the battery (2629) and sub-controller (2613)
firmware blocks, the three history blocks (6227, 6417, 6596), 6100 and the meter phase registers
(5741, 5744). MPPT3 and MPPT4 read **0** here and the unavailable value on the cable: the
dongle's zero, see [zero means absent](../concepts/zero-means-absent.md). The pack at unit 2
answers its summary (SoC 47.4 %, SoH 98 %, 19.6 degrees C, 199.2 V) and refuses its cells and
modules, as at every other dongle house; the pack's SoC again sits above the inverter's
(44.2 %).

The same settings read as on the cable (export limit 6020 W on, 31211 0x55, rated 5000 W);
the energy history is the part a dongle took away. The export-scale probe was not run through
the dongle.
