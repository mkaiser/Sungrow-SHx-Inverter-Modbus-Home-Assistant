---
type: source
title: sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan.json
ingested: '2026-11-02'
created: '2026-11-02'
tags:
  - diagnosis
  - sh10rt
  - sapphire-h-b001-v000-p020
  - robbensonmio
  - direct_lan
  - sbr256
---

# SH10RT, B001.V000.P020, robbensonmio, the inverter's own LAN port, SBR256

Capability diagnosis of one inverter, read 2026-11-02 from the terminal diagnosis, issue #786, reads
only. Home Assistant's Modbus hub was stopped for the run. The owner's direct BMS registers are
[issue #788](robbensonmio-sbr-cell-registers-788-summary.md). Source:
`device-diagnosis/results/inverter/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan.json`.

| | |
| --- | --- |
| Installation | [robbensonmio](../entities/installation-robbensonmio.md) |
| Model | [SH10RT](../entities/device-sh-rt.md), type code `0x0E03` |
| Stand-in serial | `anon-21004123443` |
| Inverter firmware | [`SAPPHIRE-H_B001.V000.P020`](../entities/firmware-sapphire-h-b001-v000-p020.md) |
| ARM firmware | `ARM_SAPPHIRE-H_V11_V01_B` |
| DSP firmware | `MDSP_SAPPHIRE-H_V11_V01_B` |
| Battery firmware | `SBRBCU-S_22011.01.27` |
| Communication module firmware | `WINET-SV200.001.00.P036` |
| Transport (owner) | the inverter's own LAN port |
| Transport (measured) | direct to the inverter's LAN port, with a communication module fitted as well but not in the path; register 6100 answered |
| Battery | [SBR256](../entities/device-sbr-battery.md) (unit 200, **eight modules**); register 5639 reads 2560 (25.6 kWh) |

## What did not answer

Nothing: 36 of 36 blocks in all three rounds, none intermittent, no reconnects in the block read
test. MPPT3, MPPT4 and 13018 read the specification's unavailable value, and so do the meter's
phase registers 5741 and 5744 (0xFFFF, 0x7FFF): no meter phase measurements here. No wallbox at
unit 3 or 248, nothing at unit 2. The owner reports twelve dropped connections in the diagnosis's
terminal log with nothing else polling; the document does not carry them, and the block read test
it does carry saw none.

## The battery

The largest SBR in the corpus, and the first with all eight module slots filled:

- `cell_type_module_1` to `_8` all read **1**. Every other cable SBR reading has 66, 68, 75 or 76
  in its fitted slots and 0 in the empty ones, so the value is not a module count or a flag that
  means the same everywhere; this pack is also on the oldest BCU firmware in the corpus.
- Pack extremes and their locations agree with the per-module words, as #788 describes:
  `max_cell_voltage` 3.3082 V at `max_cell_position` 769 (`0x301`, module 3, cell 1) equals
  `max_cell_voltage_module_3`; `min_cell_voltage` 3.3064 V at 259 (`0x103`, module 1, cell 3)
  equals `min_cell_voltage_module_1`. Spread 1.8 mV at 77.7 % SoC, current 4.2 A.
- Temperatures 18.8-20.6 °C, positions `0x101` and `0x302`; state of health 93 %.

## What the dump adds

- [31211](../entities/register-31211.md) reads 0xFFFF, as on every P020.
- [13074](../entities/register-13074.md) holds 10000 W with feed-in limitation (13087) on (0xAA).
- The discharge schedules: weekday window 1 00:00-24:00, window 2 00:00-00:00; weekend discharge
  0xAA (on), window 1 00:00-24:00, window 2 00:00-00:00. The forced-charging schedule is off
  (0x55, days 1), with window 1 set to 13:00-16:59 at 98 % and window 2 00:00-00:01 at 10 %.
- The history block, inputs 6101-6826, answers whole; monthly PV generation runs from 18162 in
  January down to 7240 in June and back up, a southern-hemisphere year. See
  [energy history](../concepts/energy-history.md).

## Contention

No other poller. See [contention](../concepts/contention.md).
