---
type: entity
title: Register 13052 (forced charge/discharge power)
tags: [register, holding, write, forced-charge, capability-test]
created: '2026-11-21'
---

# Register 13052 (forced charge/discharge power)

Holding register 13052, the power a forced charge or discharge runs at, 1 W per count, documented as
"0-100 % of BDC rated power". It acts only in forced mode (EMS mode 2); in self-consumption the inverter
ignores it. The integration's `battery_forced_charge_discharge_power`, and the power every forced check of
the [capability test](../concepts/capability-test.md) commands through.

## What the hardware does

- **Its hard limit is the inverter's rated power, not the battery's**: on gerd's SH8.0RT-V112
  ([P022](firmware-sapphire-h-b001-v000-p022.md)) 8000 W is stored and 8100, 9000 and 10000 W are
  refused with exception 0x04; an SH10RT's limit is 10000 W, the maintainer reports
  ([the day](../sources/gerd-auto-repeat-2026-11-21-summary.md)).
- **The battery-derived maximum is not enforced**: one step over it is stored, on P022 (4960 W over
  4860 W, gerd) and on P023 ([peter-sm](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-14-summary.md)).
- **A house can hold a value the register would now refuse**: gerd's held 10000 W, written before the
  integration by some other path, so a run that wrote over it could not put it back (exit 5). Such a
  value is written back to itself before a run touches the register, and the register is left out of the
  run if it is refused.
