---
type: source
title: mkaiser-mdns-2026-11-16.md
source_path: raw/mkaiser-mdns-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - mdns
  - discovery
  - firewall
  - mkaiser
---

# A multicast browse from the maintainer's Windows host, 2026-11-16

`probe.py mdns --seconds 15`, run from the **Windows host on the house LAN**
rather than the dev container, at [mkaiser](../entities/installation-mkaiser.md):
one [SH10RT](../entities/device-sh-rt.md) on its own LAN port, no
[WiNet-S](../entities/device-winet-s.md), a
[RAK WiFi module](../entities/device-rak-wifi-module.md) beside it. Read only.
Source: `.wiki/raw/mkaiser-mdns-2026-11-16.md`.

## The reader was on the device's segment

The host holds an address on the same /24 as the inverter, and its ARP cache
holds the inverter under Sungrow's `AC:19:9F`
([how a prefix is read](../concepts/telling-a-proxy-from-the-inverter.md)).
That is `on_device_segment: true`: nothing -- no router, no VLAN, no container
bridge -- sat between the browse and the inverter.

## The machine heard, and Sungrow was not among it

| Fact | Value |
| --- | --- |
| service instances heard, all types | 44 |
| service types | 35 |
| `_http._tcp` instances (`mdns.services_heard`) | **4** |
| Sungrow records | **0** |
| browse length | 15 s |

The four `_http._tcp` instances are a printer, an AV receiver, the house NAS
and a wallbox of another make. Beside them: the router, Home Assistant itself,
a Thread border router, three ESPHome nodes, Matter, AirPlay, SMB.

Searched case-insensitively over the whole capture -- instance names, server
names and every TXT value -- `sungrow`, `winet` and `solar` matched **nothing**.

So this is the unambiguous half of the pair the schema-28 fields were added
for: `nothing_answered` **with four records heard beside it**, from a machine
on the device's own segment.

- **No Sungrow record answered**, from a machine on the device's own segment
  with 44 records to prove it was listening. Four further browses the same
  afternoon, across three firewall states, found none either
  ([the firewall runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)).
  Five browses with no Sungrow record is strong evidence that an SH10RT's own
  LAN port advertises nothing; it is not proof, because a browse is a floor and
  this one missed a device that was advertising
  ([a browse is a floor](../concepts/mdns-browse-is-a-floor.md)).
- **The RAK WiFi module was not among the 44** -- which this page first read as
  its advertising nothing. **That was wrong.** It advertises under
  `_rak47x._tcp`, a type nothing else on the network uses, and a browse hears
  it only sometimes
  ([the firewall runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md),
  [the module](../entities/device-rak-wifi-module.md)). A record missing from
  one browse is not a device that is silent
  ([a browse is a floor](../concepts/mdns-browse-is-a-floor.md)).

## The Windows Defender Firewall prompt

The open sub-question, answered from the rules the firewall holds. **No prompt
appeared on this run and no rule was added**, because the prompt had been
answered for this interpreter before: Windows held two inbound Allow rules
named `TCP Query User{...}` and `UDP Query User{...}` against the interpreter's
path, which is the name Windows writes when somebody clicks *Allow access* on
the dialog. The pair is what answering grants:

| | |
| --- | --- |
| direction | inbound |
| protocols | TCP **and** UDP, in two rules |
| local port | any -- not 5353 |
| profiles | Private and Public |
| scope | the interpreter binary, not the script |

**Windows' own mDNS rule does not cover a Python process.** `mDNS (UDP-In)` is
enabled on all three profiles but scoped to `svchost.exe`, service `dnscache`;
Edge and WebView2 carry their own. So every fresh interpreter that binds 5353
raises the dialog once, and a diagnosis run by double-clicking a new Python on
Windows will raise it.

**Answered, and badly.** Declining does **not** silence the browse: it degrades
it. Four browses differing only in firewall state put a declined prompt at 37
instances and 3 `_http._tcp` against a baseline of 44 and 4, with the baseline
reproduced exactly after restoring
([the firewall runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)).
`services_heard` would have read 3 -- non-zero and healthy looking -- eight
records short ([a browse is a floor](../concepts/mdns-browse-is-a-floor.md)).

## An install note

`pip install -e ".[discovery]"` alone does not let `probe.py` start on a bare
interpreter: it imports `modbus_connection.tmodbus`, whose `serialx` comes only
from `modbus-connection`'s `tmodbus` extra (`pip install tmodbus` does not do
it; the serial support is `tmodbus[async-serial]`). On a clean Python 3.14.3
the probe died with `ModuleNotFoundError: No module named 'serialx'` until
`pip install "modbus-connection[tmodbus]"` was run too. The mDNS browse itself
needs neither -- only the module-level import does
(`device-diagnosis/scripts/python/probe.py`).
