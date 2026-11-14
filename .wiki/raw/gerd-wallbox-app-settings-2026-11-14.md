# gerd's AC22E-01: the app's system parameters against the registers, 2026-11-14 evening

The maintainer changed one setting at a time in the iSolarCloud app (*Einstellungen >
Geräteeinstellungen > Systemparameter* of the charger: *Ladegerät aktivieren*, *Plug&Play*,
*Offline-Ladestrom (A)*, range 6.0-32.0), saved, and said so; each time the wallbox was read whole
over TLS (unit 248, the diagnosis's bands) and the inverter's holding 33501-33600 over the cable,
and compared with the reading before. Read only from here; every change made in the app. Protocol
addresses in this note, as read; register numbers are one higher. The clock (holding 21224-21229)
and counters (input 21266 and the live block) move by themselves and are left out.

Starting point (19:36:53): the inverter in PV surplus, *Netzbezug* off, charging off; the wallbox
idle, no car charging. App: charger enabled, Plug&Play enabled, offline current 32.0 A.

| Time | Change in the app | Words that changed | Before → after |
| --- | --- | --- | --- |
| 19:39:35 | Offline-Ladestrom 32.0 → 16.0 A | holding 21298; input 21362 | 320 → 160; 320 → 160 |
| 19:40:50 | Offline-Ladestrom 16.0 → 32.0 A | holding 21298; input 21362 | 160 → 320; 160 → 320 (back to the start) |
| 19:41:58 | Plug&Play enabled → disabled | holding 21297; input 21361 (also input 21364 65474 → 65473, unexplained) | 1 → 0; 1 → 0 |
| 19:44:39 | Plug&Play disabled → enabled | holding 21297; input 21361 | 0 → 1; 0 → 1 (back to the start) |

Input 21364 read 65474, 65473, 65475 in three readings: it drifts by itself (signed, about -62),
so it is not the Plug&Play echo.
| 19:48:59 | Ladegerät aktivieren: enabled → **disabled** | holding 21210; input 21267; input 21316 (the charging status) | 1 → 0; 1 → 0; **1 (idle) → 8** |

With the charger disabled the app's page showed two more settings: *Leistungsgrenze* (power limit,
22 kW, "the charger adapts to a new limit and sets the offline current itself") and
*Datenlöschung* (data deletion, *Bitte auswählen*), the latter left alone.
| 19:53:21 | Leistungsgrenze 22 → **11 kW** (charger disabled) | holding 21312; input 21262 (the maximum current); input 21272 (the nominal power) | 220 → 110; 320 → 160; 22080 → 11040 |

At 11 kW the offline current (holding 21298, input 21362) still read **320 (32.0 A)**, above the
new 16 A maximum: the adjustment the app's text promises did not show in the registers.
| 19:56:06 | Leistungsgrenze 11 → 22 kW (charger disabled) | holding 21312; input 21262; input 21272 | 110 → 220; 160 → 320; 11040 → 22080 (back to the start) |

The app's offline current field showed 32 A throughout, as the registers did.
| 19:57:27 | Ladegerät aktivieren: disabled → enabled | holding 21210; input 21267; input 21316 | 0 → 1; 0 → 1; 8 → 1 (idle) |

19:58:05, against the starting point: only the clock (holding 21227-21228), input 21266 and 21364
differ. Everything the app touched is back as it was; the inverter's 33501-33600 never moved.

## What it shows (register numbers, one higher than above)

| Register | App setting | Values |
| --- | --- | --- |
| holding 21211 | Ladegerät aktivieren | 1 enabled, 0 disabled |
| input 21317 | (charging status) | **8 while the charger is disabled**, 1 idle again on enable |
| input 21268 | (enabled, echoed) | 1 enabled, 0 disabled |
| holding 21298 | Plug&Play: a plugged-in car starts charging by itself | 1 on, 0 off |
| input 21362 | (Plug&Play, echoed) | as holding 21298 |
| holding 21299 | Offline-Ladestrom | 0.1 A per count, 60-320 in the app |
| input 21363 | (offline current, echoed) | as holding 21299 |
| holding 21313 | Leistungsgrenze, shown only while the charger is disabled | 0.1 kW per count: 220 = 22 kW, 110 = 11 kW |
| input 21263 | (maximum current, follows the limit) | 0.1 A: 320 at 22 kW, 160 at 11 kW |
| input 21273 | (nominal power, follows the limit) | W: 22080 at 22 kW, 11040 at 11 kW |

None of them is in the inverter's holding 33501-33600: they are the wallbox's own. A setting the
app changed was read back within a minute or two, so each is the setting, not a cached copy.
