---
type: query
title: Does a WiNet-S advertise over mDNS, and can discovery start there?
tags: [winet-s, wallbox, mdns, discovery]
created: '2026-11-11'
query: Does a WiNet-S, and a wallbox at its own address, advertise itself over multicast mDNS, on every firmware, with the TXT record measured at gerd?
results_count: 1
---

# Does a WiNet-S advertise over mDNS, and can discovery start there?

**Partly answered.** At [gerd](../entities/installation-gerd.md) both the
[WiNet-S](../entities/device-winet-s.md) and the [wallbox](../entities/device-wallbox.md) at its
own address answer mDNS questions with a `_http._tcp` service whose TXT record names the device,
its serial and its units, and the dongle's also names the inverter and the battery behind it
([the reading](../sources/gerd-mdns-2026-11-11-summary.md)). The inverter's own LAN port
advertises nothing.

Still open:

- **Multicast.** The questions were unicast to each device's port 5353, over a VPN that does not
  carry multicast. A responder that answers those almost always answers a multicast browse too,
  but no browse on a LAN has been recorded. `device-diagnosis/scripts/python/probe.py mdns`, run
  on a machine in the house, answers it.
- **Other firmware, other houses.** One dongle, one wallbox.
- **Does `ethinfo` say wired or WiFi?** It is empty on gerd's dongle
  ([the reading](../sources/gerd-mdns-2026-11-11-summary.md)), which is on WLAN
  ([gerd](../entities/installation-gerd.md)). A wired dongle's record, beside the
  `user_inputs.transport` its diagnosis carries, would say whether it is the one way to tell the
  two apart that Modbus lacks ([WiNet-S](../entities/device-winet-s.md)).
- **The fields nothing explains**: the battery's 8423 (0x20E7), the inverter's trailing `1;4`,
  the wallbox's `info=16256` (0x3F80), and every `;1;`.

What it would change: a `zeroconf` matcher in the manifest would find a dongle and a wallbox with
no sweep, already knowing the model, serial, units and port. A record is still a hint, never an
identity: an entry is made from [what answers](../concepts/identify-by-what-answers.md) over
Modbus. An inverter on its own LAN port is found only by the sweep.
