---
type: source
title: robbensonmio-sbr-cell-registers-788.md
source_path: raw/robbensonmio-sbr-cell-registers-788.md
ingested: '2026-11-02'
created: '2026-11-02'
tags: [sbr, battery, robbensonmio, sapphire-h-b001-v000-p020]
---

# SBR direct BMS registers 10757-10788 on an SBR256 (issue #788)

`.wiki/raw/robbensonmio-sbr-cell-registers-788.md`: an owner's reading of the SBR cell and
module block at [robbensonmio](../entities/installation-robbensonmio.md), eight modules of 20
cells, BCU `SBRBCU-S_22011.01.27`, unit 200 over the inverter's own LAN port. The issue gives
protocol addresses; the registers below are one higher.

| Claim | Evidence | In the library |
| --- | --- | --- |
| 10757/10759 are the pack's highest and lowest cell, 0.1 mV | the owner's reads | `max_cell_voltage`, `min_cell_voltage` |
| 10758/10760 locate them, `(module << 8) \| cell` | `0x0414` = module 4, cell 20 | the [position words](../entities/device-sbr-battery.md) |
| 10761-10764: highest and lowest temperature and their locations, sensor in the low byte | the owner's reads | `max_module_temperature`, its position, and the minimum |
| **10765-10772 are each module's highest cell, 10773-10780 each module's lowest**, not 16 individual cells | 7 of 7 samples: the module the location names holds the pack extreme | `max_cell_voltage_module_n`, `min_cell_voltage_module_n` |
| 10781-10788 read 1 for every fitted module on this pack | the owner's reads | `cell_type_module_n` |
| Module serials at 10822-10885 read NUL bytes on this firmware | the owner's reads | not read |

**The corpus agrees with the per-module reading.** In every committed cable SBR reading that
carries the module words, 16 of them from three to eight modules, the pack's highest cell equals
`max_cell_voltage_module_n` of the module its position word names, and the lowest equals
`min_cell_voltage_module_n`, on every one. The same holds in this owner's
[diagnosis](sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan-summary.md).

**10781-10788 are not a presence flag everywhere.** On this pack they read 1; every other cable
SBR reading has 66, 68, 75 or 76 in its fitted slots and 0 in the empty ones. Zero for an empty
slot holds throughout; what the non-zero value means is not known.
