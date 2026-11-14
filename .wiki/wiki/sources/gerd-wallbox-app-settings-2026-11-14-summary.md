---
type: source
title: gerd-wallbox-app-settings-2026-11-14.md
source_path: raw/gerd-wallbox-app-settings-2026-11-14.md
ingested: '2026-11-14'
created: '2026-11-14'
tags: [wallbox, ac22e-01, gerd, isolarcloud, settings]
---

# gerd's wallbox: the app's system parameters against the registers, 2026-11-14

`.wiki/raw/gerd-wallbox-app-settings-2026-11-14.md`: the maintainer changed each of the charger's
*Systemparameter* in iSolarCloud once and back, with no car charging; after each save the
[wallbox](../entities/device-wallbox.md) at [gerd](../entities/installation-gerd.md) was read
whole over TLS and the inverter's holding 33501-33600 over the cable, and diffed. Nothing was
written over Modbus. Register numbers here.

| Fact | Evidence |
| --- | --- |
| **Holding 21211 is *Ladegerät aktivieren***, 1 enabled, 0 disabled; input 21268 echoes it | disabled and enabled in the app, both moved both ways |
| **Input 21317 (charging status) reads 8 while the charger is disabled**, idle (1) again on enable | the same two saves |
| **Holding 21298 is Plug&Play** (a plugged-in car starts charging by itself), 1 on, 0 off; input 21362 echoes it | off and on in the app |
| **Holding 21299 is the offline current**, 0.1 A per count; input 21363 echoes it | 32 → 16 → 32 A in the app: 320 → 160 → 320 |
| **Holding 21313 is the power limit (*Leistungsgrenze*)**, 0.1 kW per count; the app shows it only while the charger is disabled | 22 → 11 → 22 kW: 220 → 110 → 220 |
| Input 21263 (maximum current) and input 21273 (nominal power) follow the limit | 320 → 160 (32 → 16 A), 22080 → 11040 W, and back |
| **The offline current does not follow the limit**: 32 A at an 11 kW limit, in the registers and the app alike | holding 21299 read 320 throughout |
| None of these is in the inverter's 33501-33600: they are the wallbox's own settings | the inverter's words never moved |
| Input 21364 drifts by itself (signed, about -62) | 65473-65476 over 20 minutes with nothing changed |

Not touched: *Datenlöschung* (data deletion), also shown while the charger is disabled.
Afterwards everything read as at the start.
