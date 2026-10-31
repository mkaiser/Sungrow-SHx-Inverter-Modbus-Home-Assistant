---
type: source
title: sh10rt-v112-b001v000p023-3p-anonymous-anon-40315531061-battery-sbr224-meter-direct-lan.json
source_path: ../device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-40315531061-battery-sbr224-meter-direct-lan.json
ingested: '2026-10-31'
created: '2026-10-31'
tags:
  - survey
  - sh10rt-v112
  - sapphire-h-b001-v000-p023
  - anonymous
  - direct_lan
---

# SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port, SBR224

Capability survey of one inverter, read 2026-10-31 at night from the terminal survey, issue #786,
reads only (`--control-test no`). Published as `anonymous`. Source:
`device-survey/results/inverter/sh10rt-v112-b001v000p023-3p-anonymous-anon-40315531061-battery-sbr224-meter-direct-lan.json`.

| | |
| --- | --- |
| Model | [SH10RT-V112](../entities/device-sh-rt.md), type code `0x0E0F` |
| Stand-in serial | `anon-40315531061` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P023`](../entities/firmware-sapphire-h-b001-v000-p023.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.30` |
| Communication module firmware | `WINET-SV200.001.00.P044` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR224](../entities/device-sbr-battery.md) (unit 200, **seven modules**) |

## What did not answer

Nothing: every component and every block answered in all three rounds, none intermittent, no
reconnects. MPPT3, MPPT4 and 13018 read the specification's unavailable value. No wallbox
answered at unit 3 or 248, and nothing at unit 2.

## The battery

The most SBR modules in the corpus: `cell_type_module_1` to `_7` are non-zero (68) and `_8` is 0, so
seven modules. The [position words](../entities/device-sbr-battery.md) decode consistently up to
module 7: `max_cell_position` 1795 = `0x703` with `max_cell_module` 7, `min_cell_position` 769 =
`0x301` with `min_cell_module` 3, and the temperature positions `0x601` and `0x102` with modules
6 and 1. Capacity 22.4 kWh.

## What the dump adds

- The discharge schedules, registers 33151-33158 and 33179-33187: weekday windows 1 and 2 both
  00:00-24:00; weekend discharge 0xAA (on), windows 1 and 2 both 00:00-24:00. The same layout as
  at [peter-sm](../entities/installation-peter-sm.md), a second house.
- The dump predates 0.1.0a22: register 32998, the forced-charging schedule and the history block
  past 6198 are not in it.

## Contention

No other poller reported; the block read test saw no reconnects. See
[contention](../concepts/contention.md).
