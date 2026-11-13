---
type: source
title: sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan.json
ingested: '2026-11-13'
created: '2026-11-13'
tags:
  - diagnosis
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - anonymous
  - direct_lan
  - modbus-proxy
---

# SH10RT-V112, B001.V000.P023, anonymous, through a Modbus proxy under load, SBR128

Read 2026-11-13 at 15:20 UTC with the terminal diagnosis (read only), posted to issue #786; the
reporter field is empty, so it stays anonymous. Committed unchanged. Source:
`device-diagnosis/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan.json`.

| | |
| --- | --- |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-33455145473` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| Communication module firmware | `WINET-SV200.001.00.P045`, fitted, not in the path |
| Transport (owner) | the Home Assistant add-on modbus-proxy 1.1.0, upstream the inverter's own LAN port; Home Assistant (the YAML package) and evcc **kept polling through the same proxy** during the reading |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered; 0 link drops |
| Battery | [SBR128](../entities/device-sbr-battery.md), four modules, firmware `SBRBCU-S_22011.01.30` |
| At the time | PV 0 W, SoC 88.6 %, load 2272 W, the battery discharging 2174 W |
| Same site | an SG10RT on its own WiNet-S, [read minutes later](sg10rt-3p-anonymous-anon-05631532143-summary.md) |

Every component answered, and the block read test answered **all 37 blocks in both rounds with no
reconnect**, with two other clients polling through the proxy. See
[contention](../concepts/contention.md).
