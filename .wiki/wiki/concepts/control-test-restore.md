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
  whether a write succeeded. It reads before it writes, so a register that
  held its value throughout is never reported unrestored.
- **Exit 5 is the one code meaning a house is left changed.**
- **A failed restore is logged with its traceback** (`_LOGGER.exception` in
  `repairs.py`). It is the only record of why somebody's inverter still
  carries a test's values.
- `--restore <snapshot>` is the way out of a run that died halfway.
