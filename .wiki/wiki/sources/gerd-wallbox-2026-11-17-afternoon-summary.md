---
type: source
title: gerd-wallbox-2026-11-17-afternoon.md
source_path: raw/gerd-wallbox-2026-11-17-afternoon.md
ingested: '2026-11-17'
created: '2026-11-17'
tags:
  - wallbox
  - gerd
  - ems
  - home-assistant
  - capability-test
---

# gerd's wallbox, the afternoon of 2026-11-17

A VPN afternoon at [gerd](../entities/installation-gerd.md)'s with a three-phase car charging, 80 % to 92 %, on
the managed AC22E-01. The EV charger controls were written from the dev Home Assistant, and the managed
capability test was run from the terminal on this branch's library. Source: `raw/gerd-wallbox-2026-11-17-afternoon.md`.
The house afterwards was the same as before: charging on, fast, 16.0 A, the car charging.

| Fact | Evidence |
| --- | --- |
| **A mode change while charging did not end the session**, in either direction (fast to user defined at 14:39, user defined to fast at 14:50). The session energy kept counting through both | Home Assistant's select, recorder history of the session energy |
| On the night of 2026-11-16/17 the same changes ended the session. Today's house differed: battery 2.8 % rather than at its 0.5 % minimum, and about 0.3 kW of PV rather than none | [the night](gerd-wallbox-night-2026-11-16-summary.md) |
| *Wallbox user-defined current* in fast mode is refused by Home Assistant before anything is written (`ev_charger_user_current_mode`) | the number, 14:37 |
| In user-defined mode the car follows a lower current within 10 s (16 to 8 A) and a higher one with the 1.4 A / 5 s ramp (8 to 16 A in about 30 s) | the number, 14:41 and 14:45 |
| **21203 lags the user current by 4-5 minutes** in user-defined mode (3 min 40 s to 8.0 A, 4 min 43 s back to 16.0 A). It is not the user current at every moment | the wallbox sensor, every 10 s |
| *Wallbox charge* off: `completed` at 0 A within 4 s. On after 54 s: charging within 10 s, full power after about 40 s | the switch, 14:52-14:53 |
| **Four cutbacks with nothing written** (15:08-15:16): the car dropped to 6-8 A and ramped back within one session. Each followed a house load spike (to 16.0 kW, one phase to about 5.9 kW), with the import limit at 20 kW | the wallbox sensors, inverter load and meter phase power |
| **The managed capability test passed again, and its restore held** (the settle-and-watch restore's first hardware run): 6/8/10 A followed within 10-14 s, 5 A refused (0x04), stop in 4 s, restart in 7 s. Fast, 16.0 A and charging on put back, and the car still charged 20 s after the run | terminal run 15:45-15:48, then the field tool |
| **From Home Assistant the managed test cannot run here**: the wallbox entry took the standalone path and wrote nothing. Its link to the inverter entry is made only when the wallbox answers behind a dongle, and gerd's inverter entry is on the LAN cable | *Diagnosis: start* at 15:41 |

## What it means

- A mode change *can* end a session, but does not always. What decides it is open; the battery at its minimum
  is the difference that stands out ([the query](../queries/why-does-a-managed-wallbox-stop-charging.md)).
  The mode select's open question, whether the charging-on it writes straight after the mode change is overridden by the
  inverter's delayed off, could not be provoked today.
- Judge a user-current change by the car, not by 21203.
- The cutbacks look like load management by the inverter. No register seen names it, so the cause is a guess.
- Two faults in the integration, fixed in the same change: the extended-test guard asked a wallbox entry for
  inverter questions its options do not have (`custom_components/sungrow_modbus/testimony.py`,
  `tests/test_testimony.py`), and a stale snapshot from a standalone run would have been put back through
  the managed wallbox's own registers (it matched the wallbox apart from 21203, the inverter's to drive, and
  was discarded by hand).
