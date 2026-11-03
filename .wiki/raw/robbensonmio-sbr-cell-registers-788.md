# SBR direct BMS registers 10756-10787 on an SBR256, issue #788, 2026-11-02

Copied from the body of issue #788 as posted by its author on 2026-11-02. The
author's survey of the same installation is
`device-survey/results/inverter/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan.json`.
Addresses in the table are protocol addresses, as the author states.

## Context

Sharing a set of direct battery (SBR) registers I've verified on my system, in case they're useful for v2 and the new HA integration. They continue on from the 10710-10750 block documented for SBH in #751.

- Inverter: SH10RT, firmware `SAPPHIRE-H_B001.V000.P020`
- Battery: SBR256 (8 modules x 20 LiFePO4 cells = 160 cells, ~532 V)
- BCU firmware: `SBRBCU-S_22011.01.27`
- Connection: inverter's own LAN port (not WiNet-S), Modbus TCP 502
- Unit ID / device address: `200` (the `sungrow_modbus_sbr_device_address` slot)
- Function code: `04` (Read Input Registers)

Addresses below are 0-based, matching the YAML (`address: 10756 # reg 10757`).

## Registers

| Address | Type | Scale | Meaning |
| ---: | --- | ---: | --- |
| `10756` | uint16 | 0.1 mV | Highest cell voltage in the whole pack |
| `10757` | uint16 | - | Location of highest cell: high byte = module (1-8), low byte = cell (1-20) |
| `10758` | uint16 | 0.1 mV | Lowest cell voltage in the whole pack |
| `10759` | uint16 | - | Location of lowest cell (same encoding) |
| `10760` | int16 | 0.1 C | Highest temperature in the pack |
| `10761` | uint16 | - | Location: high byte = module, low byte = temperature sensor number |
| `10762` | int16 | 0.1 C | Lowest temperature in the pack |
| `10763` | uint16 | - | Location (same encoding) |
| `10764`-`10771` | uint16 | 0.1 mV | Highest cell voltage in module 1..8 |
| `10772`-`10779` | uint16 | 0.1 mV | Lowest cell voltage in module 1..8 |
| `10780`-`10787` | uint16 | - | Module present flags, module 1..8 (all `1` on my 8-module pack) |

Location example: `1044` = `0x0414` = module 4, cell 20.

In YAML, `scale: 0.0001` gives the voltages in V, and `max(10764..10779) - min(10764..10779)` gives the true pack-wide cell spread across all 160 cells.

## Pitfall: 10764-10779 are not 16 individual cells

It's easy to read 10764-10779 as "cell 1..16 voltage" (I did at first). On this pack they're per-module max/min: the first 8 are each module's highest cell, the next 8 each module's lowest. That only shows up with more than one module installed, so it may look right on smaller packs.

## How I verified it

Raw read-only FC04 reads of 10756-10787 in a single transaction, compared against the pack-wide extremes and their locations:

- In 7 of 7 samples, `10764 + (m-1)` equalled the pack max (10756) whenever the max location (10757) was in module `m`.
- In the same samples, `10772 + (m-1)` equalled the pack min (10758) whenever the min location (10759) was in module `m`.
- Pairing the registers as cell 1/cell 2 instead never matched.

These have been polled in HA since 2026-07 (renamed correctly 2026-10-26). Typical values on this pack: about 1-10 mV spread at rest mid-SoC, 40-100 mV under heavy charge/discharge, and brief peaks up to ~270 mV near full while balancing.

## Not working on this firmware

Per-module serial numbers at `10821`-`10884` (8 x 9-register strings, a community-sourced address) only return null bytes here, so I've dropped them.
