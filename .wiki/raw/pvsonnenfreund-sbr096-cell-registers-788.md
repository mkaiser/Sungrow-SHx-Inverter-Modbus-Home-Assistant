# SBR096 cell registers confirmed, and two odd frames (issue #788, PVSonnenfreund, 2026-11-21)

A copy of the comment on issue #788 (comment 7060699280), converted from its HTML to Markdown, wording unchanged. Addresses are 0-based protocol addresses, as the comment says.

## Confirmation on SBR096 (3 modules × 20 cells) – FC04 register scans
Thanks for sharing this register mapping! I independently verified the results on my smaller SBR096 battery.

## Setup

- **Inverter:** SH10RT-V112, firmware `SAPPHIRE-H_B001.V000.P023`

- **Connection:** Inverter LAN port (not WiNet-S), Modbus TCP port 502

- **Battery:** SBR096, 3 modules × 20 cells

- **BCU firmware:** `SBRBCU-S_22011.01.30`

- **Modbus:** Unit ID 200, FC04, 0-based addresses

## Register mapping confirmed
Across 12 snapshots, each collected within a single Modbus block response:

- Pack maximum (10756) exactly matched the maximum cell voltage of the module identified by position register 10757.

- Pack minimum (10758) exactly matched the minimum cell voltage of the module identified by position register 10759.

- Per-module maximum registers: `10764–10766`.

- Per-module minimum registers: `10772–10774`.

- All comparisons matched exactly at the 0.1 mV register resolution.
Position encoding is confirmed: high byte = module, low byte = cell.
Examples:

- `0x010B` = module 1, cell 11

- `0x0302` = module 3, cell 2

- `0x030F` = module 3, cell 15
Unused module slots 4–8 return zero. Spread calculations must therefore exclude unused modules.

## Differences compared with the SBR256
**Registers 10780–10782 return 76 (**`0x004C`**)** for each present module, instead of 1. Unused slots return zero.
The exact meaning remains unknown. This may represent a module/cell type identifier rather than a simple Boolean presence flag.
Module serial-number registers `10821`, `10830` and `10839` return valid data on my BCU firmware `.01.30`, unlike the null bytes reported with firmware `.01.27`.
Additional observed register values:

Address | Value
-- | --
10750 | 4
10751–10755 | 65535 (0xFFFF)
10788 | 2
10789 | 0
10790 | 48165 (0xBC25)

The meanings of these values have not been established.

## Modbus-TCP response length anomaly
I also found a reproducible response-length inconsistency near the upper boundary of this register range.
**FC04, address 10750, count 41:**
The MBAP Length field indicates 84 data bytes, while the FC04 byte count correctly indicates 82 bytes. An additional word `01 5F` (351) appears after the expected data.

```
Request:
00 01 00 00 00 06 c8 04 29 fe 00 29

Response:
00 01 00 00 00 57 c8 04 52 00 04 ff ff ff ff ff ff ff ff ff ff 84 bf 01 0b 84 6d 03 02 00 ea 02 01 00 e7 01 01 84 bf 84 9d 84 aa 00 00 00 00 00 00 00 00 00 00 84 77 84 75 84 6d 00 00 00 00 00 00 00 00 00 00 00 4c 00 4c 00 4c 00 00 00 00 00 00 00 00 00 00 00 02 00 00 bc 25 01 5f
```
**FC04, address 10791, count 1:**
The reverse anomaly occurs: the byte count announces two data bytes, but no register data is returned.

```
Request:
00 02 00 00 00 06 c8 04 2a 27 00 01

Response:
00 02 00 00 00 03 c8 04 02
```
Both responses were captured directly from the inverter's LAN Modbus endpoint. No additional bytes arrived afterward.
The extra word `0x015F` cannot be confirmed as the actual value of register 10791.
Repeated block reads limited to **10756–10782** were successful (10/10), without any protocol-length inconsistencies.
As a precaution, I recommend limiting future block reads to this verified range and reading other registers individually where needed.

## Conclusion
The register mapping is confirmed for the SBR096 with three modules. No changes to my existing Home Assistant YAML are necessary.
The different value of 76 in registers 10780–10782 and the Modbus-TCP length anomaly may be useful for future investigations.
Thanks again for documenting these registers!
