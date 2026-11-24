---
type: query
title: Does a WiNet-S advertise over mDNS, and can discovery start there?
tags: [winet-s, wallbox, mdns, discovery]
created: '2026-11-11'
query: Does a WiNet-S, and a wallbox at its own address, advertise itself over multicast mDNS, on every firmware, with the TXT record measured at gerd?
results_count: 8
---

# Does a WiNet-S advertise over mDNS, and can discovery start there?

**Partly answered.** At [gerd](../entities/installation-gerd.md) both the
[WiNet-S](../entities/device-winet-s.md) and the [wallbox](../entities/device-wallbox.md) at its
own address answer mDNS questions with a `_http._tcp` service whose TXT record names the device,
its serial and its units, and the dongle's also names the inverter and the battery behind it
([the reading](../sources/gerd-mdns-2026-11-11-summary.md)).

**An inverter's own LAN port advertises nothing, and that half is now measured rather than
inferred.** At [mkaiser](../entities/installation-mkaiser.md) -- an SH10RT on its own LAN port,
no dongle -- a 15-second browse from the Windows host on the house LAN heard **44 service
instances, four of them `_http._tcp`, and not one Sungrow record**: no `WiNet-WebServer`, no
`SUNGROW*`, and no match for `sungrow`, `winet` or `solar` in any instance name, server name or
TXT value ([the browse](../sources/mkaiser-mdns-2026-11-16-summary.md)). The host held an address
on the inverter's own /24 and the inverter in its ARP cache, so `on_device_segment` was true.
That is a `nothing_answered` with records heard beside it: the first reading of the unambiguous
kind. Eight further browses the same day, across three firewall states and two runs, found no
Sungrow record either ([run 1](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md),
[run 2](../sources/mkaiser-mdns-firewall-run2-2026-11-16-summary.md)).

**Nine browses with no Sungrow record is strong, and it is not proof.** The same runs caught the
[RAK WiFi module](../entities/device-rak-wifi-module.md) advertising under `_rak47x._tcp` in one
browse and missing from two others, all three of which counted 44 instances. A browse is a floor,
not a census ([the concept](../concepts/mdns-browse-is-a-floor.md)), so "no record heard" is
evidence against a device advertising, never a demonstration that it does not.

**A multicast browse on a LAN answered** at [peter-sm](../entities/installation-peter-sm.md):
Home Assistant's own zeroconf, browsing `_http._tcp` for 2 s, heard the WiNet-S fitted to the
inverter, `WiNet-WebServer`, with a TXT record in gerd's layout (`board`, `inverter` with the
same trailing `1;4`), on `WINET-SV200.001.00.P045`
([twentieth reading](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-18-summary.md)).

**A WiNet-S2 answers a multicast browse too, and its record names more.** At
[bigz2012](../entities/installation-bigz2012.md), on `WINET-SV300.001.03.P032`, a 5-second browse
from a machine on the inverter's own subnet heard one `_http._tcp` service -- the dongle's -- with
**two battery fields**, `battery1=2;200;...;SBR224;` and `battery2=3;201;...;SBR224;`, beside the
inverter and the board
([the reading](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)).
So the layout extends to a second pack with units of its own, and the record is where a house's
**per-pack serials** are legible at all. Its `inverter` field ends `1;3` where the two SH-RTs
measured end `1;4`, on a machine with four trackers, so that field is not the tracker count.

**Two dongles at one house are told apart**: at [swo14](../entities/installation-swo14.md) the browse heard
`WiNet-WebServer` and `WiNet-WebServer-2`, each naming its own inverter, the trailing pair `1;4` at the host and
`2;4` at the slave, so the first of the pair is **the inverter's unit id** there
([the reading](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md)). `ethinfo` is empty on both.

**The first real reverse-DNS label is `espressif`**, the same dongle's. peter-sm's was masked in
its document, so nothing was known of the shape before. A matcher keyed on "sungrow" in a hostname
would miss a WiNet-S2 entirely; the MAC prefix `AC:19:9F` is what the integration keys on, and it
is what that dongle reports too.

Still open:

- **Other firmware, other houses.** Two dongles, one wallbox; a wallbox heard by multicast, none.
- **A second house with no dongle.** One measured silence from an inverter's own LAN port is one
  house; what is known of the port is that it answers Modbus and is found by the sweep.
- **Which records a firewall drops.** Answered, over two runs
  ([run 1](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md),
  [run 2](../sources/mkaiser-mdns-firewall-run2-2026-11-16-summary.md)): declining the Windows
  prompt degrades the browse rather than silencing it, so `services_heard` stays non-zero while
  records go missing, and **it is the same eight records every time** -- 33 of the 42 heard
  allowed in both runs survived all four degraded browses, the same 8 were lost in all four, and
  one `_matter._tcp` moved. One of the eight is an `_http._tcp`, the type the matcher browses.
  It is the record and not the host: one TV's `_airplay._tcp` survived while its three other
  records, from the same address, were lost.
- **Why those eight.** Still open, and worth asking now that it reproduces. Not the address
  family (both sides publish IPv4 and IPv6). The hypothesis to test is unicast against multicast
  answers, which is a packet capture; nothing the integration ships waits on it.
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
own LAN port; one house is not yet a pattern. It is Sungrow's one prefix in the IEEE registry,
and the integration's DHCP matcher keys on it
([the maintainer's house](../sources/mkaiser-network-discovery-2026-11-15-summary.md)).

**`mdns.state` alone cannot answer it**, which is why the section now measures the reader too.
`nothing_answered` is the same word for "no Sungrow record among the eleven this machine heard"
-- a finding about the device -- and "this machine heard nothing at all", which is a bridge, a
VLAN or a firewall. From schema 28 two fields separate them: `mdns.services_heard` counts every
`_http._tcp` instance that answered, Sungrow or not, and `on_device_segment` says whether the
machine that ran the diagnosis holds an address on the device's network at all. Only a
`nothing_answered` with records heard beside it is evidence that an inverter's own LAN port
advertises nothing. Every reading taken before then is the ambiguous kind; the browse from the
maintainer's Windows host is the first of the other
([the browse](../sources/mkaiser-mdns-2026-11-16-summary.md)).

**The field answers less than it looks.** A firewall leaves `services_heard` non-zero and the
browse short, so the count says only that the machine was not deaf -- never that the browse was
complete ([a browse is a floor](../concepts/mdns-browse-is-a-floor.md)).
