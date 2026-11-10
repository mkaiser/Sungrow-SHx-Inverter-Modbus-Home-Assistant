---
type: source
title: ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503.json
source_path: ../device-diagnosis/results/ihomemanager/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503.json
ingested: '2026-11-10'
created: '2026-11-10'
tags:
  - diagnosis
  - ihomemanager
  - anonymous
---

# iHomeManager, SV930.001.00.P020, anonymous, port 503

iHomeManager document, read 2026-11-10 at 11:52 UTC by *Diagnosis: start* on a diagnosis-only
entry in Home Assistant, integration 0.1.0a35, posted to issue #786 and signed `anonymous`.
**The first iHomeManager measured here.** Source:
`device-diagnosis/results/ihomemanager/ihomemanager-ihomemanager-sv930-001-00-p020-anonymous-port503.json`.

| | |
| --- | --- |
| Device | [iHomeManager](../entities/device-ihomemanager.md), type code `0x072A` |
| Application software | `iHomeManager-SV930.001.00.P020` |
| Path | Modbus TCP, port **503**, unit 247 |
| Protocol version | V1.0.1 (8003, raw `0x01000100`) |

## What answered

All 56 fields of the map answered (`src/sungrow_modbus/ihomemanager/registers.py`). In the dump,
inputs 4357-4362, 8000-8006, 8145-8163, 8176-8179, 8318-8332, 8552-8574 and 8594-8774 answered,
249 in all, and holding 8024-8053, 30 in all. Inputs 8007-8144, 8164-8175, 8180-8317 and
8333-8551, and holding 8000-8023 and 8054-8128, did not.

| Reading | Register | Value |
| --- | --- | --- |
| connected devices / in fault | 8005 / 8006 | 3 / 0 |
| total rated active power | 8145 | 20.0 kW |
| total rated battery capacity | 8147 | 40.5 kWh |
| max battery charge / discharge power | 8151 / 8153 | 26.6 / 20.0 kW |
| inverter / grid / load active power | 8155 / 8157 / 8159 | 0.71 / 0.0 / 0.71 kW |
| battery power, battery level | 8161, 8163 | 0.81 kW, 85 % |
| grid import / export energy | 8176 / 8178 | 184.5 / 3453.6 kWh |
| voltages A, B, C | 8555-8557 | 416.1, 417.8, 418.7 V |
| phase-to-neutral voltages | 4358, 4360, 4362 | 240.3, 241.0, 241.4 V |
| phase powers A, B, C | 8559, 8561, 8563 | 311, -159, -162 W |
| channel 2 phase powers | 8569-8574 | 0 |
| charger status | 8552 | 6, charging completed |
| charger power | 8594 | 0 W |
| EMS mode | holding 8024 | 1, self-consumption |
| charge command / power | holding 8025 / 8026 | 0xBB (discharge) / 6.8 kW |
| feed-in limitation | holding 8028 | **0x55**, off |
| feed-in limit / ratio | holding 8029 / 8031 | 0.0 kW / 0.0 % |
| VPP heartbeat | holding 8033 | 300 s |
| charger enabled / grid draw permitted | holding 8049 / 8050 | 0xAA on / 0x55 off |

## What it settles, and what it raises

- **8028 reads 0x55 for off**, as evcc's users found on P015, not V1.0.2's 0
  ([evcc cross-reference](cross-reference-evcc-summary.md)).
- **8555-8557 are line to line here, 4358-4362 phase to neutral**, as on evcc's three-phase
  units: 416-419 V against 240-241 V. Between them 4359 and 4361 read 0, so they are U16 with a
  gap or U32 low word first; at these values the two cannot be told apart.
- **The protocol number (8001-8002) is `0x3000 0x4157`**: "AW0" read low word first, the text
  V1.0.2 gives. This document was written by a map that read it high word first, so it publishes
  "0"; the map now reads it low word first (`src/sungrow_modbus/ihomemanager/registers.py`).
- **8554 reads 0**, which the map decodes as single phase, beside three-phase voltages and
  phase powers. Either 8554 describes something else here, or 0 is not single phase.
- Codes the map does not know: 8047 (start/stop) reads 0, 8048 (charger mode) 0xA7, 8051
  (active power limitation) 0; 8052 reads 0x7FFF (3276.7 %), an unset value.
- **Inputs 8645-8650 hold text**, which the reader masked: a serial sits in the undocumented
  range 8594-8774, as the device page warned. Its stand-in matches an inverter diagnosed here,
  so the block names a device the iHomeManager manages, not the iHomeManager itself.
