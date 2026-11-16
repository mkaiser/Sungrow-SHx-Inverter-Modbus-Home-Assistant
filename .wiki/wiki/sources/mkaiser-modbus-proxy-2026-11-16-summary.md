---
type: source
title: mkaiser-modbus-proxy-2026-11-16.md
source_path: raw/mkaiser-modbus-proxy-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - proxy
  - discovery
  - transport
  - register-6100
  - mkaiser
---

# A Modbus proxy at the maintainer's house, 2026-11-16

What the network search and a config entry make of a house where a
modbus-proxy runs beside the production Home Assistant, in front of
[mkaiser](../entities/installation-mkaiser.md)'s SH10RT on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md). Read from a dev
container on the container bridge, not on the house's segment; nothing
written. Source: `raw/mkaiser-modbus-proxy-2026-11-16.md`.

| | |
| --- | --- |
| addresses swept | 1270 |
| answered the port scan | 3 |
| identified as a Sungrow | 2: the inverter's own LAN port, and the proxy |
| serial | one, `anon-37323352958`, at both |

- **The proxy and the inverter are one card each, and read alike.** Both
  carried the route note "the inverter's own LAN port": the flow's probe of
  [register 6100](../entities/register-6100.md) answered **through the
  proxy**, which agrees with the proxy read at an anonymous SH10RT-V112
  ([contention](../concepts/contention.md)).
- **Neither was named a proxy, and that is not the container's doing.** Home
  Assistant names a proxy by its own addresses, so it names one only where
  the searching Home Assistant *is* the proxy's host. Here the proxy sits
  beside the production Home Assistant, which was not the one searching. The MAC's
  vendor prefix -- `AC:19:9F` is Sungrow's one IEEE registration
  ([the discovery reading](mkaiser-network-discovery-2026-11-15-summary.md)) --
  would have named it from any machine, but an ARP entry exists only on the
  same segment and the container is behind a bridge, so it was **none**,
  which says nothing, by design.
- **The entry's own 6100 probe got no answer through the proxy**, three times:
  at setup, after a reload and after a cold boot. Pointed at the inverter's
  own LAN port it read **direct** within a minute, and back on the proxy it
  was unknown again. So the flow's probe and the entry's probe disagree about
  one address; the sessions differ (a short connection of the flow's own
  against Home Assistant's shared `modbus` connection), and which of the two
  explanations holds is
  [open](../queries/does-a-modbus-proxy-carry-6100.md).
- **The ordering of two cards that read alike was decided by the host
  string**, which put the proxy first because `.125` sorts before `.35`. The
  right card for the wrong reason, and the reason would pick the other way at
  a house whose proxy has the higher address. Fixed in
  `custom_components/sungrow_modbus/config_flow_schemas.py` (`_address_order`,
  `tests/test_config_flow_proxy.py`).
- **The search from a machine holding no session found the inverter at once**,
  where two sweeps from the production Home Assistant had not
  ([why the search missed it](../queries/why-did-the-search-miss-mkaisers-inverter.md)).
- **An ordinary entry carried 195 entities on one device page** -- 112
  primary, 58 diagnostic (17 the diagnosis and
  [capability test](../concepts/capability-test.md)), 25 config -- with the
  mode select offering all three modes and *Diagnosis: start* unavailable at
  *Read only*. Moving the entry between the two addresses, twice, kept its
  entities and history.
