---
type: source
title: mkaiser-second-session-2026-11-17.md
source_path: raw/mkaiser-second-session-2026-11-17.md
ingested: '2026-11-17'
created: '2026-11-17'
tags: [discovery, contention, sweep, mkaiser, sh10rt, sapphire-h-b001-v000-p020]
---

# A sweep from the address already polling it, mkaiser, 2026-11-17

`.wiki/raw/mkaiser-second-session-2026-11-17.md` records the measurement the query
[why did the search miss the maintainer's inverter](../queries/why-did-the-search-miss-mkaisers-inverter.md)
asked for: hold a Modbus session open and sweep the same network from the same machine. Run at
06:35 local from the repository's dev container against
[mkaiser](../entities/installation-mkaiser.md)'s [SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), over the inverter's own LAN port, with
the container's own Home Assistant polling the inverter without a break since the previous
evening.

| Claim | Evidence | Status |
| --- | --- | --- |
| The inverter's own LAN port does not refuse a second TCP session from an address that already holds one | 12 of 12 connects accepted, 7.6 to 21.8 ms, while the same machine's Home Assistant polled it | one machine, two batches |
| A sweep from that address finds it | two full /24 sweeps, 4.0 s each, the inverter found by both | two sweeps |
| The sweeps cost the poller nothing | no lost connection in the polling Home Assistant's log over either sweep | two sweeps |
| Three addresses on the segment answer on port 502 | both sweeps, the same three | two sweeps |

So the explanation the query carried -- a port deaf to a second session from the polling address
-- **is wrong** for a Home Assistant connected straight to the inverter, and the search's miss on
the production instance needs another one.

**What this does not reach.** The production Home Assistant polls this inverter through a
**modbus-proxy on its own machine** ([the proxy reading](mkaiser-modbus-proxy-2026-11-16-summary.md)),
so the session held from that address belongs to the proxy, not to Home Assistant. This run used
a directly polling instance. If the miss is about that machine or its proxy, it is untouched, and
repeating the sweep from the production machine is what would settle it.
