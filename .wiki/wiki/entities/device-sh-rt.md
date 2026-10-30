---
type: entity
title: SH-RT hybrid inverters
tags: [inverter, sh-rt, sapphire-h, three-phase]
created: '2026-10-29'
---

# SH-RT hybrid inverters

Sungrow's three-phase residential hybrids: SH10RT, SH10RT-20, SH10RT-V112,
SH8.0RT-V112 and SH6.0RT-V112 (`0x0E0D`) in this corpus. The firmware family is `SAPPHIRE-H`. Most of what
the integration knows was measured on these.

## What is established

- **Identity.** Register 5000 reports the device type code (for example
  `0x0E0E` on the SH8.0RT-V112), and 5002 reports the output type: 0 single,
  1 3P4L, 2 3P3L. Ask the inverter rather than inferring from the model
  name. `src/sungrow_modbus/inverter/registers.py`.
- **Unit id.** The inverter is usually unit 1. A cluster slave answers on
  unit **2**; see [identify by what answers](../concepts/identify-by-what-answers.md)
  and the [fwitten](installation-fwitten.md) pair.
- **Firmware decides what exists.** The same two inverters answer 31211 with
  the sentinel on [01011.95.03](firmware-sapphire-h-01011-95-03.md) and with
  0x55 on [P023](firmware-sapphire-h-b001-v000-p023.md); see
  [firmware gating](../concepts/firmware-gating.md).
- **MPPT3/4 answer 0xFFFF** on an SH10RT. Through a WiNet-S the same
  registers answer 0; see [zero means absent](../concepts/zero-means-absent.md).
- **Register 13074 writes in tens of watts** on every B001 firmware measured;
  see [register 13074](register-13074.md).
- **Inputs 2612 and 2628 come back in a padded frame**; see
  [padded frames](../concepts/padded-frames.md).
- **Few simultaneous sessions**, and 90 s of quiet to recover; see
  [contention](../concepts/contention.md).
- **A Modbus stop and start.** About 2 s to stopped. 3 to 4 minutes back to
  `0x0040 Running` in daylight and over six at night, then up to 20 s to
  generate; see [register 13000](register-13000.md) and the
  [control test](../concepts/control-test.md).
- **Inverter-reported load misses another generator.** `load_power` is the
  inverter's own output plus grid import; see
  [external generator](../concepts/external-generator.md).

## Surveys

Every SH-RT survey is listed in the [index](../index.md) under Sources.
The ones with a control test:
[mkaiser](installation-mkaiser.md), [gerd](installation-gerd.md),
[bar12](installation-bar12.md), [fwitten](installation-fwitten.md),
[peter-sm](installation-peter-sm.md) and [firetribe](installation-firetribe.md).
