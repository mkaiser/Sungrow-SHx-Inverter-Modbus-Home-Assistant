---
type: concept
title: An mDNS browse is a floor, not a census
tags: [mdns, discovery, firewall]
created: '2026-11-16'
---

# An mDNS browse is a floor, not a census

**Every record a browse hears is evidence that a device is there. No number of
records is evidence that nothing else is.** A browse answers "at least these",
never "exactly these", and three separate mechanisms shorten the list without
saying so. The same rule as
[a failed read is not a refusal](failed-read-is-not-refusal.md), one layer out.

This is why `mdns.services_heard` is read carefully. The field was introduced
to tell two silences apart: a device saying nothing, which is a finding, from a
machine hearing nothing, which is a bridge or a VLAN
([telling a proxy from the inverter](telling-a-proxy-from-the-inverter.md)).
It does that, and only that. **A non-zero count does not mean the machine heard
everything** -- it means the machine was not deaf.

## A firewall degrades the browse rather than silencing it

Measured at [mkaiser](../entities/installation-mkaiser.md) over four browses
differing only in Windows Defender Firewall state
([the runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)):

| State | Instances | `_http._tcp` |
| --- | --- | --- |
| allowed | 44 | 4 |
| no rule -- the prompt still on screen | 35 | 3 |
| **declined** -- a Block rule | 37 | 3 |
| allowed, restored | 44 | 4 |

A declined prompt would have published `services_heard: 3`: non-zero, healthy
looking, eight records short. The same eight were lost in both degraded states,
and **why those and not the other 35 is unexplained**.

On Windows every fresh interpreter that binds UDP 5353 raises that prompt once
-- Windows' own `mDNS (UDP-In)` rule is scoped to `svchost.exe` and does not
cover a Python process ([the first browse](../sources/mkaiser-mdns-2026-11-16-summary.md)).
So a contributor who clicks the wrong button produces a reading that looks
sound.

## A type nobody asked about is never heard

`async_mdns_services` browses `_services._dns-sd._udp.local.` for the window to
learn which service types exist, then browses those types
(`src/sungrow_modbus/discovery.py`). A device whose type announcement misses
that first window is never asked about at all.

The [RAK WiFi module](../entities/device-rak-wifi-module.md) is the measured
case: it advertises under `_rak47x._tcp`, a type nothing else on the network
uses, and it was heard in one browse and missed in two others the same
afternoon -- all three of which counted 44 instances.

## Two browses of one network disagree

Those same two 44-record browses, minutes apart from one host with one firewall
state, **were not the same 44**. The count is stable; the membership is not. A
count repeating is therefore no evidence that a browse was complete.

## What follows for a finding

- **A record heard is a fact.** Publish it.
- **A record not heard is not a fact.** "No Sungrow record" from one browse is
  weak; from five browses across firewall states it is strong, and it is still
  not proof. The inverter's own LAN port is in the second position
  ([open](../queries/does-a-winet-s-advertise-over-mdns.md)).
- **A count is not a quality score.** Read `services_heard` as "was this
  machine deaf", not "was this browse complete".
- **Rendering must not be able to drop records either.** `probe.py` once
  crashed part way through a sorted listing on a console that could not encode
  a binary TXT value, losing every record sorting after it -- `SUNGROW*` among
  them ([the runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)).
