---
type: concept
title: The control test's restore
tags: [control-test, restore, safety]
created: '2026-10-29'
---

# The control test's restore

What the [control test](control-test.md) changes, it puts back. These rules
exist so that a house is never left changed without anyone knowing.

- **The restore is never budgeted, never deadlined and never skipped.** Every
  early exit goes through it.
- **The snapshot is flushed before the first write**: beside the script from
  the CLI, and in Home Assistant's own store from the integration. Both
  drivers remove it only once everything is back **and read back**. A dry run
  writes none, and `--restore` removes the file it restored. A leftover
  snapshot on the next setup becomes a repair. **No snapshot file for a day
  means no writes that day.**
- **A restore writes the snapshot's raw word, and checks it by raw read.**
  Writing the *value* back goes through the scale under test, which can leave
  a register a decade off. The scaled write is only the fallback, for
  firmware that multiplies the raw word too ([register 13074](../entities/register-13074.md)).
- **A restore is a statement about where the register is**, not about
  whether a write succeeded. **Over a confirmed cable** it reads before it
  writes, so a register that held its value throughout is never reported
  unrestored.
- **Through a dongle it always writes**, because the read is the
  [WiNet-S](../entities/device-winet-s.md)'s stale cache: a write that had
  landed read as "already holding its original value" and was never undone.
  That left a forced-charging window at [gerd](../entities/installation-gerd.md)
  between the [2026-11-01 dongle run](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)
  and the [next cable snapshot](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md).
  There an accepted write is the evidence, and 13074 goes out at its measured
  factor alone (`src/sungrow_modbus/control_test/restore.py`,
  `tests/test_control_test.py`).
- **Through a dongle it puts back only what the run touched.** The snapshot
  there is the same cache, and the dongle snapshot of 2026-11-01 held a window
  the cable had already put back, so writing every snapshot word would put an
  older figure over the real one. The snapshot records each field the run
  writes, refused writes included, and flushes that **before** the write
  (`Snapshot.touched`). A register the run did write goes back to the word the
  dongle reported, which is wrong only if it was changed over another path
  since the dongle last read it.
- **A restore on its own measures the transport first.** `--restore` and
  Home Assistant's repair run with no preflight, and the default is a cable.
- **Exit 5 is the one code meaning a house is left changed.**
- **A failed restore is logged with its traceback** (`_LOGGER.exception` in
  `repairs.py`). It is the only record of why somebody's inverter still
  carries a test's values.
- `--restore <snapshot>` is the way out of a run that died halfway.
