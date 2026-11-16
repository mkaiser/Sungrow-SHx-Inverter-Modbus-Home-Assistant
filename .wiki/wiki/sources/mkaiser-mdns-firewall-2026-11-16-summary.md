---
type: source
title: mkaiser-mdns-firewall-2026-11-16.md
source_path: raw/mkaiser-mdns-firewall-2026-11-16.md
ingested: '2026-11-16'
created: '2026-11-16'
tags:
  - mdns
  - discovery
  - firewall
  - rak-module
  - mkaiser
---

# What a declined firewall prompt does to an mDNS browse, 2026-11-16

Four 15-second browses from the maintainer's **Windows host on the house LAN**
at [mkaiser](../entities/installation-mkaiser.md), elevated, changing only the
Windows Defender Firewall state between them. The same afternoon as
[the first browse](mkaiser-mdns-2026-11-16-summary.md). Read only. Source:
`.wiki/raw/mkaiser-mdns-firewall-2026-11-16.md`.

| State | Instances | `_http._tcp` | Sungrow |
| --- | --- | --- | --- |
| Allow (as found) | 44 | 4 | 0 |
| Rules disabled -- the prompt still on screen | 35 | 3 | 0 |
| Rules set to Block -- **declined** | 37 | 3 | 0 |
| Allow, restored | 44 | 4 | 0 |

Baseline and restored agree exactly, so the drop is the firewall and not a
network that went quiet.

## A declined prompt degrades the browse; it does not silence it

The sub-question [the first browse](mkaiser-mdns-2026-11-16-summary.md) left
open is answered, and the answer is the bad one. `services_heard` would have
read **3** -- non-zero, and indistinguishable from a healthy reading -- with
eight or nine records missing, one of them an `_http._tcp`.

So **a non-zero `services_heard` does not mean the machine heard everything**,
and the rule the field was introduced with ("nothing answered beside a dozen
others is the device saying nothing") holds only against a *total* silence.
See [an mDNS browse is a floor](../concepts/mdns-browse-is-a-floor.md).

The same eight records were lost in both degraded states -- a NAS's three, a
door station's three, a streaming stick's one, and the RAK module's -- with one
`_matter._tcp` lost in the disabled state only. **Why those and not the other
35 is unexplained**: the pattern is stable across both states, so it is a
property of the responders or of what the firewall lets back in, not of timing.

## The RAK WiFi module does advertise over mDNS

**This corrects two pages.** The
[RAK WiFi module](../entities/device-rak-wifi-module.md) answered in the
baseline run, under a service type of its own:

| Field | Value |
| --- | --- |
| instance | `rak475_service_` plus six hex digits |
| type | `_rak47x._tcp.local.` |
| port | 5000 |
| `MAC` | the whole address in clear, prefix `AC:1F:09` |
| `VER` | `1.9.0.10.12-2.13.4` |
| `TEST` | `Let's go` |

The six hex digits are the MAC's last three octets, the same ones its DHCP
hostname carries ([serial anonymization](../concepts/serial-anonymization.md)
is why neither is published here). Like a
[WiNet-S](../entities/device-winet-s.md), it hands its MAC to anyone on the
LAN who asks.

It is **intermittent**: heard in the baseline run, absent from the restored run
fifteen minutes later, and absent from
[the first browse](mkaiser-mdns-2026-11-16-summary.md) earlier the same day --
both of which still counted 44 instances.

## Two browses of one network disagree

Baseline and restored both heard 44 and **were not the same 44**: the baseline
had the RAK module, the restored run a `_nearbypresence._tcp` instance whose
name is a fresh UUID each time. `async_mdns_services` browses
`_services._dns-sd._udp.local.` for the window to learn which types exist, then
browses those types, so a device advertising under an unusual type is heard
only if its type announcement lands in that first window
(`src/sungrow_modbus/discovery.py`).

## probe.py crashed, and lost records doing it

The first attempt died part way through the baseline listing:
`UnicodeEncodeError: 'charmap' codec can't encode character '�'`.
`discovery.py` decodes a TXT value with `errors="replace"`, so a value that is
not text becomes U+FFFD; Windows PowerShell 5.1 gives the child a cp1252
stdout, which cannot encode it. The trigger was a Thread border router's binary
`_meshcop` record.

**Records print sorted by instance name**, so what is lost is everything
sorting after the offender -- `SUNGROW*` and `WiNet-WebServer` among them. The
reader would have seen a short list with no Sungrow in it and no reason to
doubt it: the very false negative `services_heard` exists to prevent.

Fixed: `main` reconfigures stdout and stderr to UTF-8 with
`errors="backslashreplace"` before anything prints
(`device-diagnosis/scripts/python/probe.py`). Verified by re-running under
`PYTHONIOENCODING=cp1252` -- 44 instances, the `_meshcop` record printed, no
traceback.
