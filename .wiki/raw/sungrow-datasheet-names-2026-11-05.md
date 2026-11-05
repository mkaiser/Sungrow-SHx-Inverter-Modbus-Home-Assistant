# Sungrow's register names, read from five protocol documents

Notes taken on 2026-11-05 from Sungrow's protocol documents. **The documents
themselves are not in this repository and are not to be distributed**: what
is recorded here is the register names and the short statements the
integration's naming depends on. The names, by register, are in
`scripts/generate/tables/datasheet_names.json`.

## The documents

| Document | Version | Date in the document |
| --- | --- | --- |
| Communication Protocol of Residential Hybrid Inverter | V1.1.2 | 2023-10-18 |
| Communication Protocol of Residential Hybrid Inverter | V1.1.5 | 2024-09-24 (file date) |
| Communication Protocol of Residential Hybrid Inverter | V1.1.9 | 2025-06-20 |
| Communication Protocol of Residential Hybrid Inverter | V1.1.11 | 2025-11-19 (file date) |
| Modbus Register Protokoll SG 5.0 - 110 (string inverters) | V1.1.58 | — |

Register tables were extracted as text and matched to the integration's map
by register space and Sungrow's register number.

## How many of the integration's registers each names

- Hybrid: the integration's entities read 138 registers. V1.1.11 names 123.
  15 are in neither V1.1.2 nor V1.1.11: the four firmware parts 2582, 2597,
  2613 and 2629; the serial at 4990; the meter's phase voltages and currents
  5741-5746; holding 31211, 31213, 33149 and 33150.
- Of those V1.1.2 does not list, V1.1.11 names 35, and each matches the
  integration's name for it.
- SG: the integration's entities read 57 registers, and V1.1.58 names all 57.

## Names that changed between versions

| Register | V1.1.2 | V1.1.5 | V1.1.9 and V1.1.11 |
| --- | --- | --- | --- |
| input 5622 / 5623 | Export limit min / max | Export limit min / max | Min. / Max. Feed-in Power Limitation Value |
| holding 13074 | Export power limitation (change log) | the same | Feed-in Limitation Value |
| holding 13087 | Export Power Limitation | Export Power Limitation | Feed-in Limitation |
| holding 31222 | Feed-in Limitation – Wide range | the same | Feed-in Limitation value– Wide range |
| input 13023 / 13024 | Battery level / Battery state of healthy | the same | Battery SOC / Battery SOH |
| holding 13003-13016 | Load 1 ... | Load 1 ... | Load ... (the "1" dropped) |
| input 5214 | Battery power - Wide range | the same | Battery power |
| input 5242 | Grid Frequency - High precision | the same | Grid Frequency |

So the limit family turned from *Export* to *Feed-in* between V1.1.5 and
V1.1.9; V1.1.6 to V1.1.8 were not read. 13088 *Feed-in Limitation Ratio* was
added in V1.1.7.

The measured flows say **export** in every version: input 13010 *Export
power*, 13045/13046 *Daily/Total export energy*, 13006 *Total export energy
from PV*; on the SG, 5093/5095 *Daily/Total export energy*.

## Statements the naming relies on (V1.1.11)

- **Holding 13075 is *Off-grid option*.** The off-grid parameters' text says
  that with it disabled "the BACKUP port has no power output". Every other
  backup register says *Backup*: 5720-5733 *Phase A/B/C Backup Current, Power,
  Voltage*, 5726 *Total Backup Power*, 5734 *Backup Frequency*, holding 13100
  *Reserved SOC for backup*.
- **Holding 13017 is *Forced Startup Under Low SOC Standby*,** range "0xAA:
  Forced Startup", added in V1.1.7. Its note: with no PV input, "when the
  battery SOC falls below the lower SOC limit and the inverter is in standby
  mode, it will only automatically start up once sufficient PV energy becomes
  available. By setting the 'Forced Startup Under Low SOC Standby'
  configuration point to '0xAA', the inverter can be manually initiated
  without waiting for adequate PV energy. This function is only active when
  the inverter is in grid-connected mode".
- **Input 13001 is *Power Flow Status*,** its bits defined in Appendix 3
  *Power Flow State*: bit 0 PV power, 1 battery charging, 2 battery
  discharging, 3 positive load power, 4 feed-in power, 5 import power from
  grid, 7 (retrofitting system) negative load power.
- **Input 5017 is *Total DC power*,** remark "Total PV power". The SG's 5017
  is *Total DC power* too.
- **Input 13008 is *Load power*,** remark "Power consumed by loads"; **input
  13010 is *Export power*,** remark "Power delivered by the inverter to the
  grid".
- **Holding 13089/13090 are *Active Power Limitation* and *Active Power Limit
  Ratio*** (0-1000, 0.1 %). Note 1 under the power regulation parameters: the
  feed-in limitation acts at the grid connection point, the power limiting
  function at the inverter's AC output port. Nothing in the document says
  what a ratio of 0 % does to the inverter.
- **Input 5008 is *Inside Temperature*** on the hybrid; the SG's 5008 is
  *Internal temperature*.
- **Input 5019-5021** are *A-B line voltage/phase A voltage* and so on, which
  of the two depending on the output type at 5002. V1.1.11 prints 5021 as
  "C-A line voltage/phase voltage".
