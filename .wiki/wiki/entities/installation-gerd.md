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

## Diagnoses

- [The wallbox beside Sungrow's portal](../sources/gerd-wallbox-isolarcloud-2026-10-30-summary.md), 2026-10-30

- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, second reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, second reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-2-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-summary.md)
- [AC22E-01 wallbox, gerd, TLS](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-summary.md)
- [SH8.0RT-V112, B001.V000.P022, gerd, the inverter's own LAN port, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-3-summary.md), 2026-11-03, while a car charged
- [SH8.0RT-V112, B001.V000.P022, gerd, a WiNet-S on WiFi, third reading](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-wallbox-winet-wlan-3-summary.md), 2026-11-03, the wallbox charging
- [The wallbox through a charging session](../sources/gerd-wallbox-charging-session-2026-11-03-summary.md), 2026-11-03
- [The battery level against the pack's own SoC](../sources/gerd-battery-level-2026-11-14-summary.md), 2026-11-14: max SoC now reads 100 %, 90 % in the diagnoses until 2026-11-03
- [AC22E-01 wallbox, gerd, TLS, while charging](../sources/ac22e01-gerd-anon-41346964423-wallbox-tls-2-summary.md), 2026-11-03
- [The TLS certificate of the WiNet-S and the wallbox](../sources/gerd-tls-certificate-2026-11-06-summary.md), 2026-11-06, one certificate
- [The wallbox capability test's dry run](../sources/gerd-wallbox-dry-run-2026-11-06-summary.md), 2026-11-06, no car
- [What the devices advertise over mDNS, and their web pages](../sources/gerd-mdns-2026-11-11-summary.md), 2026-11-11
- [The wallbox controlled through the inverter](../sources/gerd-wallbox-inverter-control-2026-11-14-summary.md), 2026-11-14, a car charging, on site
