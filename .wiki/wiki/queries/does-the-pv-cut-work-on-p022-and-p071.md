---
type: query
title: "Does the PV cut work on P022 and P071?"
tags: [pv-cut, register-31211, open]
created: '2026-10-29'
query: "Does writing 0xAA to 31211 stop PV on SAPPHIRE-H_B001.V000.P022 and PEARL-H_B000.V000.P071?"
results_count: 0
---

# Does the PV cut work on P022 and P071?

**Open.** [Register 31211](../entities/register-31211.md) answers 0x55 on
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md) and
[P071](../entities/firmware-pearl-h-b000-v000-p071.md), but a read shows that
the register is there, not what writing it does. Only
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md) is confirmed.

What answers it: a [control test](../concepts/control-test.md) with the cut
allowed, in daylight with at least 500 W of PV, on the inverter's own LAN
port. Run `survey.sh control <host> --cut-pv`, or use the device page's
button with **May it cut PV generation** on. On a `CONFIRMED`, commit the
survey and add its 13250 string to `CONFIRMED_ON_FIRMWARE`. On a T,
watch whether 13018 acts as well. The steps are in `plans/cut-pv-generation.md`.
