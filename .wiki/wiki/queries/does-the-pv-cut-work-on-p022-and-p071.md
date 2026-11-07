---
type: query
title: "Does the PV cut work on P022 and P071?"
tags: [pv-cut, register-31211, answered]
created: '2026-10-29'
query: "Does writing 0xAA to 31211 stop PV on SAPPHIRE-H_B001.V000.P022 and PEARL-H_B000.V000.P071?"
results_count: 3
---

# Does the PV cut work on P022 and P071?

**Answered: yes on both.** [Register 31211](../entities/register-31211.md)
answers 0x55 on both, but a read shows that the register is there, not what
writing it does.
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md) is confirmed by a
capability test at [gerd](../entities/installation-gerd.md) (2938 W, 0 W, 1913 W;
[the diagnosis](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)), as
[P023](../entities/firmware-sapphire-h-b001-v000-p023.md) is.
[P071](../entities/firmware-pearl-h-b000-v000-p071.md) is diagnosed only through
a WiNet-S, and that does not block it: the SH-RS's
[P065](../entities/firmware-sunstone-h-b000-v002-p065.md) was confirmed through a WiNet-S
([Jam3s97](../sources/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan-summary.md),
3465 W, 0 W, 3092 W), so a dongle forwards the write and the behavioural leg is enough. P071 is
confirmed the same way at [ra1k-0](../entities/installation-ra1k-0.md)'s SH20T: 20421 W, 28 W,
20395 W ([the diagnosis](../sources/sh20t-b000v000p071-3p-ra1k-0-anon-94125810090-battery-sbh400-winet-wlan-2-summary.md)). Both are in `CONFIRMED_ON_FIRMWARE`.

Still open on the T: whether 13018 acts as well; the capability test does not write it.
