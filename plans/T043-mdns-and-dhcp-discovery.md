# T043 - mDNS and DHCP discovery: what is still open

**Does a WiNet-S advertise over mDNS?** Yes (wiki: the mDNS query):
gerd's dongle and wallbox advertise `_http._tcp` with TXT records naming
model, serial and units, the dongle's for every device behind it, and
python-zeroconf (Home Assistant's library) resolves and parses both; the
inverter's LAN port answers nothing. A multicast browse on a LAN is
answered too, at peter_sm's on 2026-11-15, whose inverter MAC prefix
`AC:19:9F` is the first for a DHCP matcher. Built: the diagnosis's
`network_names` (schema 27, released) and the zeroconf matcher
(released; `WiNet-WebServer*` and `SUNGROW*` on `_http._tcp`, where the
record only decides whether to offer, Modbus identifies on confirm and
nothing set up is ever moved), and the DHCP matcher (0.1.0a41,
`wifi_module.py`), which offers a port for Sungrow's one IEEE prefix
`AC199F*` and links a RAK WiFi module (`rakmodule-*`) to the inverter
its owner names. Outstanding:
- **Other houses, other firmware.** One dongle and one wallbox so far;
  both matchers wait on diagnoses carrying `network_names`, and the DHCP
  matcher on a house whose inverter port takes its address by DHCP (a
  fixed address is never seen). Two prefix readings so far, both
  `AC:19:9F`: peter_sm's and the maintainer's, the second taken from the
  Windows host because the dev container's neighbour cache holds only
  the Docker gateway (wiki: telling a proxy from the inverter).
- **A browse the reader cannot have spoiled**, at a house with a dongle.
  Taken at the maintainer's, which has none: 44 records heard and no
  Sungrow among them, from the Windows host, on the segment (wiki: an
  mDNS browse is a floor). So an inverter's own LAN port advertising
  nothing is measured, and what is left is the dongle's half from a
  reader known not to have been deaf. Schema 28's `services_heard` and
  `on_device_segment` say which a document is, from 0.1.0a43 on.
- **Why those eight records and not the other 33.** Which records a
  firewall drops is settled over two runs of
  `.testdata/mdns-firewall-test.ps1` (wiki: an mDNS browse is a floor):
  a declined prompt degrades the browse rather than silencing it, so
  `services_heard` stays non-zero and looks healthy, and **it is the
  same eight every time** -- of the 42 instances heard allowed in both
  runs, 33 survived all four degraded browses and the same 8 were lost
  in all four, one of them an `_http._tcp`. It is the record and not the
  host: one TV's `_airplay._tcp` survived while its three other records,
  from the same address, were lost. Open: what separates the eight. Not
  the address family. The hypothesis is unicast against multicast
  answers, which Windows' "allow unicast response to multicast" would
  split exactly this way -- a packet capture on the Windows host, not a
  browse. **Nothing the integration ships waits on it**; it would only
  let the README tell a contributor what declining costs.
- **Does `ethinfo` say wired or WiFi?** It is empty on gerd's dongle,
  which is on WiFi; it may carry the Ethernet details when the dongle is
  wired. Answer it from the corpus: compare `ethinfo` with
  `user_inputs.transport` (`winet_lan` / `winet_wlan`) as the diagnoses
  arrive. bar12 has published both transports of one dongle, so a rerun
  there is the cleanest pair. If it holds, `wifi_or_ethernet` (today
  "not determinable over Modbus") can say what the dongle reports.
- **The fields nothing explains**: the battery's 8423 (0x20E7), the
  inverter's trailing `1;4`, the wallbox's `info=16256` (0x3F80), every
  `;1;`. More houses, compared with what Modbus measured there.
- **Should the diagnosis record the Windows firewall state** beside
  `services_heard`? Open, and a design question rather than a
  measurement: a non-zero count currently reads as healthy when a
  declined prompt has thinned it. Binding 5353 does raise the prompt on
  every fresh interpreter -- Windows' own `mDNS (UDP-In)` rule is scoped
  to `svchost.exe` and does not cover Python -- and the README now tells
  a contributor to allow it.
- A WiNet-S's *Visit* link for a cable entry, found by the inverter
  serial in its TXT (a link on the inverter, or the dongle as its own
  device).
