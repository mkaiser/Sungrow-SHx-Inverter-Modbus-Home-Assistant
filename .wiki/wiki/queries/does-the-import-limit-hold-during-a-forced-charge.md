---
type: query
title: "Does the site import limit hold during a forced charge on an SH-RT?"
tags: [register-32998, import-limit, sh-rt, forced-charge, open]
created: '2026-11-07'
query: "Does register 32998 cap grid import while an SH-RT force-charges its battery, and does it depend on how the charge is commanded?"
results_count: 11
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

**And the model does not either.** At [peter-sm](../entities/installation-peter-sm.md) the cap held
twice on an **SH10RT-V112** on P023, ulfben's model, over the cable with the charge commanded
through 13050 and 13051: 800 W against 1438 W of import, and 1730 W against 2359 W, each returning
when the cap came off
([the twenty-first](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-19-summary.md)
and [twenty-second readings](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-20-summary.md)).
That leaves how ulfben's charge was commanded as the only untried explanation.

A scheduled charge is capped too: at bar12 the forced-charging schedule's 4099 W charge was cut to
~510-690 W under a 1.00 kW cap ([the schedule run](../sources/bar12-import-limit-schedule-2026-11-07-summary.md)).
And P022 obeys, over the cable and through a WiNet-S, EMS and schedule
([gerd](../sources/gerd-import-limit-2026-11-08-summary.md),
[the schedule](../sources/gerd-import-limit-schedule-2026-11-08-summary.md)). So on P020, P022 and P023, cable and
dongle, EMS and schedule, the cap has held every charge this repository commanded.

**Except at a cluster master, so far.** At [fwitten](../entities/installation-fwitten.md)'s master
SH10RT-V112 on P023, the charge commanded through 13050 and 13051 by the capability test, a 1090 W
cap left import at 1718 W against 1724 W before; the charge obeyed and the battery sat well above
its floor ([the run](../sources/fwitten-import-limit-engine-2026-11-22-summary.md)). Four
more caps there, on the master, the slave and both, under charges of 1250 W and 3601 W, did nothing
either, every word read back ([the cluster run](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md)). The other failure on record,
swo14's on 01011.95.03, is a cluster master too. Backup mode, on at both, does not stop
it at a lone SH10RT on P020 ([the run](../sources/mkaiser-import-limit-backup-mode-2026-11-24-summary.md)). Whether ulfben's house is a
cluster is not known, and it is now worth asking.

What would answer it: how ulfben's charge is commanded (iSolarCloud's own forced charge is not
among those tried), his B001 firmware, and whether a cap was set at all when it charged. The model
and the firmware are no longer candidates.
