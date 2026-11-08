---
type: entity
title: Register 13017 (forced startup under low SoC standby)
tags: [register, holding, switch, specification, write]
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

## What the diagnoses read

From the committed diagnoses under `device-diagnosis/results/inverter/`, **never `0xAA`**:

| Value | Where |
| --- | --- |
| 0 | every [SH-RT](device-sh-rt.md) on B001 firmware (P020, P022, P023) |
| `0x55` | every [SH-T](device-sh-t.md) (SH15T, SH20T, P071) |
| unavailable (`0xFFFF`) | every [SH-RS](device-sh-rs.md), and the SH-RT on [01011.95.03](firmware-sapphire-h-01011-95-03.md) |

Sungrow's document says the same of it
([hybrid protocol V1.1.17](../sources/hybrid-protocol-v1-1-17-summary.md)): only `0xAA` is a value,
and "this function is only active when the inverter is in grid-connected mode ... and does not work
in off-grid scenarios". So a watch of the write needs a grid-connected inverter.

## What a write does

Watched at [bar12](installation-bar12.md) on [P023](firmware-sapphire-h-b001-v000-p023.md), over
the cable and through a [WiNet-S](device-winet-s.md), with the battery below its minimum SoC
([the run](../sources/bar12-forced-startup-2026-11-07-summary.md)), and the same at
[mkaiser](installation-mkaiser.md) on [P020](firmware-sapphire-h-b001-v000-p020.md) over the cable:
Starting after 2 min 1 s, Running after 3 min 35 s, Standby again ~21 s after 0x55, and 0x01 and 0
refused ([the run](../sources/mkaiser-forced-startup-2026-11-08-summary.md)):

- **It is a switch, not a pulse.** `0xAA` wakes an inverter in low-SoC Standby with no other
  command (Starting after 2.5-4 min, Running after ~5 min, battery idle), reads back `0xAA`, and
  keeps the inverter running: 23 minutes later it was still `0xAA` and Running.
- **`0x55` is off**: a running inverter at low SoC returns to Standby within ~20 s.
- **Only `0xAA` and `0x55` are taken**: 0, 0x01 and 0xFF are refused with exception 0x04. So the
  factory 0 cannot be written back; a restore writes `0x55`.
- Through the WiNet-S the same, and the dongle's readback is current.
- **A forced charge does not need it**: an EMS forced charge or the forced-charging schedule wakes
  a standby inverter by itself in ~2 min ([the import limit runs](../sources/bar12-import-limit-2026-11-07-summary.md)).

One owner reports the inverter flipping `0xAA` to `0x55` by itself ~20 minutes after the write
(issue #444, firmware not stated); at bar12 it had not after 23 minutes.

## In the capability test

`diagnosis.sh tests <host> --forced-startup` is a mode of its own, because it needs the one state
every other check refuses: low-SoC standby, the battery within 5 % of its minimum and no PV. It
writes `0xAA`, waits up to 10 minutes for Running, writes `0x55`, waits up to 2 minutes for
Standby, and restores the register, the factory 0 as `0x55`
([the restore](../concepts/capability-test-restore.md)). Its row is the check *forced startup
under low SoC*, judged by the running state alone. In Home Assistant it is the
`run_capability_test` action with `forced_startup: true`. No run is on record yet.

## In the integration

A switch, *Forced startup under low SoC* / *Zwangsstart bei niedrigem Ladezustand*: on writes
`0xAA`, off writes `0x55`, and its state is read from the register, the factory 0 as off
(`SWITCHES` in `scripts/generate/tables/writes.py`). It is created only where
`Capability.FORCED_STARTUP` answered (SH-CX excluded) **and** the firmware is in
`CONFIRMED_ON_FIRMWARE` for `Capability.FORCED_STARTUP_CONTROL`
([firmware gating](../concepts/firmware-gating.md)): P023, from
[the bar12 run](../sources/bar12-forced-startup-2026-11-07-summary.md), and P020, from
[the mkaiser run](../sources/mkaiser-forced-startup-2026-11-08-summary.md). Other firmware gets it
from a watched start.
