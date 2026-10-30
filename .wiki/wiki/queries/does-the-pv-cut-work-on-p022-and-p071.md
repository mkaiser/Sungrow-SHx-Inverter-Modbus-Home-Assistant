---
type: query
title: "Does the PV cut work on P022 and P071?"
tags: [pv-cut, register-31211, open]
created: '2026-10-29'
query: "Does writing 0xAA to 31211 stop PV on SAPPHIRE-H_B001.V000.P022 and PEARL-H_B000.V000.P071?"
results_count: 1
---

# Does the PV cut work on P022 and P071?

**P022: yes. P071: open.** [Register 31211](../entities/register-31211.md)
answers 0x55 on both, but a read shows that the register is there, not what
writing it does.
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md) is confirmed by a
control test at [gerd](../entities/installation-gerd.md) (2938 W, 0 W, 1913 W;
[the survey](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)), as
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md) is.
[P071](../entities/firmware-pearl-h-b000-v000-p071.md) is surveyed only through
a WiNet-S, so it is still unconfirmed.

What answers it: a [control test](../concepts/control-test.md) with the cut
allowed, in daylight with at least 500 W of PV, on the inverter's own LAN
port. Run `survey.sh control <host> --cut-pv`, or use the device page's
button with **May it cut PV generation** on. On a `CONFIRMED`, commit the
survey and add its 13250 string to `CONFIRMED_ON_FIRMWARE`. On a T,
watch whether 13018 acts as well. The steps are in `plans/cut-pv-generation.md`.
