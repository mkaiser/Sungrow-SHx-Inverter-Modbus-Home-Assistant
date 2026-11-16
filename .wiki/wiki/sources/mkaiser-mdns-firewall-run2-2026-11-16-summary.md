---
type: source
title: mkaiser-mdns-firewall-run2-2026-11-16.md
source_path: raw/mkaiser-mdns-firewall-run2-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - mdns
  - discovery
  - firewall
  - rak-module
  - mkaiser
---

# The firewall browse run a second time, 2026-11-16

The four-browse firewall test repeated at
[mkaiser](../entities/installation-mkaiser.md), three and a half hours after
[the first run](mkaiser-mdns-firewall-2026-11-16-summary.md), with the same
script unchanged (`.testdata/mdns-firewall-test.ps1`). Elevated, read only,
restore verified by read-back, exit 0. Source:
`.wiki/raw/mkaiser-mdns-firewall-run2-2026-11-16.md`.

It was run to settle what the first run left open: whether the eight records a
declined prompt costs are the same eight every time.

| State | Instances | `_http._tcp` | Sungrow |
| --- | --- | --- | --- |
| Allow (as found) | 46 | 4 | 0 |
| Rules disabled -- the prompt still on screen | 36 | 3 | 0 |
| Rules set to Block -- **declined** | 35 | 3 | 0 |
| Allow, restored | 47 | 4 | 0 |

**Counts are not comparable between runs** (44 / 35 / 37 / 44 the first time):
more devices were on air in the afternoon. The comparison is per record.

## Answered: the same eight, every time

Of the 42 instances heard in an allowed browse in **both** runs, 33 survived
all four degraded browses, **8 were lost in all four**, and one `_matter._tcp`
was lost once per run -- the disabled state in run 1, the blocked state in run
2. The eight are the ones the first run named, record for record: a NAS's
three, a door station's three, a streaming stick's one, and the
[RAK WiFi module](../entities/device-rak-wifi-module.md)'s `_rak47x._tcp`.

So the split is **reproducible and is a property of the record**, not of
timing. A contributor who declines the prompt loses the same four devices every
time, one of them an `_http._tcp` -- the type the Sungrow zeroconf matcher
browses ([the query](../queries/does-a-winet-s-advertise-over-mdns.md)).

## It is the record, not the host

A TV that was switched off during run 1 published four records from one
address: `_airplay._tcp` survived both degraded browses while `_googlecast`,
`_display` and `_ghp` were lost. One host, one address, one path -- so the
mechanism is not reachability, a route or a VLAN, but how that particular
responder answers. Those three records are also the only apparent disagreement
between the runs, and they disagree because the TV was off the first time.

## Not the address family

Each of the eight published both an IPv4 and an IPv6 address, as did nearly
every survivor, so "reachable over one IP version only" is ruled out.

**Still unexplained, and now worth explaining because it reproduces**: what
separates those eight from the 33. The hypothesis to test next is unicast
versus multicast answers -- Windows' "allow unicast response to multicast"
would let a unicast reply back past a per-application block while an answer
multicast to `224.0.0.251:5353` is dropped. That needs a packet capture, and
nothing the integration ships depends on it.

## A sixth browse, still no Sungrow

No Sungrow or WiNet record in any of the four, as in the five before it. The
inverter's own LAN port advertising nothing is now a floor six browses deep,
and still not proof
([an mDNS browse is a floor](../concepts/mdns-browse-is-a-floor.md)).

The four allowed browses taken across the day heard 44, 44, 46 and 47 and were
four different sets; the RAK module was present in run 2's restored browse and
absent from its baseline, the opposite of run 1.
