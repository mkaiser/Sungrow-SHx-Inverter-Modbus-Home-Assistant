---
type: query
title: Can evcc drive a managed wallbox through Home Assistant?
query: Does evcc, through Home Assistant's entities alone, start, stop and regulate a car on a wallbox the inverter manages, and set the battery's modes?
results_count: 0
tags: [wallbox, evcc, ems, battery, open]
created: '2026-11-25'
---

# Can evcc drive a managed wallbox through Home Assistant?

**Open.** Nobody has watched it. `doc/evcc.md` is the setup to watch.

What it rests on:

- The controls work from Home Assistant with a car charging: 6, 8 and 10 A followed, stop in 1 s, start in 12 s
  ([gerd, 2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)).
- The battery stays at a lowered discharge limit: 499 W at 500 W
  ([mkaiser, 2026-11-08](../sources/mkaiser-import-limit-discharge-2026-11-08-summary.md)). 10 W, and whether the sun
  still charges the battery at that limit, are not measured here.

What would answer it: a surplus charge by evcc at [gerd](../entities/installation-gerd.md), and
`evcc meter verifybatterymodes` at [mkaiser](../entities/installation-mkaiser.md).
