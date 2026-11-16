---
type: source
title: mkaiser-mac-prefixes-2026-11-16.md
source_path: raw/mkaiser-mac-prefixes-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - proxy
  - discovery
  - mac
  - mkaiser
---

# The MAC prefixes of the proxy and the inverter, 2026-11-16

Two neighbour-cache lookups from the Windows host that carries the dev
container, on [mkaiser](../entities/installation-mkaiser.md)'s own segment,
after [the same evening's proxy reading](mkaiser-modbus-proxy-2026-11-16-summary.md)
left the proxy and the inverter indistinguishable in the picker.

- **The inverter's own LAN port answers `AC:19:9F`**, Sungrow's one IEEE
  prefix. The second reading of an inverter port's prefix, after
  [peter_sm's eighteenth](sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md),
  and the first from another house.
- **The proxy's address answers a locally administered prefix** -- first
  octet `02`, IEEE's U/L bit set -- because the production Home Assistant
  runs on a virtual machine and a hypervisor invents its NIC's address. No
  manufacturer issues a prefix with that bit set, so this is stronger than
  "not Sungrow": see
  [telling a proxy from the inverter](../concepts/telling-a-proxy-from-the-inverter.md).
- **The cache answers only on the segment.** From the container it held one
  entry, the Docker gateway, which is why the same evening's search could
  not tell the two apart.

No address and no whole MAC was recorded: the last three octets identify one
unit.
