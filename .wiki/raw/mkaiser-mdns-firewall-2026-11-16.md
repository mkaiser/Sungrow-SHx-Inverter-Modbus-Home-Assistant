# What a declined firewall prompt does to an mDNS browse, 2026-11-16

Taken from the maintainer's **Windows host on the house LAN**, elevated, the
same afternoon as the browse in `mkaiser-mdns-2026-11-16.md`. Read only;
nothing was written to the inverter. No address here; the house's /24 is called
"the home network".

Four 15-second browses, changing only the Windows Defender Firewall state
between them. The two inbound rules for the interpreter were snapshotted to
disk first, the changes sat in a `try/finally`, and the restore was verified by
reading the rules back -- it reported restored, and the fourth run confirms it.

## The result

| State | Instances | `_http._tcp` | Sungrow |
| --- | --- | --- | --- |
| Allow (as found) | 44 | 4 | 0 |
| Rules disabled -- the prompt still on screen | 35 | 3 | 0 |
| Rules set to Block -- **declined** | 37 | 3 | 0 |
| Allow, restored | 44 | 4 | 0 |

The baseline and the restored run agree exactly on both counts, so the drop is
the firewall and not a network that went quiet.

## A declined prompt does not silence the browse. It degrades it.

This is the bad case. `services_heard` would have read **3** -- non-zero, and
indistinguishable from a healthy reading -- while eight or nine records were
missing, among them one of the four `_http._tcp`. A reader applying the rule
"nothing answered beside a dozen others is the device saying nothing" would
have believed a degraded browse.

The same eight records were lost in both degraded states:

- the NAS's three records (`_http._tcp`, `_smb._tcp`, `_device-info._tcp`)
- a door station's two (`_psia._tcp`, `_axis-video._tcp`) and its
  `_workstation._tcp`
- a streaming stick's `_amzn-wplay._tcp`
- the RAK module's `_rak47x._tcp` (below)

The disabled state lost one more, a `_matter._tcp`. **Why these and not the
other 35 is not explained by anything measured here.** The pattern is stable
across both states, so it is a property of the responders or of what the
firewall lets back in, not of the browse's timing.

## The RAK WiFi module does advertise over mDNS

Heard in the baseline run, and this corrects both the 2026-11-15 reading
through Home Assistant and the browse committed earlier today:

```
rak475_service_<six hex digits>._rak47x._tcp.local.
  type      _rak47x._tcp.local.
  port      5000
  MAC       AC:1F:09:<redacted>
  VER       1.9.0.10.12-2.13.4
  TEST      Let's go
```

The six hex digits are the MAC's last three octets, the same ones its DHCP
hostname carries; the `MAC` field publishes the whole address in clear, to
anyone on the LAN. The RAKwireless prefix `AC:1F:09` identifies it as the
module beside the inverter beyond doubt.

It is **intermittent**: present in the baseline run, absent from the restored
run fifteen minutes later, and absent from the browse committed earlier today.
Both of those runs still counted 44 instances, so the count is no guide to
whether a particular device was heard.

## A browse is a floor, not a census

The baseline and the restored run both heard 44 instances and **were not the
same 44**: the baseline had the RAK module, the restored run had a
`_nearbypresence._tcp` instance whose name is a fresh UUID each time. Two
browses of the same network, minutes apart, from the same host, with the same
firewall state, disagree about which devices exist.

`async_mdns_services` browses `_services._dns-sd._udp.local.` for the full
window to learn which service types exist, then browses those types. A type
whose announcement misses that first window is never asked about, so a device
advertising under an unusual type -- `_rak47x._tcp` here -- is heard or not
heard depending on when it last spoke.

## probe.py crashed, and lost records doing it

The first attempt at this run died part way through the baseline listing with
`UnicodeEncodeError: 'charmap' codec can't encode character '�'`.

`discovery.py` decodes an mDNS TXT value with `errors="replace"`, so a value
that is not text becomes U+FFFD. Windows PowerShell 5.1 gives the child Python
a cp1252 stdout, which has no mapping for U+FFFD, and `print` raises. The
trigger was a Thread border router's `_meshcop` record, whose `id`, `xa` and
`xp` fields are binary. Under a UTF-8 console the same record prints as
mojibake and survives, which is why the earlier browse did not hit it.

**The records print sorted by instance name**, so what is lost is everything
sorting after the offender. `SUNGROW*` and `WiNet-WebServer` both sort after
`Home Assistant OpenThread Border Router`. A contributor running this on
Windows would have seen a short list with no Sungrow in it, the traceback on
stderr, and no reason to doubt it.

Fixed in `device-diagnosis/scripts/python/probe.py`: `main` reconfigures stdout
and stderr to UTF-8 with `errors="backslashreplace"` before anything prints.
Verified by re-running with `PYTHONIOENCODING=cp1252`, the condition that
crashed it: 44 instances, the `_meshcop` record printed, no traceback.
