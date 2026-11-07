---
type: entity
title: Register 31213 (shutdown at a 0 % power limit)
tags: [register, holding, active-power-limit, undocumented, isolarcloud]
created: '2026-11-05'
---

# Register 31213 (shutdown at a 0 % power limit)

Holding register 31213 decides what the inverter does when its **active power limit is 0 %**:
`0xAA` stops it, `0x55` keeps it running at 0 W. **It is in no Sungrow protocol document**
([the datasheet notes](../sources/sungrow-datasheet-names-2026-11-05-summary.md)): it was found by
watching what iSolarCloud writes, as "Shutdown at active power limit ratio of 0%", after an SH15T
shut down when set to 0 % ([issue #554](../sources/issue-554-active-power-limit-registers-summary.md)).
The limit it reacts to acts at the inverter's AC output (holding 13089/13090), not at the grid
connection point as the feed-in limit does.

## What the diagnoses read

From the committed diagnoses under `device-diagnosis/results/inverter/`:

| Value | Where |
| --- | --- |
| `0x55` | every [SH-RT](device-sh-rt.md), over cable and through a WiNet-S alike; [Jam3s97's](installation-jam3s97.md) SH10RS on P065; [fullhd23's](installation-fullhd23.md) SH15T; one of [ra1k-0's](installation-ra1k-0.md) three SH20T runs |
| `0xAA` | the [SH-RS](device-sh-rs.md) of [bleughb](installation-bleughb.md) (P057), [brendan](installation-brendan.md) (P067), an anonymous P059 and an anonymous SH6.0RS on P068 ([the diagnosis](../sources/sh60rs-b000v001p068-1p-anonymous-anon-17579213881-battery-sbr192-winet-summary.md)); the SH15T of [GalKar](installation-galkar.md) and [jm493](installation-jm493.md) |
| 0 | two of ra1k-0's SH20T runs |

**Both values of the pair exist**, and inverters of one model differ (SH10RS, SH15T), so it is a
setting someone made, not a model constant. The dongle is not the cause: the inverters read over
a cable and through a WiNet-S read `0x55` both ways. Why ra1k-0's SH20T reads 0 in two runs and
`0x55` in a third, all through a WiNet-S, is not known; a 0 is not evidence of anything
([zero means absent](../concepts/zero-means-absent.md)).

## In the integration

A diagnostic binary sensor, **Shutdown inverter when limited to 0 % power**
(`Derived.apl_shutdown_at_zero` in `src/sungrow_modbus/hybrid_inverter/derived.py`): on for `0xAA`,
off for `0x55`, unknown for anything else, a 0 included. The number itself
(`apl_shutdown_at_zero_raw`) is a sensor only where an entry keeps the YAML package's entity ids,
for that history. Nothing writes it.
