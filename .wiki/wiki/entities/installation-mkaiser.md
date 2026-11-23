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
**All seven scenes of `doc/scenes.md` have now run here** (2026-11-19): both forced scenes move
what they are told to within two watts, bypass holds the battery at 0 W and sends the PV it was
absorbing to the grid, and the two export scenes and both automations work -- with the lesson that
a scene is not atomic and this link drops, so three of seven presses needed a second
([the scenes](../sources/mkaiser-scenes-2026-11-19-summary.md)). In self-consumption below about
10 % this inverter charges the pack **from the grid** rather than covering the load with it.
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
([open](../queries/does-a-modbus-proxy-carry-6100.md)). Since 2026-11-21 the production instance
runs the integration (0.1.0a46, new ids) **beside the YAML package, both through that proxy**, with
neither losing reads; its extended test passed 21 checks with every readback matched, and the import
limit held with PV above the load ([the production install](../sources/mkaiser-production-install-2026-11-21-summary.md)).
Its own LAN port **takes a second TCP
session from the address already polling it**: with the dev container's Home Assistant polling it
without a break, 12 of 12 connects were accepted and two full sweeps from that same container
found it ([the run](../sources/mkaiser-second-session-2026-11-17-summary.md)), so contention does
not explain why the production instance's sweep missed it; on 2026-11-20 the same search from the
production machine, proxy running, found it and the proxy as one inverter, so the miss does not
reproduce ([the sweep](../sources/mkaiser-production-sweep-2026-11-20-summary.md),
[the query](../queries/why-did-the-search-miss-mkaisers-inverter.md)). From the Windows host, which is on the
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
A night and a day of observing between runs brought the readings checks their **first failure on
hardware**, and the inverter is not at fault: `daily counters reset at midnight` recorded
`daily_pv_generation fell from 4.4 to 0 at 23:04`, which is 00:04 on the inverter's own clock, the
development instance being on UTC while the inverter keeps German local time. The counter reset on
time and to zero; the check judged the fall by Home Assistant's midnight, not the inverter's
([the midnight reset](../sources/mkaiser-midnight-reset-2026-11-17-summary.md)). It was the house's
one failing row, and **the next night repeated it to the minute**: 1.6 to 0 at 00:03 on the
inverter's clock, against 4.4 to 0 at 00:04 the night before. So this inverter's daily counters
reset on time and to zero, measured twice
([the second night](../sources/mkaiser-midnight-reset-night-2-2026-11-18-summary.md)).
**The check judges on the inverter's clock since 2026-11-19**, and raising its revision drops
what it judged by the old one, so the row cleared itself here without the ledger being touched
([the capability test](../concepts/capability-test.md)). At the next midnight it **passed, and
answered what the first two nights could not**: eight daily counters fell to zero in the same
one-minute poll -- `pv_generation` 4.9, `imported_energy` 12, `exported_energy` 0.2,
`battery_charge` 1.8, `battery_discharge` 1.6, `exported_energy_from_pv` 0.2,
`battery_charge_from_pv` 1.5, `direct_energy_consumption` 3.2 -- with none left standing, at
00:09 by the inverter's clock against 23:09 by Home Assistant's. So **this inverter resets its
daily counters in one step**. The day before had put 12 kWh through the meter, which is what gave
the reset eight counters to lose where the earlier nights had only one
([eight in one poll](../sources/mkaiser-midnight-reset-answered-2026-11-20-summary.md)).
`lifetime battery counters contain each other` settled in the same stretch, 175 passes and no
failure, the first time anywhere, and its first field being read on that boot is what moved the
house's total from 54 checks to 55. It stood then at **37 of 55, none failing**: fewer than the
39 below, because the bound checks' own revision was raised on 2026-11-17 and six
`upper bound of ...` rows went back to waiting with it, each needing a charged battery
([eight in one poll](../sources/mkaiser-midnight-reset-answered-2026-11-20-summary.md)).
Beside it, the two checks that wait for **a day of polls** reached their minimum here, the first
time either has anywhere: over 1470 observations spanning 30 hours, `lifetime counters never fall`
passed on 1464 judged steps with none going backwards, and `running states` passed on four codes,
all in the decode table -- Standby 1013, Running 452, Stop 4, **Starting 1**, that last a reminder
that a one-minute cadence catches a transient state by luck. Together they take the house to
**39 of 54** ([the day of polls](../sources/mkaiser-day-of-polls-2026-11-18-summary.md)).
**The production instance's auto repeat finished the collection on 2026-11-23: 56 of 56 established,
0 failed**, 26 runs, five bounds not enforced, everything put back each time
([seventh reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6-summary.md)): the export limit held 1247.5 W for 1250 W, 13059 refused 51 %, and the
daily counters reset together at two more midnights.
Its [energy history](../concepts/energy-history.md) reads implausible 2024 slots.

## Diagnoses

- [SH10RT, B001.V000.P020, mkaiser, seventh reading: every check established](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-6-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, second reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, third reading](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fourth reading: a night of auto repeat](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-3-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, fifth reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-4-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, sixth reading: auto repeat with plausibility](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-5-summary.md)
