---
type: source
title: pvsonnenfreund-sbr096-cell-registers-788.md
source_path: raw/pvsonnenfreund-sbr096-cell-registers-788.md
ingested: '2026-11-21'
created: '2026-11-21'
tags: [sbr, battery, padded-frames, pvsonnenfreund, sapphire-h-b001-v000-p023]
---

# SBR096 cell registers confirmed on BCU .01.30, and two odd frames (issue #788)

`.wiki/raw/pvsonnenfreund-sbr096-cell-registers-788.md`: an owner's raw-socket block reads of the SBR
cell block at [PVSonnenfreund](../entities/installation-pvsonnenfreund.md), an SBR096 of three modules
behind an SH10RT-V112 on P023, BCU `SBRBCU-S_22011.01.30`, unit 200 over the inverter's own LAN port.
The comment gives protocol addresses; the registers below are one higher.

| Claim | Evidence | In the library |
| --- | --- | --- |
| The pack's highest and lowest cell (10757, 10759) equal the per-module word of the module their position names | 12 of 12 block reads, exact at 0.1 mV | `max_cell_voltage_module_n`, `min_cell_voltage_module_n` |
| Positions are `(module << 8) \| cell` | `0x010B`, `0x0302`, `0x030F` | the position words |
| Empty module slots 4-8 read 0 | the owner's reads | `SbrBatteryModules.fitted_modules` |
| 10781-10783 read 76 for each fitted module | the owner's reads | `cell_type_module_n`; 76 already seen on other packs |
| **Module serials (10822, 10831, 10840) carry data on BCU `.01.30`**, where the SBR256 on `.01.27` read NUL bytes | the owner's reads | not read |
| **A read at protocol address 10750 for 41 words: the MBAP length says 84 data bytes, the byte count 82**, and a word 0x015F follows the data | the raw frame | the library reads only to protocol address 10787 (register 10788) |
| **A read at protocol address 10791 for 1 word: the byte count says 2 and no data follows** | the raw frame | not read |
| Block reads at protocol addresses 10756-10782 succeeded 10 of 10 with no mismatch | the owner's reads | inside the library's block |

The values seen at 10751 (4), 10752-10756 (0xFFFF), 10789 (2), 10790 (0) and 10791 (0xBC25) have no
known meaning. These are raw-socket reads, so the frame findings are a lead for `blocks.py`'s strict
measurement ([padded frames](../concepts/padded-frames.md)), not a layout change.
