---
type: query
title: "Does the site import limit hold during a forced charge on an SH-RT?"
tags: [register-32998, import-limit, sh-rt, forced-charge, open]
created: '2026-11-07'
query: "Does register 32998 cap grid import while an SH-RT force-charges its battery, and does it depend on how the charge is commanded?"
results_count: 6
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
([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)), and the capability test's
check confirmed it ([the engine run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)). On ulfben's [SH10RT-V112](../entities/device-sh-rt.md) the battery
force-charges at full power whatever it is set to, by the owner's report, before and after a
firmware update.

Not known:

- whether the SH10RS test included a forced charge, or only household load;
- how ulfben's charge was commanded: iSolarCloud, the EMS mode registers (13050, 13051) or the
  forced-charging schedule (33208-33219);
- which B001 firmware (register 13250) the SH10RT-V112 runs.

P023 does not differ: at [bar12](../entities/installation-bar12.md)'s SH10RT-20 a 1.00 kW cap held
a 1250 W forced charge to ~950 W of import, over the cable and written through a WiNet-S, ulfben's
transport ([the bar12 runs](../sources/bar12-import-limit-2026-11-07-summary.md)). So neither the
firmware nor the dongle explains the report.

A scheduled charge is capped too: at bar12 the forced-charging schedule's 4099 W charge was cut to
~510-690 W under a 1.00 kW cap ([the schedule run](../sources/bar12-import-limit-schedule-2026-11-07-summary.md)).
And P022 obeys, over the cable and through a WiNet-S
([gerd](../sources/gerd-import-limit-2026-11-08-summary.md)). So on P020, P022 and P023, cable and
dongle, EMS and schedule, the cap has held every charge this repository commanded.

What would answer it: how ulfben's charge is commanded (iSolarCloud's own forced charge is not
among those tried), his B001 firmware, and whether a cap was set at all when it charged.
