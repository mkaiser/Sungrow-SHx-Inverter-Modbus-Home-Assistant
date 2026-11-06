# Sungrow's hybrid protocol V1.1.17

What *Communication Protocol of Residential and Small Industrial Hybrid
Inverter* **V1.1.17** (released 2026-09-30, classification "Open") says,
read on 2026-11-06. It is the newest version found; V1.1.16 (2026-07-03) is
the one before it and differs from it in device types only. Every number is
a **register number**, as the document prints them (its worked example reads
SN from address 4990 as `13 7D`, 0x137D = 4989 on the wire).

Where it was found: the PDF is linked from a third party's SH10RT guide
(episensor.com/devices/sungrow-sh10rt) and served by Sungrow at
`info-support.sungrowpower.com/general-material/2d6b9595-3579-4124-a82c-68482d545d8c.pdf`.
The cover forbids distributing it ("shall not be uploaded to third-party
platforms such as public networks"), so it stays in the maintainer's
gitignored `tmp/`, never in this repository; this is the record of what it
says.

## What changed since V1.1.11

| Version | Date | Change |
| --- | --- | --- |
| V1.1.12 | 2025-12-10 | device types MG7.5RL, SH5RL, SH6RL, SH8RL, SH10RL |
| V1.1.13 | 2026-04-30 | MG12RL |
| V1.1.14 | 2026-05-10 | SH110/125CX |
| V1.1.15 | 2026-05-28 | SH50/80/100CX; **33274's range corrected** to 0-600.00 (0.01 kW) |
| V1.1.16 | 2026-07-03 | SH3/3.6/4RL |
| V1.1.17 | 2026-09-30 | **MG10, MG12, MG15, MG20, MG25TL: 0xE53-0xE57** |

No register was added or removed since V1.1.11. `DEVICE_TYPES` in
`src/sungrow_modbus/const.py` held every type but the five MG..TL codes,
which it now holds as `Family.TL` (`src/sungrow_modbus/hybrid_inverter/capabilities.py`).

## What it says of MG10-25TL

Appendix 1 gives each of MG10TL to MG25TL three trackers (strings 1;1;1,
MG20TL 2;2;1). Four remarks name the group, apart from "MG5-12RL and
SH3-10RL": 13250-13294 firmware, 13200-13207 meter channel 2 and 33208
forced charging add "and MG10-25TL" to the unsupported list; 13089/13090,
13088 and 13043 exclude only "MG5-12RL and SH3-10RL", not the TL; 13018
supports "SHT" only.

Appendix 4 (the fault codes) is word for word V1.1.11's, and Appendices 2
and 3 differ from it in page layout only (compared as text, 2026-11-06).

## What it does not list

The integration reads these, and this document does not name them:

| Registers | Here |
| --- | --- |
| input 2582, 2597, 2613, 2629 | not listed; the firmware strings are 13250-13294 |
| input 5741-5746 | not listed; the meter's phase *active power* is 5603/5605/5607 |
| holding 31211, 31213 | not listed |
| holding 33149, 33150 | not listed; 33148 is "Charging/Discharging Power - Wide range" |

**Input 4990-4999 is listed**: `SN`, UTF-8, ten registers.

## Registers it lists that the hybrid map does not read

| Register | Name | Type, unit | Remarks |
| --- | --- | --- | --- |
| 31222 | Feed-in Limitation value - Wide range | U16, 0.01 kW, read-write | beside 13074 (1 W) |
| 13080 | External EMS heartbeat | U16, 1 s, 0-1000, default 20 s | |
| 13043 | DRM state | U16, 1-9 is DRM0-DRM8 | not on MG5-12RL, SH3-10RL |
| 13015, 13016 | Load power optimized mode: end minute; optimized power of load | U16 | the load control block |
| 13086 | Meter Comm. Detection | U16, 0xAA enable, 0x55 disable | |
| 33042 | Charge Cutoff Voltage - Wide range | U16, 0.1 V | |
| 33148 | Charging/Discharging Power - Wide range | U16, 0.01 kW | |
| 33274 | Load Rated Power | U16, 0-600.00, 0.01 kW | |
| 6100-6826 | the history blocks (daily, monthly, annual yields) | | WiNet-S/S2 and Logger not supported |

## Notes the document makes

- **13017 Forced Startup Under Low SOC Standby**: only `0xAA`. "Only active
  when the inverter is in grid-connected mode ... does not work in off-grid
  scenarios." SH50~125CX are not supported.
- **13018 PV power limitation**: 0xAA limit PV, 0x55 allow PV; "SHT are
  supported" only.
- **13021 Battery current**: S16 on SH3.0-6.0RS and SH8.0-10RS; the document
  recommends 5631 and 5214-5215 instead. **13022 Battery power** is U16.
- **13088 Feed-in Limitation Ratio** (0.1 %) and **13074** are the same limit
  in two units; "when both are configured, the value of this tag takes
  precedence" (the ratio).
- The document names the holding registers as read/write by function code
  3, 6 and 16, input registers by 4.
