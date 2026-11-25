---
type: entity
title: Installation gerd
tags: [installation, gerd]
created: '2026-10-29'
---

# Installation gerd

An [SH8.0RT-V112](device-sh-rt.md) on [P022](firmware-sapphire-h-b001-v000-p022.md) with an
[SBR096](device-sbr-battery.md) and an AC22E-01 [wallbox](device-wallbox.md). The owner reports the
wiring: a LAN cable into the inverter, the WiNet-S on WLAN, and the wallbox on a LAN cable of its own.
The wallbox answers at unit 3 through the dongle and at unit 248 at its own address over TLS.
The only wallbox measured. [Register 32998](register-32998.md) capped a forced charge over the cable
and through the dongle; a run through the dongle while the house's Home Assistant polled lost the
dongle mid-restore, and the cable closed every session for minutes
([the run](../sources/gerd-import-limit-2026-11-08-summary.md)).
**The inverter manages the wallbox**: its charging, mode and user-defined current are written at
the inverter, and the wallbox's own current setting is the inverter's to drive
([the session](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md)). The car on it
draws at most 16 A on three phases; the installation allows 22 kW (32 A).

**The night of 2026-11-16/17**: the managed capability test's first run passed, a mode change to or
from user defined ends a session, 21203 is the user current in that mode and the inverter's offer
in fast mode, and the car suspended its own charge for hours at about 89 %, then reached 100 % by the
morning, reporting its Internet connection not established
([the night](../sources/gerd-wallbox-night-2026-11-16-summary.md),
[the morning](../sources/gerd-car-morning-2026-11-17-summary.md),
[why a managed wallbox stops charging](../queries/why-does-a-managed-wallbox-stop-charging.md)).

**The afternoon of 2026-11-17**: the EV charger controls from Home Assistant with a car charging, two mode
changes that did not end the session, four load-driven cutbacks with nothing written, and the managed
test's second pass with a restore that held
([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)).

**The evening of 2026-11-20**, no car: the wallbox entry names the inverter entry on the cable as the one
that manages it, and that entry gets the EV charger controls; an inverter entry through the WiNet-S gives
the wallbox up to its own entry and takes it back when that entry is deleted
([the pairing](../sources/gerd-wallbox-2026-11-20-pairing-summary.md)). The managed test from Home
Assistant is left to run with leave and a car charging.

**2026-11-21, the diagnosis in auto repeat on his own Home Assistant**: ten runs, 37/55 checks passed and
none failed. 13052 held 10000 W, above the 8000 W this model accepts, so the first run could not put it
back (exit 5); it was set to 8000 W by hand. Forced discharge, the export limit, the charging start
threshold and the charge ceiling were confirmed
([the day](../sources/gerd-auto-repeat-2026-11-21-summary.md)).
In the evening the day's three fixes went in over SSH (a local build, not a release), and one run on them
confirmed the discharge window and the discharging start threshold; the restart permission is left off
([the evening](../sources/gerd-t076-2026-11-21-summary.md)).

**2026-11-22, a night window with his Home Assistant's entries disabled**: the forced startup (13017)
did as told on P022, and a watched restart showed one start is enough -- the boot waits ~4.5 min in
Standby at night, which the engine had answered with re-sends
([the night](../sources/gerd-forced-startup-and-restart-2026-11-22-summary.md)).

**2026-11-25**: his Home Assistant went to device-scoped ids, the Energy dashboard with it
([the switch](../sources/gerd-entity-id-switch-2026-11-25-summary.md)).

## Diagnoses

- [The wallbox beside Sungrow's portal](../sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md), 2026-10-30

- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, second reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, second reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md)
- [AC22E-01 wallbox, gerd, TLS](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md), 2026-11-03, while a car charged
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, fourth reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-4-summary.md), 2026-11-22, from his Home Assistant, with a day and a half of plausibility checks
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md), 2026-11-03, the wallbox charging
- [The wallbox through a charging session](../sources/gerd-wallbox-charging-session-2026-11-03-summary.md), 2026-11-03
- [The battery level against the pack's own SoC](../sources/gerd-battery-level-2026-11-14-summary.md), 2026-11-14: max SoC now reads 100 %, 90 % in the diagnoses until 2026-11-03
- [AC22E-01 wallbox, gerd, TLS, while charging](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md), 2026-11-03
- [The TLS certificate of the WiNet-S and the wallbox](../sources/gerd-tls-certificate-2026-11-06-summary.md), 2026-11-06, one certificate
- [The wallbox capability test's dry run](../sources/gerd-wallbox-dry-run-2026-11-06-summary.md), 2026-11-06, no car
- [The wallbox capability test's first writing run](../sources/gerd-wallbox-capability-test-2026-11-13-summary.md), 2026-11-13, left the wallbox disabled
- [What the devices advertise over mDNS, and their web pages](../sources/gerd-mdns-2026-11-11-summary.md), 2026-11-11
- [The wallbox controlled through the inverter](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md), 2026-11-14, a car charging, on site
- [The EV charger controls from Home Assistant, and the managed test again](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md), 2026-11-17, a car charging, over VPN
- [The wallbox entry paired with the inverter entry](../sources/gerd-wallbox-2026-11-20-pairing-summary.md), 2026-11-20 evening, no car, over VPN
