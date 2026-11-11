---
type: source
title: gerd-mdns-2026-11-11.md
source_path: raw/gerd-mdns-2026-11-11.md
ingested: '2026-11-11'
created: '2026-11-11'
tags:
  - winet-s
  - wallbox
  - mdns
  - discovery
  - gerd
---

# gerd's devices over mDNS, and their web pages, 2026-11-11

What [gerd](../entities/installation-gerd.md)'s [WiNet-S](../entities/device-winet-s.md), his
[wallbox](../entities/device-wallbox.md) and his inverter's own LAN port advertise over mDNS, asked
one device at a time by unicast over a VPN, and which of them serve a web page. Source:
`raw/gerd-mdns-2026-11-11.md`.

| Device | mDNS | Advertises | Web page |
| --- | --- | --- | --- |
| WiNet-S | answers | `_http._tcp`, instance `WiNet-WebServer`, host `SUNGROW` + its serial, SRV port 80 | HTTPS on 443 only; port 80 refuses |
| wallbox at its own address | answers | `_http._tcp`, instance and host `SUNGROW` + its serial, SRV port **516** | none: 80 and 443 closed |
| inverter's own LAN port | silent | nothing | none |

- **The dongle's TXT record lists every device behind it**, each with its serial:
  `inverter=1;3598;<serial>;1;516;SH8.0RT;1;4;`,
  `battery1=2;200;8423;<serial>;1;516;SBR096;` and `board=SUNGROW;1;WiNet-S;<serial>;1;`. The
  wallbox's own record is `board=SUNGROW;3;AC22E-01;<serial>;1;248;` beside `info=16256;516;1;`.
- **The serials are the measured devices'.** The inverter's and the wallbox's stand-ins
  (`anon-00267885816`, `anon-41346964423`) are those of gerd's committed diagnoses.
- **Fields that match what Modbus measured**: 3598 is 0x0E0E, the SH8.0RT-V112's device type
  code at 4999 (`src/sungrow_modbus/hybrid_inverter/layout.py`); the battery's 2 and 200 are an
  SBR's unit through a dongle and over the cable, and the wallbox's 3 and 248 its unit through a
  dongle and at its own address
  ([identify by what answers](../concepts/identify-by-what-answers.md)); 516 is the TLS port
  both the dongle and the wallbox serve. The rest (the battery's 8423, the inverter's
  trailing `1;4`, the wallbox's 16256, every `;1;`) is not explained by anything measured.
- **An `_http` record is not a web page.** The dongle's names port 80, which refuses; the
  wallbox's names its Modbus TLS port.
- **One house, one firmware of each**, and unicast questions only: whether a multicast browse
  sees the same is [still open](../queries/does-a-winet-s-advertise-over-mdns.md).
