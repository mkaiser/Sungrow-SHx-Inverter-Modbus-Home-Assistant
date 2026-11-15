---
type: query
title: Does a WiNet-S advertise over mDNS, and can discovery start there?
tags: [winet-s, wallbox, mdns, discovery]
created: '2026-11-11'
query: Does a WiNet-S, and a wallbox at its own address, advertise itself over multicast mDNS, on every firmware, with the TXT record measured at gerd?
results_count: 2
---

# Does a WiNet-S advertise over mDNS, and can discovery start there?

**Partly answered.** At [gerd](../entities/installation-gerd.md) both the
[WiNet-S](../entities/device-winet-s.md) and the [wallbox](../entities/device-wallbox.md) at its
own address answer mDNS questions with a `_http._tcp` service whose TXT record names the device,
its serial and its units, and the dongle's also names the inverter and the battery behind it
([the reading](../sources/gerd-mdns-2026-11-11-summary.md)). The inverter's own LAN port
advertises nothing.

**A multicast browse on a LAN answered** at [peter-sm](../entities/installation-peter-sm.md):
Home Assistant's own zeroconf, browsing `_http._tcp` for 2 s, heard the WiNet-S fitted to the
inverter, `WiNet-WebServer`, with a TXT record in gerd's layout (`board`, `inverter` with the
same trailing `1;4`), on `WINET-SV200.001.00.P045`
([twentieth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md)).

Still open:

- **Other firmware, other houses.** Two dongles, one wallbox; a wallbox heard by multicast, none.
- **Does `ethinfo` say wired or WiFi?** It is empty on gerd's dongle
  ([the reading](../sources/gerd-mdns-2026-11-11-summary.md)), which is on WLAN
  ([gerd](../entities/installation-gerd.md)). A wired dongle's record, beside the
  `user_inputs.transport` its diagnosis carries, would say whether it is the one way to tell the
  two apart that Modbus lacks ([WiNet-S](../entities/device-winet-s.md)). peter-sm's carries an
  address; whether that dongle is wired is not recorded (its diagnosis's transport is the
  inverter's own LAN port).
- **The fields nothing explains**: the battery's 8423 (0x20E7), the inverter's trailing `1;4`,
  the wallbox's `info=16256` (0x3F80), and every `;1;`.

What depends on it: the integration's manifest matches `_http._tcp` instances named
`WiNet-WebServer*` and `SUNGROW*`, so Home Assistant offers a dongle naming an inverter, and a
wallbox at its own address, with no search. The record decides only whether to offer; an entry is
made from [what answers](../concepts/identify-by-what-answers.md) over Modbus once the owner
confirms. The TXT fields are read by the layout measured at gerd
(`sungrow_modbus.network_names.LAYOUTS`), so a record laid out otherwise names fewer facts, never
wrong ones. An inverter on its own LAN port is found only by the sweep.

How it gets answered: from schema 27 every diagnosis carries a `network_names` section — the
Sungrow records heard by a multicast browse, the reverse-DNS name's first label and the MAC
vendor prefix, serials as stand-ins (`device-diagnosis/reference.md`). Its `mdns.state` answers
the multicast question per house; the name and the prefix are what a DHCP matcher for an
inverter's own LAN port would need. The first prefix: `AC:19:9F`, for peter-sm's inverter on its
own LAN port; one house is not yet a pattern.
