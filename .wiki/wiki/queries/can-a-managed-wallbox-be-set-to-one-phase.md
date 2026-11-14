---
type: query
title: Can a managed wallbox be set to one phase over Modbus?
query: Is there a word at the inverter, or a wallbox word the inverter respects, that chooses one or three phases for a wallbox the inverter manages?
results_count: 0
tags: [wallbox, phases, ems, open]
created: '2026-11-14'
---

# Can a managed wallbox be set to one phase over Modbus?

**Open.** No document or report names one
([the sources](../sources/wallbox-phase-switching-sources-2026-11-14-summary.md)), and the
inverter switches the phases by itself
([a managed wallbox's phases](../concepts/managed-wallbox-phases.md)).

What is known at [gerd](../entities/installation-gerd.md):

- The wallbox's own 21204, written 1 with the car stopped, did not change the actual mode.
- The inverter's charger block, 33540-33550, has no word that changed with the phases.
- 33538 (85, shaped like 0x55/0xAA) and 33539 (161, shaped like a mode) sit just below the block
  and refused writes (exception 0x04) with charging off, in fast charge and in PV surplus alike;
  33539 read 161 in both modes
  ([gerd, 2026-11-14](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)).

What would answer it: read the inverter's holding 33501-33600 during a one-phase session (PV
surplus, energy purchase off, a small surplus, the battery above its minimum) and compare with the
three-phase baseline of 2026-11-14 (`plans/wallbox_tests.md`, test 5). If 33538 or 33539 moves
then, it reports the phases rather than sets them, as far as writes have shown.
