---
type: source
title: sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json
source_path: ../device-survey/inverter/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-20
  - sapphire-h-b001-v000-p020
  - bar12
  - winet_wlan
  - control-test
---

# SH10RT-20, B001.V000.P020, bar12, a WiNet-S on WiFi

Capability survey of one inverter, read 2026-09-08. Source: `device-survey/inverter/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan.json`.

| | |
| --- | --- |
| Installation | [bar12](../entities/installation-bar12.md) |
| Model | [SH10RT-20](../entities/device-sh-rt.md), type code `0x0E13` |
| Stand-in serial | `anon-81257679535` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.27` |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Version strings | `SAPPHIRE-H_01011.95.12`, `SAPPHIRE-H_03011.95.12` |
| Transport (owner) | a WiNet-S on WiFi |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN; the site's owner reports nothing else was polling the inverter. Both of this house's addresses answer with the same serial, so it is one inverter reached two ways. Measured on both: register 6100 refuses and port 443 answers, so both paths go through a communication module, and register 13265 names the same WiNet-S firmware on each. Which medium each path uses -- the dongle has an Ethernet port and WiFi -- is not established, which is why the transport is recorded as not sure. Corrected 2026-10-09: this address is the WiNet-S over WiFi. It still answered on 2026-10-08 after the dongle's Ethernet cable was moved into the inverter, while the wired address disappeared.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`

## Control test

Outcome **3**: ran, but checks were skipped or inconclusive. See [the control test](../concepts/control-test.md).

| Field | Register | Verdict |
| --- | --- | --- |
| `battery_min_soc` | 13059 | matched |
| `battery_max_soc` | 13058 | the device kept its old value |
| `battery_reserved_soc_for_backup` | 13100 | matched |
| `battery_max_charge_power` | 33047 | the device kept its old value |
| `battery_max_discharge_power` | 33048 | the device kept its old value |
| `export_power_limit` | 13074 | matched |
| `battery_forced_charge_discharge_power` | 13052 | matched |
| `battery_charging_start_power` | 33149 | matched |
| `battery_discharging_start_power` | 33150 | matched |

- Behaviour, forced charge: **the inverter did as it was told**.
- Behaviour, forced discharge: **the inverter did as it was told**.
- Behaviour, charge ceiling: **the inverter did as it was told**.
- Behaviour, export power limit: **the inverter did as it was told** -- export was made by discharging 3010 W.
- Restore: every register back and read back.
