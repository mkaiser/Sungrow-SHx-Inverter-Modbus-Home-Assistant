---
type: concept
title: Telling a proxy from the inverter
tags: [proxy, discovery, mac, transport]
created: '2026-11-16'
---

# Telling a proxy from the inverter

A Modbus proxy forwards everything -- the serial, the device type,
[register 6100](../entities/register-6100.md) -- so over Modbus the proxy and
the inverter are **one device at two addresses**, and no register tells them
apart ([the reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)).
What separates them is outside Modbus. Three tests, each three-valued: absent
is never a verdict.

| Test | Says | Strength |
| --- | --- | --- |
| the address is Home Assistant's own | a proxy runs here | certain, but only where the searching Home Assistant *is* the host |
| the MAC prefix is locally administered | software invented this port, so a host is relaying | certain, and from any machine on the segment |
| the MAC prefix is a known hypervisor's | the same, said positively | certain for the hypervisors on the list |
| the MAC prefix is registered but not `AC:19:9F` | something is relaying | a note only |

## The U/L bit is the one that decides

Bit 1 of a MAC's first octet is IEEE's U/L bit, clear in every registered
prefix and set when a hypervisor, a bridge or a bond invents an address. So a
locally administered prefix does not say "not Sungrow", which a second
registration could undo and which hardware says too -- a
[RAK module](../entities/device-rak-wifi-module.md) carries RAKwireless's
`AC:1F:09`. It says **no manufacturer issued this port**, which neither an
inverter nor a communication module can be. Measured at
[mkaiser](../entities/installation-mkaiser.md)'s: the inverter's own LAN port
`AC:19:9F`, the proxy beside it a locally administered prefix
([the reading](../sources/mkaiser-mac-prefixes-2026-11-16-summary.md)).

That is why the picker ranks a card on this and merely annotates one on a
foreign registered prefix: being wrong the second way tells somebody their
inverter is a proxy.

## Hypervisors with a registered block

The bit misses a hypervisor that holds an IEEE block of its own, and the
common ones do: Proxmox has `BC:24:11` (registered June 2023), Hyper-V
`00:15:5D`, VMware `00:0C:29` and `00:50:56`, VirtualBox `08:00:27`, Xen
`00:16:3E`, Parallels `00:1C:42`. A virtual machine made on a current Proxmox
therefore carries a prefix no different in shape from a maker's -- which is
the maintainer's own stack, where only the machine's age put it on the other
side of the test.

Those prefixes are named in a short list (`wifi_module.VIRTUAL_MAC_PREFIXES`)
and rank a card like an invented address, because the claim is positive: a
port answering as an inverter from a VMware block is a relay, and Sungrow
would have to ship an inverter with one for it to be wrong. The list stays
short deliberately. Going stale costs a label and never a wrong one -- an
unlisted hypervisor falls through to the note -- while a list that grew to
Raspberry Pi and Intel would be an attempt to enumerate "not an appliance",
which is the note's job. QEMU's `52:54:00` and Docker's `02:42` are not on
it: they are locally administered and caught a step earlier.

## A registered foreign prefix needs the route

A communication module has a maker too, so a foreign prefix alone cannot tell
a dongle from a proxy. [Register 6100](../entities/register-6100.md) can: a
dongle refuses it, a proxy forwards it.

| | 6100 answers | 6100 refused |
| --- | --- | --- |
| `AC:19:9F` | the inverter's own port | -- |
| registered, foreign | a proxy | a communication module |
| locally administered | a proxy | a proxy in front of a module |
| no entry | unknown | unknown |

## Why there is often no entry

A TCP socket never carries the peer's MAC: the only MAC in an arriving frame
is the next hop's. The neighbour cache holds an entry only for an address on
the reader's own segment, and only once something has talked to it. Behind a
router, a VPN or a container bridge there is **no answer**, which says nothing
about the device -- the same rule as
[a failed read is not a refusal](failed-read-is-not-refusal.md). The
repository's own dev container is such a place: its whole cache is the Docker
gateway. The same line divides the mDNS browse: from the Windows host, one ARP
hop from the inverter, a 15-second browse heard 44 records and could say that
none was Sungrow's ([the browse](../sources/mkaiser-mdns-2026-11-16-summary.md));
from the container the same browse would have heard nothing and proved nothing.

From schema 28 a diagnosis records this about itself, as `on_device_segment`:
a reading taken off the segment says so, instead of leaving a null vendor
prefix and an empty mDNS browse to be read as findings about the device.

Read where it is available: `network_names.async_mac_prefix` (`/proc/net/arp`
on Linux, `arp -a` elsewhere), `wifi_module.is_locally_administered`, and the
picker's labels in `config_flow_schemas.py`. The diagnosis publishes the
prefix it found as `network_names.mac_vendor_prefix`, never the whole address:
the last three octets identify one unit
([serial anonymization](serial-anonymization.md)).
