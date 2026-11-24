---
type: concept
title: The capability test's restore
tags: [capability-test, restore, safety]
created: '2026-10-29'
---

# The capability test's restore

What the [capability test](capability-test.md) changes, it puts back. These rules
exist so that a house is never left changed without anyone knowing.

- **The restore is never budgeted, never deadlined and never skipped.** Every
  early exit goes through it. **Seen on hardware**: *Diagnosis: stop* pressed
  60 s into part B, after six settings had been written and during the forced
  charge probe, put all seventeen back with zero mismatches in about 50 s,
  dropped the snapshot store, released the owner's controls and started no
  restart ([the run](../sources/mkaiser-stop-mid-run-2026-11-17-summary.md)).
  Before that only the simulator had seen a stop.
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
- **One word goes back as its equivalent.** [Register 13017](../entities/register-13017.md)
  holds 0 from the factory on every SH-RT, refuses 0 with exception 0x04, and treats 0 as off;
  the restore writes `0x55` (off), checks it by raw read, and says so in its row. The pair is
  `RESTORE_EQUIVALENT` in `capability_test/procedure.py`, and nothing else is restored as
  anything but the snapshot's word.
- **A control the owner sets after a run replaces that register's entry in the
  leftover snapshot.** The owner's value is the one the house should keep, so
  the inverter's snapshot drops the field and a managed wallbox's takes the
  owner's word, with the charge left off where the owner switched it off. While
  a run writes, the owner's controls refuse, so this happens only between a run
  that did not finish and its repair (`custom_components/sungrow_modbus/write_owner.py`,
  `tests/test_write_owner.py`; the maintainer's decision of 2026-11-15, in
  `doc/architecture.md`).
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
  factor alone (`src/sungrow_modbus/capability_test/restore.py`,
  `tests/test_capability_test.py`).
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
- **A restore that depends on a credential which can expire mid-run is not a
  restore.** The shipped test is immune: it writes over its own Modbus
  connection and holds nothing that expires. A one-off watch driving Home
  Assistant is not -- a token held from the start expired 29 minutes in, every
  restore attempt came back HTTP 401, and
  [register 13017](../entities/register-13017.md) stayed on for 50 minutes
  past the watch's end until a person put it back
  ([the watch](../sources/mkaiser-forced-startup-left-on-2026-11-17-summary.md)).
  Such a watch presses through `scripts/dev/ha_watch.py`, which mints its
  credential at the moment of restoring and never holds one.
- **Exit 5 is the one code meaning a house is left changed.** It can also be a value held by something else: at
  [swo14](../entities/installation-swo14.md) a cluster slave's 13050 read 2 through five restore writes while the
  host's run was under way, and 0 six minutes later ([the run](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2-summary.md),
  [open](../queries/does-a-cluster-slave-mirror-the-masters-ems-mode.md)). Test one inverter of a cluster at a time.
- **A failed restore is logged with its traceback** (`_LOGGER.exception` in
  `repairs.py`). It is the only record of why somebody's inverter still
  carries a test's values.
- `--restore <snapshot>` is the way out of a run that died halfway.
