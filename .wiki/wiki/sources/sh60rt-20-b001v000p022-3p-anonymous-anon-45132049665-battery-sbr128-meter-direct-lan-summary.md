---
type: source
title: sh60rt-20-b001v000p022-3p-anonymous-anon-45132049665-battery-sbr128-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh60rt-20-b001v000p022-3p-anonymous-anon-45132049665-battery-sbr128-meter-direct-lan.json
ingested: '2026-11-05'
created: '2026-11-05'
tags:
  - survey
  - sh60rt-20
  - sapphire-h-b001-v000-p022
  - anonymous
  - direct_lan
  - modbus-proxy
---

# SH6.0RT-20, B001.V000.P022, anonymous, through a Modbus proxy, SBR128

Capability survey of one inverter, read 2026-11-05 at 11:16 UTC from Home Assistant's survey (the
preview integration's diagnostics, `command_line` "home assistant diagnostics"), issue #786, reads
only. Published as `anonymous`. The second SH6.0RT-20 in the corpus, and the first on P022. Source:
`device-survey/results/inverter/sh60rt-20-b001v000p022-3p-anonymous-anon-45132049665-battery-sbr128-meter-direct-lan.json`.

| | |
| --- | --- |
| Model | [SH6.0RT-20](../entities/device-sh-rt.md), type code `0x0E11`, three phase 3P4L |
| Stand-in serial | `anon-45132049665` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P022`](../entities/firmware-sapphire-h-b001-v000-p022.md) |
| Version 1 / 2 / 3 | `SAPPHIRE-H_01011.95.13` / `SAPPHIRE-H_03011.95.13` / `SUBCTL-S_04011.01.01` |
| ARM / DSP firmware | `ARM_SAPPHIRE-H_V11_V01_B` / `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.27` |
| Communication module firmware | `WINET-SV200.001.00.P040` |
| Transport (owner) | the inverter's own LAN port, **through a Modbus proxy**; a WiNet-S is fitted but not in the path; the YAML package was stopped for the run |
| Transport (measured) | direct to the inverter's LAN port; register 6100 answered |
| Battery | [SBR](../entities/device-sbr-battery.md) at unit 200, four modules (`cell_type_module_1` to `_4` read 1), 12.8 kWh |

## What did not answer

Nothing: every block of the block read test answered in all three rounds, none intermittent, no
reconnects, with this entry's polling held off. MPPT3, MPPT4 and 13018 read the unavailable value
(0xFFFF), as on every SH-RT.

## What the dump adds

- [Register 31211](../entities/register-31211.md) answers **0x55**, as on the other P022 surveys.
- Export limit is **off** (13087 = 0x55), with the limit word 13074 at raw 7600 and maximum 7600 W;
  no write was made, so its [write scale](../entities/register-13074.md) is unmeasured here.
- Forced-charging schedule (33208) off; weekend discharge (33179) reads 0xAA (on).
- Register 32998 reads 2000.
- Max SoC 100 %, min SoC 5 %, backup reserve 0 %. Active power limitation on at 100 %.

## The battery

Pack state of charge 51.8 % against the inverter's battery level 49.0 %, health 96 %, 267.3 V,
18.2 °C, charging at 975 W. Cell spread 6.8 mV; the position words decode consistently
(`max_cell_position` 261 = `0x105`, module 1 cell 5; `min_cell_position` 513 = `0x201`, module 2
cell 1). Register 5639 reads 12.8 kWh for four modules.

No control test, so the PV cut and the 13074 scale stay as measured on P022 at [gerd](../entities/installation-gerd.md).
