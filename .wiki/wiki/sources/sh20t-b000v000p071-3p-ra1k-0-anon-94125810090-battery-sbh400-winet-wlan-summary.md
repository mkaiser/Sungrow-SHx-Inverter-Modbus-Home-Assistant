---
type: source
title: sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan.json
source_path: ../device-survey/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh20t
  - pearl-h-b000-v000-p071
  - ra1k-0
  - winet_wlan
---

# SH20T, B000.V000.P071, ra1k_0, a WiNet-S on WiFi

Capability survey of one inverter, read 2026-09-16. Source: `device-survey/results/inverter/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [ra1k_0](../entities/installation-ra1k-0.md) |
| Model | [SH20T](../entities/device-sh-t.md), type code `0x0E26` |
| Stand-in serial | `anon-94125810090` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM firmware | `ARM_PEARL-H_V11_V01_A` |
| DSP firmware | `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBHBCU-S_22011.04.11` |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Version strings | `PEARL-H_01011.01.45`, `PEARL-H_03011.01.45` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBH400](../entities/device-sbh-battery.md) |

> iHomeManager and AC22E-01 is installed too

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

## Contention

Polled by this Home Assistant, throughout (13 components); block read test: not run: it costs 26 block reads times three rounds plus narrowing, which belongs in a background task rather than a diagnostics download. See [contention](../concepts/contention.md).
