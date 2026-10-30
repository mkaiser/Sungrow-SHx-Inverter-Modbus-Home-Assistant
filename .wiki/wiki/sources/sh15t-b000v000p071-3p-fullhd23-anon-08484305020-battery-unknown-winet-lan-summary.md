---
type: source
title: sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan.json
source_path: ../device-survey/results/inverter/sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh15t
  - pearl-h-b000-v000-p071
  - fullhd23
  - winet_lan
---

# SH15T, B000.V000.P071, FullHD23, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-10-27. Source: `device-survey/results/inverter/sh15t-b000v000p071-3p-fullhd23-anon-08484305020-battery-unknown-winet-lan.json`.

| | |
| --- | --- |
| Installation | [FullHD23](../entities/installation-fullhd23.md) |
| Model | [SH15T](../entities/device-sh-t.md), type code `0x0E25` |
| Stand-in serial | `anon-08484305020` |
| Inverter firmware | [`PEARL-H_B000.V000.P071`](../entities/firmware-pearl-h-b000-v000-p071.md) |
| ARM firmware | `ARM_PEARL-H_V11_V01_A` |
| DSP firmware | `MDSP_PEARL-H_V11_V01_A` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV300.001.03.P033` |
| Version strings | `PEARL-H_01011.01.45`, `PEARL-H_03011.01.45` |
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | unknown |

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

## Contention

Polled by this Home Assistant, held off for the run (14 components); block read test: run, before the probes, with this entry's polling held off; see block_read_test. See [contention](../concepts/contention.md).
