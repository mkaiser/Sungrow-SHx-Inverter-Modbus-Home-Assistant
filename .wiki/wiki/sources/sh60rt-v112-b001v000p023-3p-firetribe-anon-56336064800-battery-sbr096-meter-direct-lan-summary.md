---
type: source
title: sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan.json
source_path: ../device-survey/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan.json
ingested: '2026-10-29'
created: '2026-10-29'
tags:
  - survey
  - sh6.0rt-v112
  - sapphire-h-b001-v000-p023
  - firetribe
  - direct_lan
  - control-test
---

# SH6.0RT-V112, B001.V000.P023, firetribe, the inverter's own LAN port

Capability survey of one inverter, read 2026-10-29 from Home Assistant, issue #784. Source: `device-survey/inverter/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan.json`.

| | |
| --- | --- |
| Installation | [firetribe](../entities/installation-firetribe.md) |
| Model | [SH6.0RT-V112](../entities/device-sh-rt.md), type code `0x0E0D` |
| Stand-in serial | `anon-56336064800` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P044` |
| Version strings | `SAPPHIRE-H_01011.95.14`, `SAPPHIRE-H_03011.95.14`, `SUBCTL-S_04011.01.01` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 present |
| Battery | [SBR096](../entities/device-sbr-battery.md) (typed `SB096`; the pack answered at unit 200) |

## What did not answer

Every component and all 28 blocks answered. MPPT3 and MPPT4 are unavailable,
as on every SH-RT read by cable, and so are meter channel 2 and PV power
limitation (13018).

## Contention

Polled by this Home Assistant, held off for the run (14 components). The owner
reports two other clients on the **WiNet-S**, not on this port: a WARP3
wallbox and a second Home Assistant. See [contention](../concepts/contention.md).

## Control test

Outcome **2**: refused before any write, because register 13000 reported
`Starting` rather than running. Nothing was written. See
[the control test](../concepts/control-test.md).
