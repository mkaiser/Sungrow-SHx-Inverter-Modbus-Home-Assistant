---
type: query
title: Does a cluster slave mirror the master's EMS mode?
tags: [cluster, ems, capability-test, restore, open]
created: '2026-11-24'
query: "Does register 13050 on a cluster slave follow the master's, so that a write to the slave does not hold while the master is in forced mode?"
results_count: 1
---

# Does a cluster slave mirror the master's EMS mode?

**Open; one observation.** At [swo14](../entities/installation-swo14.md), on
[01011.95.03](../entities/firmware-sapphire-h-01011-95-03.md), the slave's capability test found 13050 at 2
where its snapshot held 0, wrote 0 five times and read 2 each time, and ended in outcome 5. It had not
written 13050 itself. The host's test was running at the same time, and 13050 read 0 on both inverters
minutes later ([the slave](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2-summary.md), [the host](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)).

- **For it**: the overlap, and that the slave held 2 against five writes and gave it up by itself.
- **Not excluded**: evcc or the YAML package writing 13050 while the car charged; a proxy handing the
  host's answer to the slave's port.
- **Against a plain always-mirror**: the slave's first run, the host's running beside it, restored cleanly
  ([first run](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md)); which check the host was in is not known.

What answers it: at a cluster with nothing else writing, EMS mode 2 written to the master and 13050 read
on the slave, then 0 written to the slave while the master holds 2. Until then, test one inverter of a cluster at a time.
