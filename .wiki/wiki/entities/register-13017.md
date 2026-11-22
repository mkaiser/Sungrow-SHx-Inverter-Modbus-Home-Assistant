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

A house that has run the forced startup check reads `0x55` afterwards and not the factory 0, which
the register refuses: the restore writes `0x55` in its place
([the restore](../concepts/capability-test-restore.md)). So a `0x55` on B001 firmware says a write
has happened there, not that the firmware differs.

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

**A running state that changes is not on its own evidence that it did.** At
[mkaiser](installation-mkaiser.md) on P020, with 13017 at `0x55` and nothing written that evening,
the inverter went `Starting` → `Stop` → `Running` → `Standby` by itself inside six minutes, a
fifteen-second running window, on a November night with the battery empty
([the engine run](../sources/mkaiser-forced-startup-2026-11-16-summary.md)). An inverter in
low-SoC standby stirs on its own, so the #444 question has to be answered by reading the register
back, not by watching the state.

**Read back that way, P020 does not flip it.** 13017 was left at `0xAA` at mkaiser's and read back
for **90 minutes 48 seconds** without changing -- the longest watch on record, against #444's
~20 minutes and bar12's 23. Dawn did not undo it either: PV first rose above 0 W at 59 minutes and
the register still read `0xAA` 31 minutes after that. The inverter ran for 56 minutes in the dark
on `0xAA` alone, with the battery at 0 %, before any PV
([the watch](../sources/mkaiser-forced-startup-left-on-2026-11-17-summary.md)). What could still
explain #444: other firmware, or iSolarCloud rewriting the register at a house connected to it.

## In the capability test

`diagnosis.sh tests <host> --forced-startup` is a mode of its own, because it needs the one state
every other check refuses: low-SoC standby, the battery within 5 % of its minimum and no PV. It
writes `0xAA`, waits up to 10 minutes for Running, writes `0x55`, waits up to 2 minutes for
Standby, and restores the register, the factory 0 as `0x55`
([the restore](../concepts/capability-test-restore.md)). Its row is the check *forced startup
under low SoC*, judged by the running state alone. In Home Assistant it is the
`run_capability_test` action with `forced_startup: true`, and **auto repeat
runs it by itself** in low-SoC standby until a kept run has established it
(`ContinuousCapabilityTest._forced_startup_due`, `low_soc_standby`).

**It has run on hardware**, at [mkaiser](installation-mkaiser.md) on P020 over the cable, from
Home Assistant, with the battery at 0.0 % against its 10 % minimum and no PV: left standby after
123 s, Running after 208 s, back in standby 16 s after `0x55`, verdict "the inverter did as it was
told", outcome 0 and no finding
([the engine run](../sources/mkaiser-forced-startup-2026-11-16-summary.md)). The guard admitted
low-SoC standby without argument, part B wrote that one probe and nothing else, and the restore
had nothing to do: the snapshot held `0x55` already, which is what the earlier run left. The
timing repeats: across nine days and three methods at this house, `Starting` came at 121, 123 and
122 s and `Running` at 215, 208 and 207 s
([2026-11-08](../sources/mkaiser-forced-startup-2026-11-08-summary.md),
[2026-11-16](../sources/mkaiser-forced-startup-2026-11-16-summary.md),
[2026-11-17](../sources/mkaiser-forced-startup-left-on-2026-11-17-summary.md)).

**On P022 the same**, at [gerd](installation-gerd.md)'s SH8.0RT over the cable, from the
capability test's forced startup mode, battery at 0.3 % against its 10 % minimum, no PV: 13017 read
the factory 0 before (no check had run there), left standby after 163 s, Running after 208 s with the
battery idle, back in standby 17 s after `0x55`, verdict "the inverter did as it was told", every
fault word 0. A second `0xAA` by hand right after took longer: Starting at 241 s, Running at 329 s
([the run](../sources/gerd-forced-startup-and-restart-2026-11-22-summary.md)). So three B001
firmwares now agree; whether P022 flips `0xAA` back by itself (#444) was not watched.

## In the integration

A switch, *Forced startup under low SoC* / *Zwangsstart bei niedrigem Ladezustand*: on writes
`0xAA`, off writes `0x55`, and its state is read from the register, the factory 0 as off
(`SWITCHES` in `scripts/generate/tables/writes.py`). It is created only where
`Capability.FORCED_STARTUP` answered (SH-CX excluded) **and** the firmware is in
`CONFIRMED_ON_FIRMWARE` for `Capability.FORCED_STARTUP_CONTROL`
([firmware gating](../concepts/firmware-gating.md)): P023, from
[the bar12 run](../sources/bar12-forced-startup-2026-11-07-summary.md), P020, from
[the mkaiser run](../sources/mkaiser-forced-startup-2026-11-08-summary.md), and P022, from
[the gerd run](../sources/gerd-forced-startup-and-restart-2026-11-22-summary.md). Other firmware
gets it from a watched start.
