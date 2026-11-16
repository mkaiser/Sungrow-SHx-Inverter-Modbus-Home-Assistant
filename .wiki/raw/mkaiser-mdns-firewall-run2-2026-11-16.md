# The firewall browse, run twice: is it the same eight every time?

The second run of the four-browse firewall test at the maintainer's **Windows
host on the house LAN**, elevated, three and a half hours after the first
(`mkaiser-mdns-firewall-2026-11-16.md`). Read only; nothing was written to the
inverter. No address here; the house's /24 is called "the home network".

Run to settle one question the first run left: the first run lost the same
eight records in both of its degraded states, and nothing explained *why those*
and not the other 35. A second run says whether the set is a property of the
responders or an accident of one afternoon.

Same script, unchanged: `.testdata/mdns-firewall-test.ps1`, four 15-second
browses of `_services._dns-sd._udp.local.` and then every type it names,
changing only the Windows Defender Firewall state for the two inbound rules on
the interpreter. Snapshot to disk first, changes in a `try/finally`, restore
verified by reading the rules back. **Exit 0: restored and verified.**

## The counts

| State | Instances | `_http._tcp` | Sungrow |
| --- | --- | --- | --- |
| Allow (as found) | 46 | 4 | 0 |
| Rules disabled -- the prompt still on screen | 36 | 3 | 0 |
| Rules set to Block -- **declined** | 35 | 3 | 0 |
| Allow, restored | 47 | 4 | 0 |

Against the first run's 44 / 35 / 37 / 44. **The counts are not comparable
between runs** -- the house had more devices on air at 15:49 than at 12:28 --
so the comparison below is made per record, not per count.

A sixth consecutive browse with no Sungrow record of any kind. Still a floor,
not a proof.

## Yes: the same eight, every time

42 instances were heard in an *allowed* browse in **both** runs. Classifying
each by whether it survived the four degraded browses, two per run:

| | Records |
| --- | --- |
| Survived all four degraded browses | 33 |
| **Lost in all four** | **8** |
| Lost in some but not others | 1 |

The eight are the same eight the first run named, device for device and record
for record:

- a NAS's three (`_http._tcp`, `_smb._tcp`, `_device-info._tcp`)
- a door station's three (`_psia._tcp`, `_axis-video._tcp`, `_workstation._tcp`)
- a streaming stick's `_amzn-wplay._tcp`
- the RAK WiFi module's `_rak47x._tcp`

So it is **not timing and not luck**. The split is a stable property of the
record, and `services_heard` loses the same four devices every time a
contributor declines the prompt -- one of them an `_http._tcp`, the type the
Sungrow matchers browse.

The one record that moved is a `_matter._tcp` instance, lost in the disabled
state in run 1 and in the blocked state in run 2: one loss per run, the other
way round each time. One borderline responder, not a second pattern.

## It is the record, not the host

The clearest evidence in either run comes from a device that was off during the
first one. A TV was on air for run 2 and published four records from one
address:

| Record | Degraded browses |
| --- | --- |
| `_airplay._tcp` | **survived both** |
| `_googlecast._tcp` | lost |
| `_display._tcp` | lost |
| `_ghp._tcp` | lost |

One host, one IP, one network path, four records, and the firewall state
separates them. Whatever the mechanism is, it is **not** "this host is
unreachable" and not a route or a VLAN. It is how that particular responder
answers.

This also explains the only apparent disagreement between the runs: run 2 lost
three records run 1 did not, and they are all this TV's. The TV was not
advertising at all during run 1. Nothing changed its mind; it was switched on.

## What it is not: the address family

The obvious first guess, that the lost responders are reachable over one IP
version only, is **wrong**. Every one of the eight published both an IPv4 and
an IPv6 address, and so did almost every survivor. The two `_matter._tcp`
records that survived every browse are the only IPv6-only entries in either
run.

**Still unexplained**, and now known to be worth explaining, since it is
reproducible: what distinguishes those eight records from the 33. The next
thing to test is whether the survivors answer the query by unicast to the
querier's source port, which Windows' "allow unicast response to multicast"
profile setting would let back in past a per-application block, while a
multicast-only responder's answer to `224.0.0.251:5353` is dropped. That is a
packet capture, not a browse, and it is not needed for anything the integration
ships.

## Two browses of one network still disagree

The allowed browses of run 2 heard 46 and 47 and were not the same set: the
RAK module was absent from the baseline and present in the restored run,
the exact opposite of run 1. Four allowed browses across the day, four
different sets. The count is no guide to membership.
