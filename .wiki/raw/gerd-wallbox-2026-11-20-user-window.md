# gerd's wallbox, 2026-11-20 evening: the user-defined mode's time window

Raw note, frozen at ingest. The same tunnel and consent as `raw/gerd-wallbox-2026-11-20.md`, the owner's
integration still disabled, one client per path. The inverter at unit 1 on its LAN cable, the AC22E-01 over
TLS, read every 5 s by `tmp/gerd-wallbox-2026-11-20/watch_window.py` (read only). Register numbers. Times
CET. No address or serial is in this note.

## The app's screen

*Benutzerdefiniertes Laden* shows a start and an end time (*Start*, *Ende*, each with a day, *Heute*), a
24-hour dial with the two handles, and *Strom/Leistung* (14 A shown as 9,66 kW). The maintainer reports
that the dial moves in steps of no less than **10 minutes**, and that the end could be set no less than
**one hour after the start**. Set: start 16:30, end 17:30 today, 14 A.

## 16:25 the save

Before (16:23:59, `settings_diff.py` snapshot): mode 162, charging off (85), user current 16.0 A, the time
pair 33546-33549 at 2026-11-20 00:00 and 2026-11-21 00:00 UTC; the car *completed*, idle.

- **16:25:34**: word 170 (on), **mode 163**, **33545 = 140 (14.0 A)**, and **33546/33547 = 2026-11-20 16:30,
  33548/33549 = 2026-11-20 17:30** -- u32 pairs, low word first, the local times written as if UTC, as
  scheduled charging's departure is. So **33546-33549 are the user-defined mode's window**, and the
  midnights a day apart read on every earlier day are a whole day's window. 33542-33544 (scheduled
  charging's target and departure) were left as 162 had them.
- 16:25:39: 21203 = 14.0 A, status **5 (suspended by the vehicle)**, 0 A: the inverter offered the user
  current at once, before the window's start.
- 16:25:50 21203 8.8 A; **16:25:55 status 3 (charging)**, 7.2-7.6 A, 4.9 kW; 16:26:01 11.7 A offered, the car
  10.6-11.2 A; **16:26:11 21203 = 14.0 A, the car 12.8-13.6 A, 8.8 kW**. The car charging **4 minutes 5 s
  before the window's start** (16:30).
- Nothing in the block or the car changed at 16:30 (read to 16:31:10). So the window's start did not hold
  the charge back: the save's charging-on started it at once.

## 16:43 test 9 begins beside the watch: the block through the WiNet-S every 10 s

`tmp/gerd-wallbox-2026-11-20/winet_block_hour.py` (read only): holding 33538-33550 at unit 1 through the
WiNet-S (port 502), every 10 s for an hour, one session, the wallbox not read on that path. The watch on the
inverter's cable and the wallbox's TLS port runs beside it, a different path each.

- 16:43:04 first read, 248 ms: `[85, 161, 170, 163, 19, 29188, 27392, 140, 30088, 27392, 33688, 27392, 85]`,
  the same block the cable reads. 16:43:14 227 ms.

## 17:30 the window's end stops the charge, and the window moves to the next day

The watch (`watch_window.py`, every 5 s, 16:25-17:36), the car at 12.9-13.7 A, 8.9 kW from 16:26 to 17:30:01.

- 17:30:01: charging, 8889 W, window 2026-11-20 16:30..17:30.
- **17:30:07: status 6 (*completed*), 0 A, 21203 0; and 33546-33549 now read 2026-11-21 16:30..17:30** -- the
  inverter moved the window one day on as it closed it. The word still 170.
- 17:30:12: 21203 back at 14.0 A, the car at 0 A. **17:30:17: the word 85 (off)**, about 10-16 s after the
  car stopped, as with every other stop today.
- From then to 17:36: off, *completed*, 0 A, 21203 14.0 A, mode 163, user current 14.0 A.
- So the user-defined window is a **daily** window: its end ends the session and switches charging off;
  its start did not hold back a charge switched on by the save (16:25). Whether the next day's start
  (2026-11-21 16:30) switches charging on by itself is not known; the maintainer plans to change the mode
  at 20:00 anyway.

## 17:43 test 9 ends: an hour through the WiNet-S, nothing lost

- **360 reads answered, 0 lost**, one session for the hour, 10 s apart, beside the watch on the cable and
  the wallbox's TLS port. Round trip: median 350 ms, 95th percentile 610 ms, the slowest 2688 ms.
- The block changed twice, at the same seconds as the cable saw: 17:30:06 the window to 2026-11-21, 17:30:17
  the word 85. No stale read-back on this path today.
- Left at 17:43: mode 163, user current 14.0 A, window 2026-11-21 16:30..17:30, charging **off**, the car
  *completed* at 0 A. The maintainer plans test 4 (a mode change from the app while charging) at 20:00.
