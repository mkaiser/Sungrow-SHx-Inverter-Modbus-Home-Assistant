---
type: entity
title: Register 13017 (forced startup under low SoC standby)
tags: [register, holding, command, specification]
created: '2026-11-05'
---

# Register 13017 (forced startup under low SoC standby)

Holding register 13017, Sungrow's *Forced Startup Under Low SOC Standby*, added in V1.1.7. Writing
`0xAA` starts an inverter that is waiting in standby because the battery reached its minimum SoC
and there is no PV; without it, the inverter waits for PV. Grid-connected only
([the datasheet notes](../sources/sungrow-datasheet-names-2026-11-05-summary.md)). A use: charging
an empty battery from the grid at night, which a sleeping inverter will not do.

Not to be confused with **input** 13017, *Daily direct energy consumption*: the two spaces are
separate ([protocol addresses](../concepts/protocol-addresses.md)).

## What the surveys read

From the committed surveys under `device-survey/results/inverter/`, **never `0xAA`**:

| Value | Where |
| --- | --- |
| 0 | every [SH-RT](device-sh-rt.md) on B001 firmware (P020, P022, P023) |
| `0x55` | every [SH-T](device-sh-t.md) (SH15T, SH20T, P071) |
| unavailable (`0xFFFF`) | every [SH-RS](device-sh-rs.md), and the SH-RT on [01011.95.03](firmware-sapphire-h-01011-95-03.md) |

So the register holds no lasting state worth showing: it is a **command**. What it reads after a
write has not been watched.

## In the integration

A diagnostic sensor today, *Forced startup under low SoC raw*, gated by `Capability.FORCED_STARTUP`
in `src/sungrow_modbus/hybrid_inverter/capabilities.py` (SH-CX excluded). Decided: it becomes a
button, *Force startup* / *Zwangsstart*, created only on firmware where a write has been watched
([firmware gating](../concepts/firmware-gating.md)); in `Todo.md`.
