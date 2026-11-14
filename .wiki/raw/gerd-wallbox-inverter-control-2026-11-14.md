# gerd's wallbox, controlled through the inverter, 2026-11-14

On site at gerd's (the maintainer in the house's LAN, no VPN), with the owner's consent to any test
while charging. The owner's Home Assistant was stopped. The AC22E-01 (stand-in `anon-41346964423`)
hangs off the SH8.0RT (stand-in `anon-00267885816`), whose EMS manages it. Read and written from a
terminal: the wallbox over TLS 516, unit 248; the inverter at unit 1 over its LAN cable or through
the WiNet-S (said at each test). The car: three phase, 11 kW, takes at most 16 A. The installation
allows 22 kW (32 A, the wallbox's rating). No serial, no address. Times are CET (UTC+1).

Register numbers are protocol (wire) addresses in this note, as they were written: the inverter's
block is **wire 33539-33549**, the wallbox's documented registers are one higher than their wire
address (holding 21203 is wire 21202). The inverter block's meanings are from
`cross-reference-wallbox-control-2026-11-13.md` (the ioBroker thread), confirmed or added to here.

| Wire | Meaning (as measured here) | Values seen |
| --- | --- | --- |
| 33539 | charging on/off | 170 (0xAA) on, 85 (0x55) off |
| 33540 | charging mode | 160 fast, 161 PV surplus, 163 user defined (162 quantity/time not seen) |
| 33544 | user-defined current, 0.1 A | 60 to 330 written; 160, 100 held |
| 33549 | surplus from the grid | 85 no (not changed in these tests) |

## Before anything was written

- 10:32, dry run of `sungrow_wallbox_capability_test.py`: holding 21211 (enable) 0, status
  *disabled*, 21203 0, no car. iSolarCloud showed "EV Charger is deactivated". A power cut of the
  wallbox for 30 s changed nothing (21211 still 0).
- The owner switched the charger off and on in the app: **21211 read 1**, status *standby*: the
  app's enable is holding 21211.
- 21212 (start/stop) read 1 in standby. The owner pressed Start in the app: **21212 read 0**, the car
  charged at 16.0 A, 21203 read 316. So the app's Start/Stop is 21212, 0 = start.
- At 316 the car drew 16.0 A: 0.01 A per count would offer 3.16 A, so 21203 is not 0.01 A per count.

## Writes to the wallbox's own 21203 (10:53 and 11:0x): ignored

Written in breach of `plans/wallbox_recovery_and_retest.md` ("no further wallbox write"); only 21203,
nothing under 60, no 21211 and no 21212.

- Capability test base run (`--leave`): wrote 60; the same session read 0, a fresh one 316. Exit 3,
  the readback mismatch ended the step before any behaviour was watched. Restored 316, read back 316.
- Hand probe, one session: wrote 60. 21203 read **160 for about 6 s**, then 316/317 again; the car
  stayed at 15.3 / 15.6 / 16.1 A throughout (a dip of 0.4 A while 160 was read). Wrote 316 back: 160
  for about 5 s again, then 317. A fresh session 10 s later read 202.
- Read only afterwards, 60 s: 21203 at 266 for 20 s, then climbing in steps of about 7 every 1.75 s
  to 317, with the car at 16 A throughout. Something other than the test writes 21203 continuously:
  the inverter (below).

## The inverter's block, read only, while the owner used the app (12:39-13:17)

Reader: inverter over the cable, wallbox over TLS, every 5 s.

| Time | Owner in the app | 33539 | 33540 | 33544 | Wallbox 21203 | Status | Car |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12:39 | (fast charge, charging) | 170 | 160 | 160 | 302, drifting | charging | 16 A, 10.8 kW |
| 12:52:38 | Stop | 170 → 85 (12:52:49) | 160 | 160 | 0 | completed | 0 |
| 12:53:38 | PV surplus, saved | 85 | **161** | 160 | 0 | completed | 0 |
| 12:54:09 | Start | **170**, back to 85 at 12:54:20 | 161 | 160 | 60, then 0 | completed | 0 |
| 12:58:57 | Start again | 170, back to 85 at 12:59:09 | 161 | 160 | | completed | 0 |
| 12:59:36 | fast charge | 85 | 160 | 160 | 0 | completed | 0 |
| 13:00:05 | Start | 170 | 160 | 160 | ramps 73 → 214 in 55 s, then holds | **suspended by the vehicle** | 0 |
| 13:14:49 | replugged the car | 85 → 170 (13:14:54) | 160 | 160 | 60, then ramps | charging from 13:15:00 | follows the ramp |
| 13:17:05 | user defined, 10 A, saved | 170 | **163** | **100** | **100 at once** | charging | 9.1 / 9.3 / 9.6 A, 6.4 kW |

- **In PV surplus the start was dropped after about 10 s** with 60 (6 A) offered: PV 1.74 kW, house
  0.28 kW, grid about 0, battery charging 1.3 kW at 1.5 % in its window (input 13023), i.e. at its
  minimum SoC. 6 A on three phases needs about 4.1 kW.
- **After the stop the car went to sleep**: a Start 7 minutes later gave *suspended by the vehicle*
  with up to 21.4 A offered. The app's reason screen listed: battery temperature / SoC at its upper
  limit / insulation fault; scheduled charging, user interruption or the vehicle asleep; failed
  handshake / unstable voltage. A replug woke it.
- **The ramp, after the replug**: the inverter raises 21203 by about 1.4 A every 5 s from 6.0 A, and
  the car follows one step behind: 7.3 A offered, 6.1-6.5 A drawn; 9.5 / 7.9-8.3; 12.4 / 10.5-11.1;
  15.2 / 13.8-14.7; 17.4 / 15.1-16.0 (the car's maximum). **This settles 21203 at 0.1 A per count by
  behaviour.** In fast charge the inverter drives 21203 on towards the rating (28-32 A), well past
  the car's 16 A.
- Input 21314 (start mode) read 1 idle and **3 while a session runs** (from the replug); input 21268
  (remote control status) read 1 throughout.

## Phase B: the user current written over Modbus (13:18, cable, mode user defined set in the app)

| Time | Write | 33544 | 21203 | Car |
| --- | --- | --- | --- | --- |
| +0 s | 33544 = 80, answered | 80 | 100 → **80 at +6 s** | 7.2 / 7.3 / 7.6 A, 5.0 kW |
| +63 s | 33544 = 120, answered | 120 | 80 → 108 (+13 s) → **120 (+22 s)** | 10.9 / 11.1 / 11.6 A, 7.7 kW |
| +131 s | 33544 = 100 (restore), read back 100 | 100 | 100 | 9.2 / 9.3 / 9.7 A |

A lower current applies at once; a higher one is ramped. The car draws about 0.5 A under the
setting.

**Earlier, at 12:2x, with the mode at fast charge (160)**, the same kind of write (33544 = 100, over
the cable) was refused with exception 0x04, and so was writing back the value it already held (160),
37 times. **33544 accepts a write only while 33540 is 163.**

## Test 1: the mode written over Modbus (13:37, cable)

| Time | Write | 33539 | 21203 | Car |
| --- | --- | --- | --- | --- |
| 13:37:09 | 33540 = 163 (33544 held 100) | 170 | 285 → **100 at +10 s** | 16 A → 9.1-9.7 A at +13 s |
| 13:38:08 | 33540 = 160 | **85**, 170, 85 | 100 → 0 | **0, completed** at +7 s |

Restored 33540 = 160, read back. **Leaving user defined for fast charge over Modbus ended the
session**; the house was not as before (charging) until test 2.

## Test 2: start over Modbus (13:40, cable)

Wrote 33539 = 170 with the session ended (completed) for 2.5 minutes: +3 s *suspended by the charge
point*, 21203 74; **+9 s charging**, 2.4 A, ramping; +41 s 16 A, 10.6 kW. No replug needed.

## Test 3: the user current's range (13:42, cable)

Mode 163 written first (car 16 → 9.2-9.7 A at +13 s, 21203 100).

| Write | Answer | Car |
| --- | --- | --- |
| 33544 = 50 (5 A) | **refused, exception 0x04** | unchanged, 9.2-9.7 A |
| 33544 = 60 (6 A) | answered | 5.7 / 5.7 / 5.9 A, 3.9 kW, at +6 s |
| 33544 = 320 (32 A) | answered | ramped 60 → 88 → 117 (about 2.9 A every 10 s); 10.8-11.4 A |
| 33544 = 330 (33 A) | answered | ramp went on to 204; car at its 16 A |

Restored 33544 = 100, 33540 = 160, read back: the session ended again (completed at +8 s, 33539 85).
The start written next was not sent: the cable timed out (the owner's own Modbus polling was running
on it at the time, a second client).

## Back to 16 A, through the WiNet-S (13:47)

The owner asked for 16 A at the end. 33544 cannot be written in fast charge, so: 33540 = 163 →
**33539 went 85 → 170 by itself** and 21203 to 60, the car charging from +7 s; 33544 = 160; 33540 =
160 → 33539 85, completed; 33539 = 170 → +4 s *suspended by the charge point*, +8 s *suspended by
the vehicle*, **+15 s charging**, 16 A at +47 s. The owner's app showed 10.6 kW. **The WiNet-S takes
these writes as the cable does.**

## Test 4: stop and start over Modbus while charging (13:50, WiNet-S)

| Time | Write | 33539 read | Status | Car |
| --- | --- | --- | --- | --- |
| 13:50:23 | 33539 = 85 | 85, then 170 for 10 s, then 85 | charging → **completed at +4 s** | **0 within 1 s** |
| 13:50:57 | 33539 = 170 (34 s later) | 170 | +4 s suspended by the charge point, **+7 s charging** | ramps to 16 A in 40 s |

The 170 read back after the stop write is through the WiNet-S (its readback is not evidence); the
car stopped regardless.

## Test 5: PV surplus with surplus from the grid allowed (13:53, WiNet-S)

| Time | Write | 33539 | 21203 | Status | Car |
| --- | --- | --- | --- | --- | --- |
| 13:53:56 | 33549 = 170 (in fast charge), answered | 170 | 295 | charging | 16 A, unchanged |
| 13:54:10 | 33540 = 161 | **85** | 295 | suspended by the charge point | **0** |
| 13:54:13 | | 170 | 60 | completed | 0 |
| 13:54:23 | | 85 | 0 | completed | 0, for the 2 minutes after |
| 13:56:13 | 33549 = 85, 33540 = 160 | 85 | 0 | completed | 0 |
| 13:56:38 | 33539 = 170 | 170 | 67 → ramps | **charging at +4 s** | 16 A at +39 s |

Sun at the time: about 1.7 kW PV (12:55 reading), battery at its minimum SoC. **Switching to PV
surplus ended the session at once**, and with "surplus from the grid" set the inverter offered 6 A
once (13:54:13) and then switched charging off, as without it at 12:54. What 33549 = 170 does is
not established: it did not keep a minimum charge going here. Left as found: fast charge, 33549 85,
16 A user current, charging.

## Wire 33545-33548: two times, read only

The four words between the user current and the grid flag read, as two 32-bit values with the
low word first, as Unix times:

| When read | Words 33545, 33546 / 33547, 33548 | As UTC |
| --- | --- | --- |
| until about 13:17 | 57584, 27181 / 57584, 27181 | 2026-06-13 23:00 / the same |
| from about 13:25, after the owner saved settings in the app | 42112, 27383 / 62976, 27384 | 2026-11-14 00:00 / 2026-11-15 00:00 |

A start and an end, one day apart, set when the app saved; likely the window of the quantity-and-
time mode (162), not tried. 2026-06-13 23:00 UTC is local midnight in summer time; the newer pair
is midnight UTC. Not written.

## What this settles

1. On a wallbox the inverter manages, the inverter's block is the control; the wallbox's own 21203 is
   driven by the inverter and a write to it is overwritten within seconds.
2. 33539 starts and stops a session; 33540 sets the mode; 33544 the current in user defined mode,
   0.1 A per count, 6 A the floor (5 A refused), not capped by the inverter at the wallbox's rating.
3. Changing 33540 has side effects: to 163 switches charging on; to 160 from 163, and to 161 from
   160, end the session. A controller that changes the mode writes 33539 = 170 after it, if a
   charge is wanted.
4. 21203 is 0.1 A per count (behaviour); the app's enable is 21211 and its Start/Stop 21212.
