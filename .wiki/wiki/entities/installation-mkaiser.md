---
type: entity
title: Installation mkaiser
tags: [installation, mkaiser]
created: '2026-10-29'
---

# Installation mkaiser

The maintainer's [SH10RT](device-sh-rt.md) on [P020](firmware-sapphire-h-b001-v000-p020.md) with a
third-party battery, on its own LAN port, with a [RAK WiFi module](device-rak-wifi-module.md) on the
same network ([discovery, 2026-11-15](../sources/mkaiser-network-discovery-2026-11-15-summary.md)). Its capability tests matched every readback written,
13074 writes times ten, and the forced-charging window raised charging to 4499 W (judged "could
not tell"), and moving the discharge windows away from now stopped a 722.5 W discharge to 0 W and
it came back ([the check](../sources/mkaiser-discharge-window-2026-11-04-summary.md)). A watched write of [register 32998](register-32998.md) held grid import at 2.00 kW under a
4500 W forced charge ([the run](../sources/mkaiser-import-limit-2026-11-07-summary.md)), and with PV capped import alone
([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)); the capability test's check
confirmed it, and with the PV isolator open the inverter first went to Standby
([the engine run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)); with the battery
held idle it did not cap the house's own load ([the load run](../sources/mkaiser-import-limit-load-2026-11-07-summary.md)), and with
PV above the load it left export alone ([the export run](../sources/mkaiser-import-limit-export-2026-11-08-summary.md)); with the
discharge limit below the load it did not draw on the battery past it ([the discharge run](../sources/mkaiser-import-limit-discharge-2026-11-08-summary.md)).
[Register 13017](register-13017.md)'s 0xAA woke it from low-SoC Standby and 0x55 sent it back; 13017
is left at 0x55 ([the forced startup run](../sources/mkaiser-forced-startup-2026-11-08-summary.md)).
The capability test engine's own forced startup mode had its **first run on hardware** here on
2026-11-16, from Home Assistant: left standby after 123 s, Running after 208 s, back in standby
16 s after 0x55, no finding, and the restore had nothing to put back -- within seconds of the
script's figures eight days earlier. The same evening, with 13017 off and nothing written, the
inverter took a fifteen-second running window by itself at 22:48
([the engine run](../sources/mkaiser-forced-startup-2026-11-16-summary.md)). Left at 0xAA the next
morning it held for **90 minutes**, through dawn, and ran 56 minutes in the dark before any PV, so
this inverter undoes neither by itself nor on PV
([the watch](../sources/mkaiser-forced-startup-left-on-2026-11-17-summary.md)). *Diagnosis: stop*
pressed 60 s into part B here put all seventeen touched settings back with zero mismatches and
started no restart, the first stop on hardware
([the stop](../sources/mkaiser-stop-mid-run-2026-11-17-summary.md)). A 48-minute forced charge
from the grid the same morning, run from the `doc/scenes.md` scenes, took the pack from 0.0 % to
25.5 % at a steady 4501 W, showed its state of charge advancing in ~1.1 point steps, and had the
companion automation render `state_attr(..., 'max')` as 7420 W -- a ceiling that read 7148 W with
the pack empty and 7318 W a minute later, because it falls back to what the BMS will take at that
moment ([the charge](../sources/mkaiser-forced-charge-2026-11-17-summary.md)).
The forced-charging window took charging from -633 W to 4499 W and back, did as it was told
([third reading](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)).
A night of *Extended test (auto repeat)*, 19 runs, did it seven times more, held the site import
limit seven times, sat out five hours of low-SoC Standby without writing, and in the morning
established the forced discharge and the charge ceiling; restarts took 367 s after dark and 186 s
in daylight ([fourth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3-summary.md)). The development instance's run
repeated the ceiling ([fifth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4-summary.md)).
A short auto-repeat collection on 2026-11-15 (three runs, 0.1.0a40) passed the forced-charging
window and brought the house's first [plausibility](../concepts/capability-test.md) block (power
balance, tracker V×I, both meter checks matched; the battery idle, so its V×I could not tell), and
stored five battery-power settings above their maximum, the bound unenforced
([sixth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5-summary.md)).
The production Home Assistant polls it **through a modbus-proxy on its own machine**, so the
house answers as one inverter at two addresses, one serial and one route note at both; the
search from the dev container found both and could name neither as the proxy
([the proxy reading](../sources/mkaiser-modbus-proxy-2026-11-16-summary.md)), and an entry
pointed at the proxy cannot measure its route
([open](../queries/does-a-modbus-proxy-carry-6100.md)). Its own LAN port **takes a second TCP
session from the address already polling it**: with the dev container's Home Assistant polling it
without a break, 12 of 12 connects were accepted and two full sweeps from that same container
found it ([the run](../sources/mkaiser-second-session-2026-11-17-summary.md)), so contention does
not explain why the production instance's sweep missed it
([open](../queries/why-did-the-search-miss-mkaisers-inverter.md)). From the Windows host, which is on the
house's segment, the cache does separate them: the inverter's own LAN port carries Sungrow's
`AC:19:9F` and the proxy a locally administered prefix
([the prefixes](../sources/mkaiser-mac-prefixes-2026-11-16-summary.md),
[how](../concepts/telling-a-proxy-from-the-inverter.md)). From the same host a 15-second
multicast browse heard 44 service instances, four of them `_http._tcp`, and **not one Sungrow
record** -- the house's inverter is on its own LAN port with no dongle, so this is the measured
form of the claim that such a port advertises nothing
([the browse](../sources/mkaiser-mdns-2026-11-16-summary.md),
[open](../queries/does-a-winet-s-advertise-over-mdns.md)). Four more browses that afternoon,
across three Windows firewall states, found no Sungrow record either, and showed what a declined
firewall prompt costs: 37 instances against 44, with `services_heard` still non-zero
([the firewall runs](../sources/mkaiser-mdns-firewall-2026-11-16-summary.md)). They also caught
the [RAK WiFi module](device-rak-wifi-module.md) advertising under `_rak47x._tcp`, which two
earlier readings had recorded as silent
([a browse is a floor](../concepts/mdns-browse-is-a-floor.md)).
Its [energy history](../concepts/energy-history.md) reads implausible 2024 slots.

## Diagnoses

- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, second reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, third reading](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fourth reading: a night of auto repeat](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fifth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, sixth reading: auto repeat with plausibility](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5-summary.md)
