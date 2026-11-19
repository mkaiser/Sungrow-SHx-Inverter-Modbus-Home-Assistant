---
type: entity
title: Installation brendan
tags: [installation, brendan]
created: '2026-11-05'
---

# Installation brendan

An [SH10RS](device-sh-rs.md) on [P067](firmware-sunstone-h-b000-v002-p067.md) with two SBR224
packs, through a [WiNet-S](device-winet-s.md) on Ethernet, with the owner's other pollers
running. One reading, with a capability test that was refused: the inverter was key-stopped.

- Register 5639 reads 44.8 kWh, the two packs together, against 488.8 V of one stack.
- 31211 answers 0x55; the PV cut and the 13074 scale are unmeasured.
- **`total_battery_charge` reads 6,374.1 kWh against a discharge total of 12,708.0 kWh**, which no
  battery can do: its high word (13042) is missing a wrap, and the real figure is about 12,927.7 kWh.
  The register is wrong on every [P067](firmware-sunstone-h-b000-v002-p067.md) machine read.

## Diagnoses

- [SH10RS, B000.V002.P067, brendan, a WiNet-S on Ethernet, capability test refused](../sources/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md)
