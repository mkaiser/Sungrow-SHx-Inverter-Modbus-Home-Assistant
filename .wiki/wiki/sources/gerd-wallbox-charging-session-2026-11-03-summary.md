---
type: source
title: gerd-wallbox-charging-session-2026-11-03.md
source_path: raw/gerd-wallbox-charging-session-2026-11-03.md
ingested: '2026-11-03'
created: '2026-11-03'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - charging-session
  - tls
---

# gerd's wallbox through a charging session, 2026-11-03

Three hours of one TLS session at [gerd](../entities/installation-gerd.md)'s
[wallbox](../entities/device-wallbox.md), read every 30 s, from a car charging
at 10.7 kW to the moment it stopped. Source: `raw/gerd-wallbox-charging-session-2026-11-03.md`.
It answers the Todo question that a reading with no car could not.

- **Input 21313 falls to 0 when charging ends**: 456-458 up to the stop, 0 from
  94 s after the power fell, on the poll where the status reached 6. During
  the session it wandered 297-527 at constant power, so it is neither power
  nor current. Still unnamed.
- **The stop, in order:** power and currents to 0 and the control pilot from
  5.94 V to 8.97 V (state B), status 5 (suspended by the vehicle) with 21315
  at 1, then status 6 (completed) with 21315 back at 0. Status 5 had not been
  seen before.
- **Input 21310 keeps the session's energy** after the end (39814 Wh).
- **21308/21310 signedness is not settled**: the high words read 0 throughout
  and no value left 10634-10760 W.
- **Input 21267** rose one in about 5.4 s through the stop; the shape of an
  uptime counter, not of a write counter. The wiki said once in 10 s.
- **Start mode 21314 read 3 charging or not**, and input 21365 stayed between
  -71 and -63.
