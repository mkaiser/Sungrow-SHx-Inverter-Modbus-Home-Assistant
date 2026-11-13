---
type: source
title: sg10rt-3p-anonymous-anon-05631532143.json
source_path: ../device-diagnosis/results/string_inverter/sg10rt-3p-anonymous-anon-05631532143.json
ingested: '2026-11-13'
created: '2026-11-13'
tags: [diagnosis, string-inverter, sg10rt, beryl-s, anonymous, winet]
---

# SG10RT, anonymous, its own WiNet-S, at dusk

Read 2026-11-13 at 15:26 UTC with the terminal diagnosis (read only), posted to issue #786; the
reporter field is empty, so it stays anonymous. The first three-phase string inverter in the
corpus. Committed unchanged. Source:
`device-diagnosis/results/string_inverter/sg10rt-3p-anonymous-anon-05631532143.json`.

| | |
| --- | --- |
| Model | [SG10RT](../entities/device-sg-rt.md), type code `0x2433`, three phase 3P4L |
| Stand-in serial | `anon-05631532143` |
| ARM / DSP firmware | `LCD_BERYL-S_V11_V01_A` / `MDSP_BERYL-S_V11_V01_A`; no inverter firmware string read |
| Transport | its own [WiNet-S](../entities/device-winet-s.md), Modbus TCP, port 502, unit 1 |
| Other clients | the WiNet Extractor add-on polled the WiNet-S's websocket API every 10 s; evcc may have read it over Modbus (owner) |
| At the time | dusk: 102 W on DC, 54 W on AC, work state 33024 (`0x8100`) |
| Same site | an SH10RT-V112, [read through a Modbus proxy](sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan-summary.md) |

## What answered

- **The whole read block**: input 4950-5229 and 7013-7032 (300 words), holding 5000-5049. Only
  input 4990-4999, the serial, is blanked, and holding 5020 read nothing, as on the
  [SG5.0RS](../entities/device-sg-rs.md).
- **Two MPPTs** with voltage (460.2 V and 574.6 V, 0 A at dusk); MPPT3 to MPPT12 read 0. The
  integration's tracker table says 2 for the SG10RT (`MPPT_COUNTS`,
  `src/sungrow_modbus/string_inverter/registers.py`), consistent.
- **Three phase voltages** of 229.6, 229.6 and 231.4 V; currents 0 A.
- **The meter block (input 5083-5104) reads 0** throughout ([zero means absent](../concepts/zero-means-absent.md)).
- **Holding 5007 reads 170 (`0xAA`, power limitation on) and 5008 1000 (100.0 %)**, as on both SG5.0RS.
- Bus voltage 693.5 V, grid frequency 50.0 Hz, lifetime PV 38116.8 kWh, 14660 h running.

The owner reports one dropped connection during the reading, and offers a daylight reading.
