# A multicast browse from the maintainer's Windows host, 2026-11-16

Taken from the **Windows host on the house LAN**, deliberately not from the
dev container, whose Docker bridge carries no multicast and whose neighbour
cache holds only the gateway. Read only; nothing was written to the inverter.
No address here; the house's /24 is called "the home network".

The house: one SH10RT on its own LAN port, **no WiNet-S**, with the older
RAK WiFi module beside it.

## What was run

```
pip install -e ".[discovery]"
python device-diagnosis\scripts\python\probe.py mdns --seconds 15
```

The first command is not enough to run `probe.py` on a bare interpreter.
`probe.py` imports `modbus_connection.tmodbus`, which imports `serialx`, and
`serialx` arrives only with `modbus-connection`'s `tmodbus` extra. On Python
3.14.3 with nothing else installed the probe died with
`ModuleNotFoundError: No module named 'serialx'` until
`pip install "modbus-connection[tmodbus]"` was run as well. `pip install tmodbus`
alone does not do it either -- the serial support is `tmodbus[async-serial]`.
The repository's own `[discovery]` extra (`zeroconf>=0.39.0`) was already
satisfied; `zeroconf` 0.151.3.

## The reader could hear

- The host holds an address on the home network's /24, the same /24 as the
  inverter -- `on_device_segment` would be `true`.
- The host's ARP cache holds the inverter, with MAC vendor prefix `AC:19:9F`,
  Sungrow's. So the two are one ARP hop apart and multicast between them is
  not crossing anything.
- The interface is WLAN, profile Private. Three other adapters are up
  (Tailscale and two Hyper-V vEthernet switches); `zeroconf` binds them all.

## What answered

**44 service instances, across 35 service types**, in 15 seconds.

Of those, **four are `_http._tcp`** -- the count the diagnosis publishes as
`mdns.services_heard`:

| `_http._tcp` instance | What it is |
| --- | --- |
| the printer's | an inkjet printer |
| the receiver's | an AV receiver |
| the NAS's | the house NAS |
| the charger's | a wallbox of another make |

The rest, by type: `_matter._tcp` 3, `_esphomelib._tcp` 3, `_tr064._tcp` 2,
`_fbox._tcp` 2, and one each of `_airplay`, `_amzn-wplay`, `_axis-video`,
`_canon-chmp`, `_device-info`, `_esphomebuilder`, `_heos-audio`,
`_home-assistant`, `_igd`, `_igd2`, `_ipp`, `_ipps`, `_l2tpv3`,
`_libmediasrv`, `_meshcop`, `_nearbypresence`, `_pdl-datastream`, `_printer`,
`_psia`, `_qobuz-connect`, `_raop`, `_sendspin`, `_smb`, `_spotify-connect`,
`_tf-warp-cm`, `_tidalconnect`, `_trel`, `_uscan`, `_uscans`, `_workstation`.
Home Assistant announced itself (`_home-assistant._tcp`, 2026.11.1), as did
the router, a Thread border router and three ESPHome nodes.

## Nothing Sungrow answered

Case-insensitively, **zero** matches for `sungrow`, `winet`, `solar` or `SG`
followed by a digit anywhere in the whole 15-second capture -- not in an
instance name, not in a server name, not in a TXT value. No
`WiNet-WebServer`. No `SUNGROW*` instance.

So:

- **The inverter's own LAN port advertises nothing over mDNS**, heard from a
  machine on its own segment, with 44 records to prove the machine was
  listening.
- **The RAK WiFi module advertises nothing over mDNS** either. It was not
  among the 44, under `rakmodule-` or any other name.

## The Windows Defender Firewall prompt

**No prompt appeared on this run, because one had already been answered.**
The firewall already held two inbound rules for the interpreter, and the run
added none:

| Rule name | Protocol | Action | Profiles | Local port |
| --- | --- | --- | --- | --- |
| `TCP Query User{...}C:\python314\python.exe` | TCP | Allow | Private, Public | Any |
| `UDP Query User{...}C:\python314\python.exe` | UDP | Allow | Private, Public | Any |

The `Query User{GUID}` prefix is what Windows writes when somebody clicks
**Allow access** on the "Windows Defender Firewall has blocked some features
of this app" dialog, so that dialog was answered for this interpreter at some
earlier time. The pair shows what answering it grants: **TCP and UDP,
inbound, any local port, on the Private and Public profiles, scoped to the
interpreter binary** -- not to port 5353, and not to the script. Any other
Python on the machine gets its own prompt; the rules for a second interpreter
(`...\.platformio\python3\python.exe`) sit beside them.

Windows' own mDNS rule does **not** cover it. `mDNS (UDP-In)` is enabled for
Domain, Private and Public, but it is scoped to
`%SystemRoot%\system32\svchost.exe`, service `dnscache`. Edge and WebView2
carry their own. A Python process binding 5353 is covered by none of them.

**Not tested:** whether *declining* the prompt silences the browse outright or
only part of it. That matters, because a declined prompt would produce exactly
the ambiguous `nothing_answered` that `mdns.services_heard` exists to tell
apart -- on a machine that is on the right segment. Testing it means disabling
the two rules above and re-running, which was not done.
