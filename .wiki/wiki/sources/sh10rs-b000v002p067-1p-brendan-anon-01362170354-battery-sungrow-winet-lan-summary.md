---
type: source
title: sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan.json
source_path: ../device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan.json
ingested: '2026-11-05'
created: '2026-11-05'
tags:
  - diagnosis
  - sh10rs
  - sunstone-h-b000-v002-p067
  - brendan
  - winet
  - capability-test
---

# SH10RS, B000.V002.P067, brendan, a WiNet-S on Ethernet, capability test refused

Capability diagnosis of one inverter, read 2026-11-05 at 05:24 UTC from the terminal diagnosis, issue
#786, with the capability test requested (`--capability-test yes`) and the owner's other pollers running
(`--pollers yes`). The owner says two SBR224 packs. Source:
`device-diagnosis/results/inverter/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan.json`.

| | |
| --- | --- |
| Installation | [brendan](../entities/installation-brendan.md) |
| Model | [SH10RS](../entities/device-sh-rs.md), type code `0x0D1B`, single phase |
| Stand-in serial | `anon-01362170354` |
| Inverter firmware | [`SUNSTONE-H_B000.V002.P067`](../entities/firmware-sunstone-h-b000-v002-p067.md), the first diagnose on it |
| ARM / DSP firmware | `ARM_SUNSTONE-H_V11_V01_A` / `MDSP_SUNSTONE-H_V11_V01_A` |
| Version 1 / 2 | `SUNSTONE-H_01011.02.67` / `SUNSTONE-H_03021.01.15` |
| Battery firmware | `SBRBCU-S_22011.01.30`, with bytes after its NUL |
| Communication module firmware | `WINET-SV300.001.03.P032` |
| Transport (owner) | a [WiNet-S](../entities/device-winet-s.md) on Ethernet |
| Transport (measured) | through a communication module; register 6100 refused |
| Battery | [SBR](../entities/device-sbr-battery.md) at unit 2 (cell and module blocks refused with 0x02) |
| PV | four MPPTs answer |

## What did not answer

The sub-controller (2613) and battery (2629) firmware blocks, the meter phase registers 5741 and
5744 (refused), and the PV and export history blocks, as through every WiNet-S. 13018 reads the
unavailable value. Link drops: 0.

## What the dump adds

- [Register 31211](../entities/register-31211.md) answers **0x55**.
- The forced-charging schedule (33208) and weekend discharge (33179) read 0x55 (off).
- Feed-in limitation is on (13087 = 0xAA) and 13074 holds a raw 50, with maximum 10000 W; no write
  was made, so its [write scale](../entities/register-13074.md) is unmeasured here.
- Register 32998 reads 1300, as on the other SH10RS.
- Max SoC 100 %, min SoC 0 %, backup reserve 10 %.

## The pack's capacity is two packs', its voltage one stack's

5639 reads **44.8 kWh** (4480), twice an SBR224's 22.4 kWh, and the pack reports 488.8 V, 100 %
SoC, health 99 (97 in the readings block). The owner has two SBR224. So the capacity register
sums the packs while the voltage is one stack's, which is the reading the anonymous
[P059 diagnosis](sh10rs-b000v002p059-1p-anonymous-anon-27241675299-battery-sungrow-winet-lan-summary.md)
left open (32.0 kWh at 331.9 V): a sum of packs is the likelier cause there too, though that
owner did not name a pack.

## Capability test

Outcome **2**: it did not run. The inverter reported "Key stop" rather than running, so every
leg was refused before a write; `readback`, `effects` and `restored` are empty, so nothing was
written and nothing needed restoring. This is a stopped inverter (the owner's key stop), not a
finding about the firmware. The PV cut on P067 stays unconfirmed; see
[the capability test](../concepts/capability-test.md).
