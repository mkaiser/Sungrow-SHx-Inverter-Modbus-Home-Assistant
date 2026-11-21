---
type: query
title: "Why did the search miss the maintainer's inverter?"
tags: [discovery, contention, mkaiser, answered]
created: '2026-11-15'
query: "Why did a sweep from the production Home Assistant not find the inverter's own LAN port?"
results_count: 4
---

# Why did the search miss the maintainer's inverter?

**Answered: it does not reproduce.** Two sweeps from the production Home Assistant on 0.1.0a40 found port 502 open only on
the [RAK WiFi module](../entities/device-rak-wifi-module.md), never on the
[mkaiser](../entities/installation-mkaiser.md) SH10RT, which the YAML package was polling through
the same Home Assistant; the dev container's connects to the inverter all completed in under
10 ms, and the manual step identified it at once
([the reading](../sources/mkaiser-network-discovery-2026-11-15-summary.md)). The sweep retries
slowly only when nothing answers, and the RAK module answered.

**Narrowed on 2026-11-16.** A sweep of the same /24 from the dev container -- a machine holding
no session of its own -- found the inverter's own LAN port and identified it, in the same
round as the proxy on the production Home Assistant's machine
([the proxy reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)). So the port is
not deaf to a sweep; what it does under a sweep *from the address already polling it* is
still the question.

**That explanation is now measured, and it is wrong.** On 2026-11-17 the dev container swept the
same /24 while its *own* Home Assistant had been polling the inverter without a break since the
previous evening: 12 of 12 connects accepted in 7.6 to 21.8 ms, both full sweeps found the
inverter, and the poller lost no connection over either
([the run](../sources/mkaiser-second-session-2026-11-17-summary.md)). An inverter's own LAN port
does **not** refuse a second TCP session from an address that already holds one, so
[contention](../concepts/contention.md) does not explain the miss.

**What is left.** The production Home Assistant does not poll this inverter directly: it goes
through a **modbus-proxy on its own machine**
([the proxy reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)), so the session held
from that address is the proxy's, and the sweep there runs beside a proxy rather than beside a
direct session. The measurement that would settle it is the same sweep **from the production
machine**, with the proxy running: if the inverter is found there too, the miss was never about
sessions at all and the sweep's own result on that host is what to look at.

**Measured on 2026-11-20, and it does not reproduce.** After a reinstall (0.1.0a45 or a preview build
after it, with `discovery.py` unchanged since a40), the search run **from the production machine, with
the proxy running** and the YAML package polling through it, found the inverter's own LAN port and the
proxy, called the proxy a proxy, and counted both as one inverter by serial
([the sweep](../sources/mkaiser-production-sweep-2026-11-20-summary.md)). Neither a session held from
the sweeping address nor a proxy beside the sweep explains the 2026-11-15 miss, and the same code on
the same host now finds it. What went wrong that day is not recoverable from the one reading, and
nothing in the search changes for it; a second miss anywhere reopens this.
