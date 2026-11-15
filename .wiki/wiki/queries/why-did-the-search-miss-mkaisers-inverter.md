---
type: query
title: "Why did the search miss the maintainer's inverter?"
tags: [discovery, contention, mkaiser, open]
created: '2026-11-15'
query: "Does an inverter's own LAN port refuse a second TCP connection from an address that already holds one?"
results_count: 1
---

# Why did the search miss the maintainer's inverter?

**Open.** Two sweeps from the production Home Assistant on 0.1.0a40 found port 502 open only on
the [RAK WiFi module](../entities/device-rak-wifi-module.md), never on the
[mkaiser](../entities/installation-mkaiser.md) SH10RT, which the YAML package was polling through
the same Home Assistant; the dev container's connects to the inverter all completed in under
10 ms, and the manual step identified it at once
([the reading](../sources/mkaiser-network-discovery-2026-11-15-summary.md)). The sweep retries
slowly only when nothing answers, and the RAK module answered.

One explanation, unmeasured: the inverter's LAN port refuses or stalls a second connection from an
address that already holds one ([contention](../concepts/contention.md)). What answers it: from
one machine, hold a Modbus session open and time a second connect, then the same from two
machines.
