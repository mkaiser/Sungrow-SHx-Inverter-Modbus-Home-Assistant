# The MAC prefixes of the proxy and the inverter, 2026-11-16

Taken by the maintainer on the Windows 11 host that carries the dev
container, which is on the house's own segment where the container is not.
Read only: one ICMP echo to populate the neighbour cache, then `arp -a` for
that address, which is what `network_names.async_mac_prefix` runs on Windows.
Follows the same evening's proxy reading
(`raw/mkaiser-modbus-proxy-2026-11-16.md`), which left the two cards
indistinguishable because the container's neighbour cache holds nothing but
the Docker gateway.

No address and no whole MAC here: the last three octets identify one unit,
and the proxy's prefix is the maintainer's own machine's.

## What the cache held

| Address | Vendor prefix | U/L bit |
| --- | --- | --- |
| the inverter's own LAN port | `AC:19:9F` | universally administered |
| the production Home Assistant, which runs the proxy | first octet `02` | locally administered |

Both answered the echo in 3 ms and both entries were `dynamisch` (dynamic),
so both were resolved by ARP on the segment rather than configured.

## What it decides

- **The inverter's own LAN port carries `AC:19:9F`.** The second reading of
  one, after peter_sm's eighteenth diagnosis, and the first from a different
  house. One of 87 published diagnoses carries the field at all.
- **The proxy's address carries a locally administered prefix**, which no
  manufacturer issues: IEEE's U/L bit is bit 1 of the first octet, clear in
  every registered prefix, and set by a hypervisor or a bridge inventing an
  address. The production Home Assistant runs on a virtual machine.
- So the neighbour cache does decide this pair, from a machine on the
  segment. It said nothing from the container for a reason no code reaches: a
  TCP socket never carries the peer's MAC, and the cache holds an entry only
  for an address on the reader's own segment.
