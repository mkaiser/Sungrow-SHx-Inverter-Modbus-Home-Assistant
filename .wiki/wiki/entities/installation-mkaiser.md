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
([open](../queries/does-a-modbus-proxy-carry-6100.md)). From the Windows host, which is on the
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
