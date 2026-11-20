# gerd's wallbox, 2026-11-20 at 18:20: a window's start, and a mode change from the app while charging

Raw note, frozen at ingest. The same tunnel and consent as `raw/gerd-wallbox-2026-11-20.md`, the owner's
integration disabled, one client per path. The inverter at unit 1 on its LAN cable, the AC22E-01 over TLS, read
every 5 s by `tmp/gerd-wallbox-2026-11-20/watch_window.py` from 18:21:10 (read only). Register numbers. Times CET.
No address or serial is in this note.

## 18:22 saves with the mode already user defined

Before: mode 163, user current 14.0 A, window 2026-11-21 16:30..17:30, charging off (85), the car *completed*.
The first read at 18:21:20 timed out on the cable (8 s); every read after answered.

- 18:22:37: user current **8.0 A**, window **2026-11-20 18:30..20:00**; 18:22:53 the end 19:30; 18:23:04 the end
  20:00 again (the maintainer saving three times). **The word stayed 85 (off)**, the car *completed* at 0 A.
- So a save of *Benutzerdefiniertes Laden* that does not change the mode does **not** switch charging on; at
  16:25 the save that changed the mode (162 → 163) did. The app then shows *Ladevorgang abgeschlossen*, 0 kW,
  the plan "18:30 - 20:00, 8A/5,52kW", and a button *Ladevorgang beginnen*.
- Not pressed: the window opens at 18:30 with charging off, to see whether its start switches charging on.

## 18:28 the car unplugged; 18:30 the window's start switches charging on by itself

- 18:28:05 status 6 (*completed*); **18:28:11 status 1 (idle)**, 21203 14.0 A. At 18:31 the control-pilot voltage
  (21312) read **11.9 V**, the no-vehicle level: **the car was unplugged at about 18:28**, not by us. Who unplugged
  it was not known from here.
- 18:29:40-18:30:01: word 85, status 1, 21203 0.
- **18:30:06: the word 170 (on) with nothing written**, the window's start (18:30). 18:30:12: 21203 = **6.0 A**
  (not the 8.0 A user current), status 1, 0 A: no car to charge. Unchanged to 18:31:05.
- So **the window's start switches charging on by itself**, and the window's end (17:30, the earlier note)
  switches it off: the user-defined window is a daily on/off schedule, held by the inverter. A charge switched on
  by a mode change starts at once, inside the window or not (16:25).
- Test 4 (a mode change from the app while charging) could not run: no car.

## 18:39 the block put back as found at 13:55, and which words take a write in which mode

The maintainer asked for the morning's state (fast, charging on). The watch was stopped first (one client on
the cable). `tmp/gerd-wallbox-2026-11-20/restore_fast.py` and two short scripts, on the inverter's cable;
the block before them flushed to disk.

- Before (18:39:12): `[85, 161, 170, 163, 19, 29188, 27392, 80, 37288, 27392, 42688, 27392, 85]` -- on, 163,
  8.0 A, window 18:30..20:00, the scheduled words as mode 162 left them.
- In mode 163: 33545 = 160 (16.0 A) **taken**. Then, single writes (FC 6): 33546, 33547, 33548, 33549 (the
  window) and 33542, 33543, 33544 (scheduled target and departure) **all refused, exception 0x04**. 33541 = 160
  taken, 33540 = 0xAA taken.
- In mode 160: the window as one write of four words (FC 16, 33546-33549) **refused, 0x04**.
- 18:40:16 33541 = 163; **18:40:18 the window as one FC 16 write taken** (2026-11-20 00:00 .. 11-21 00:00 UTC, a
  whole day); 33541 = 160; 33540 = 0xAA.
- So the window takes a write only in mode 163, and as one four-word write: in 163 its single-word writes
  were refused at 18:39:13-16 (the FC 16 form in 163 was not tried word by word after). The user current takes
  a write only in 163 (2026-11-14), and the scheduled target took a single write in 162 (15:39) but not in 163.
- **18:40:23, a fresh session: `[85, 161, 170, 160, 19, 29188, 27392, 160, 36224, 27391, 57088, 27392, 85]`** --
  charging on, fast, 16.0 A, a whole day's window, grid purchase off: as at 13:55, but for 33542-33544 (1.9 kWh,
  2026-11-20 16:15), which mode 162 alone reads. The car unplugged (pilot 11.9 V at 18:31).
