---
type: source
title: sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan.json
source_path: ../device-survey/inverter/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh10rt-20
  - sapphire-h-b001-v000-p020
  - bar12
  - winet_lan
---

# SH10RT-20, B001.V000.P020, bar12, a WiNet-S on Ethernet

Capability survey of one inverter, read 2026-09-08. Source: `device-survey/inverter/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan.json`.

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
| Transport (owner) | a WiNet-S on Ethernet |
| Transport (measured) | through a communication module (WiNet-S, WiNet-S2 or Logger); register 6100 refused |
| Battery | [SBR096](../entities/device-sbr-battery.md) |

> Read by the maintainer over a VPN; the site's owner reports nothing else was polling the inverter. Both of this house's addresses answer with the same serial, so it is one inverter reached two ways. Measured on both: register 6100 refuses and port 443 answers, so both paths go through a communication module, and register 13265 names the same WiNet-S firmware on each. Which medium each path uses -- the dongle has an Ethernet port and WiFi -- is not established, which is why the transport is recorded as not sure. Corrected 2026-10-09: this address was the WiNet-S's own Ethernet port. The owner's LAN cable went into the dongle, not the inverter; on 2026-10-08 it was moved into the inverter, the dongle's address disappeared and the inverter's LAN port answered at a new one (published as its own reading). So this is the wired half of the pair.

## What did not answer

- `battery_firmware`
- `sub_controller_firmware`
