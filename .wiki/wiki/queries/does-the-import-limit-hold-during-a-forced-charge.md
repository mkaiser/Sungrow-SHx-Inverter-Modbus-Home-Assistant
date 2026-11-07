---
type: query
title: "Does the site import limit hold during a forced charge on an SH-RT?"
tags: [register-32998, import-limit, sh-rt, forced-charge, open]
created: '2026-11-07'
query: "Does register 32998 cap grid import while an SH-RT force-charges its battery, and does it depend on how the charge is commanded?"
results_count: 2
---

# Does the site import limit hold during a forced charge on an SH-RT?

**Open, narrowed.** On an [SH10RS](../entities/device-sh-rs.md) [register 32998](../entities/register-32998.md)
held a meter-measured import cap
([discussion #546](../sources/discussion-546-site-import-power-limit-summary.md)). On
[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md) it **holds during a forced charge**
commanded through 13050 and 13051: 1978 W of import against a 2.00 kW cap, the charge cut from
4500 W to ~1500 W ([the run](../sources/mkaiser-import-limit-2026-11-07-summary.md)). With PV it
caps grid import alone. At 1 (0.01 kW) the forced charge drew only on PV
([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)). On ulfben's [SH10RT-V112](../entities/device-sh-rt.md) the battery
force-charges at full power whatever it is set to, by the owner's report, before and after a
firmware update.

Not known:

- whether the SH10RS test included a forced charge, or only household load;
- whether P023 differs from P020;
- how ulfben's charge was commanded: iSolarCloud, the EMS mode registers (13050, 13051) or the
  forced-charging schedule (33208-33219);
- which B001 firmware (register 13250) the SH10RT-V112 runs.

What would answer it: the same run on a P023 SH-RT, and on P020 a forced charge commanded by
the forced-charging schedule (33208-33219) instead of 13050 and 13051.
