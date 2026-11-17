# gerd's wallbox, the night of 2026-11-16/17: managed test, same-value writes, mode changes, a car that stopped charging

Raw note, frozen at ingest. A VPN to the owner's site from 21:20 to 06:10 (CET), read only except where a write is
listed, with the owner's consent (gerd's, given for the evening) and the maintainer present. The inverter at unit 1
over its LAN cable (port 502), the AC22E-01 over TLS (516, unit 248); one client per path (the watch was stopped
before every write). Register numbers; the protocol address is one lower (33540 is written at 33539). The car is a
three-phase one that draws at most 16.2 A per phase. Times are CET. The owner's readings of the car's own app
are quoted where they were given. No address or serial is in this note.

Parts: the working notes as written through the night (the 15-minute entries repeat when nothing changed), then
the four test logs, second by second.

---

# Working notes

# gerd's, night of 2026-11-16/17: read-only watch while a car charges

Working notes (gitignored). To be ingested as a raw note + wiki source page afterwards.
Read only: no write to the inverter or the wallbox. Inverter LAN port (unit 1), wallbox over TLS
516 unit 248. Every 2 min a fresh session pair (`night_watch.py`), log `watch.jsonl` beside this file.
Register numbers below (protocol address one lower).

## 21:21 baseline

- Inverter EV block 33538-33550: `[85, 161, 170, 160, 0, 0, 0, 160, 42112, 27383, 62976, 27384, 85]`
  = charging **on** (0xAA), mode **160 fast**, user current 16.0 A, grid purchase 85 (0x55, off),
  33538 = 85, 33539 = 161 (as on 11-14).
- The two times 33546-33549 decode to **2026-11-14 00:00 UTC and 2026-11-15 00:00 UTC**: exact
  midnights, a day apart. Consistent with a quantity-and-time window's date pair, not a clock.
- House: PV 0, importing ~11.25 kW, load ~11.25 kW, battery 13023 = 0.5 (at its minimum), battery
  power 0.
- Wallbox: status charging, three phases 15.4 / 15.7 / 16.2 A, 10.62 kW, session 19.2 kWh;
  21204 = 0 (three phase), 21225 = 3, 21270 = 0, 21272 = 4140 (W: the 3-phase minimum, 6 A x 3 x 230).
- **21203 reads 26.6-26.7 A** while the inverter's user current is 16.0 A and the car draws ~16 A.
  On 11-14 it read 16.0 / 15.1 while charging. In fast mode the setting is not the user current:
  either the inverter writes something else into it in fast mode, or this is a (car/cable) cap-free
  value. To watch: does it move over the night?
- **Battery at its minimum and fast charge running for hours, not stopped** (19.2 kWh in the session).
  Against the open question "does the inverter stop the charge at the battery's minimum SoC":
  in fast mode at least, it does not (so far).

## Log

## 21:33 managed capability test, first run on hardware (--leave --start-stop)

Dry run 21:31 resolved, nothing written. Real run 21:33 (before the owner's "no start/stop now"
reached me): all five checks passed. User current 6/8/10 A followed (car 5.6 / 7.5 / 9.5 A after
7-10 s); 5 A refused with 0x04 (33544 = 50); stop seen after 4 s, charging again after 10 s.
Exit 0, report in device-diagnosis/20261116-203305-managed-wallbox-capability-test.json (gitignored).

**Afterwards, 28 s later and again at 21:34:35: charging OFF.** Inverter word 33540 = 85 (0x55),
mode fast, user 16.0 A, wallbox status `completed`, 0 A, 21203 = 0. The run had restored 0xAA and
read the car charging. The two time words 33546-33549 changed (now 18304/27386, 39168/27387 =
2026-11-14 .. -15 shifted to ...). Same picture as 2026-11-14: the inverter (or the car) ends the
session after a restart; battery 13023 = 0.5 (minimum), PV 0. Not written to since. No further
writes until the owner decides.

## 21:36 restart, by the owner's leave

The owner's VW app said "Ladevorgang abgeschlossen" at **47 %**, so the session was ended on the
charger side, not by the car's own limit (it was to charge to 100 %). One write of 33540 = 0xAA
(inverter, unit 1) at about 21:36 restarted it: charging on, 15.2/15.6/16.2 A, 10.57 kW, the
session counter back to 0. Owner: 47 % -> 100 %, ETA 4:40 (from 21:36, so about 2:15).
Finding: **a stop-then-start by the managed test ended in "completed" within ~30 s of the restore**,
as on 2026-11-14 (restart from the app, then off). With the battery at its minimum (13023 = 0.5)
and no PV. The restore word (0xAA) was read back as on and the car drew power; then the inverter's
word went to 0x55 by itself. A single "on" from a stopped, completed state held at least 2 min.
The time words 33546-33549 changed at the same moment (inverter rewrites them with the session).
Plan: owner wants only the critical tests at 80 % SoC, no start/stop before.

### 21:39 summary
One row since the restart (21:37:36): charging on, fast, user 16.0 A, grid purchase off; car 15.2/15.6/16.1 A,
10.58 kW; session 278 Wh since 21:36 (counter restarted); 21203 = 27.5 A (inverter user current 16.0 A,
unchanged discrepancy); battery 13023 = 0.5, PV 0, load 11.07 kW; phases 21204 0, 21225 3, 21270 0,
21272 4140. No ERR rows. Watch alive, tunnel handshake 17 s old. Nothing new.

### 21:54 summary
21:39-21:53, 7 rows, no ERR. Charging steady: 15.3-15.4/15.6-15.7/16.1 A, 10.62-10.68 kW. Session 3076 Wh at
21:53 (since the 21:36 restart; 10.7 kW mean). Block unchanged: on (0xAA), fast, user 16.0 A, grid purchase off,
time words 18304/27386, 39168/27387 constant. 21203 wanders 26.1-27.6 A (user current 16.0 A): not the
user current in fast mode, no trend. Battery 13023 = 0.5, PV 0, load 11.1-11.4 kW. Phases 21204 0, 21225 3,
21270 0, 21272 4140, constant. Tunnel handshake 41 s old, watch alive, watchdog re-armed 21:40. Nothing new.

### 22:09 summary
21:55-22:06, 6 rows, no ERR, watch alive, handshake 4 s. Session 5410 Wh at 22:06 (10.3 mean since 21:53,
slightly below 10.7 because of the two dips).
**NEW: two transient current dips in fast mode, block unchanged** (on, fast, 16.0 A, time words constant):
- 21:57:50: 5.7/5.8/6.0 A, 3.96 kW, 21203 = 6.6 A, load 9.6 kW.
- 22:02:23: 7.4/7.5/7.8 A, 5.11 kW, 21203 = 8.9 A, load 5.9 kW.
Rows before and after each (21:55, 22:00, 22:04) are back at 15.4/15.7/16.1 A with 21203 about 24-25 A.
So the inverter ramps the current down for a spell (a step to ~6 A, the floor, and an intermediate 7.5 A)
and back up, in fast mode with the battery at its minimum and no PV; it is not the user current (33545
stays 160). 21203 follows the actual current in the dips. Possibly the inverter limiting import (house
load 11-12 kW with the site import limit?); to check against 32998 and the grid import at those times.
Phases constant (21204 0, 21225 3, 21270 0, 21272 4140). 21203 otherwise 23.9-25.3 A (was 26-27.6).

### 22:24 summary
22:09-22:22, 7 rows, no ERR, watch alive, handshake 80 s (watchdog re-armed 22:10). Session 8215 Wh at 22:22
(10.66 kW mean since 22:06). Steady: 15.4/15.7/16.2 A, 10.69-10.71 kW, no dips this time. Block unchanged
(on, fast, 16.0 A, grid purchase off, time words constant). 21203 settled at 25.0 A from 25.3 (was 26-27.6
at the start, 23.9-25.3 after 21:55): a slow downward drift, not the user current. Battery 13023 = 0.5, PV 0,
grid import 11.3-12.2 kW = load. Phases constant. Nothing new beyond the two dips logged at 22:09.

### 22:39 summary
22:24-22:38, 7 rows, no ERR, watch alive, handshake 44 s. Session 11033 Wh at 22:38 (10.69 kW mean since 22:22).
Steady: 15.4/15.7/16.1-16.2 A, 10.68-10.71 kW, no dips. Block unchanged (on, fast, 16.0 A, grid purchase off,
time words constant). 21203 24.5-24.9 A (user current 16.0 A), still a slow drift down. Battery 13023 = 0.5,
PV 0, import 11.8-12.0 kW = load. Phases constant. Nothing new.

### 22:54 summary
22:40-22:51, 6 rows, no ERR, watch alive, handshake 129 s (watchdog re-armed 22:40). Session 13451 Wh at 22:51
(10.8 kW mean since 22:38). Steady: 15.4/15.7-15.8/16.2 A, 10.72-10.74 kW, one row at 22:51:55 with 10.62 kW and
21203 26.7 A (after 24.4): small, no dip. Block unchanged (on, fast, 16.0 A, grid purchase off, time words
constant). Battery 13023 = 0.5, PV 0, import 11.3-12.2 kW = load. Phases constant. Nothing new.

### 23:09 summary
22:54-23:08, 7 rows, no ERR, watch alive, handshake 45 s. Session 16317 Wh at 23:08 (10.5 kW mean since 22:51).
Steady: 15.4/15.7/16.2 A, 10.59-10.60 kW (about 0.1 kW lower than before 22:52, the phase currents the same:
voltage/power-factor effect). Block unchanged (on, fast, 16.0 A, grid purchase off, time words constant).
21203 24.2-27.2 A (user current 16.0 A), no trend. **Small new: battery 13023 fell 0.5 -> 0.4 % at 22:59**
(still at its floor, battery power 0). Phases constant. Nothing else new. Owner: car 60 % at about 22:55.

### 23:35 summary
23:10-23:33, 12 rows, no ERR, watch alive, handshake 103 s. Session 20695 Wh at 23:33 (10.6 kW mean since 23:08).
Steady: 15.4/15.7-15.8/16.2 A, 10.60-10.62 kW. Block unchanged (on, fast, 16.0 A, grid purchase off, time words
constant). 21203 24.2-27.4 A (user current 16.0 A), no trend. Battery 13023 = 0.4, PV 0, import 11.1-11.9 kW.
Phases constant. Nothing new, no restart needed. Tests start at 0:14 (go/no-go).

### 23:50 summary
23:35-23:48, 7 rows, no ERR, watch alive, handshake 66 s. Session 23503 Wh at 23:48 (10.6 kW mean since 23:33).
Steady: 15.4/15.7-15.8/16.2 A, 10.61-10.66 kW. Block unchanged (on, fast, 16.0 A, grid purchase off, time
words constant). 21203 26.7-27.5 A (user current 16.0 A). Battery 13023 = 0.4, PV 0. Phases constant.
Nothing new, no restart needed. Go/no-go for the tests at 0:14.

### 00:05 summary (2026-11-17)
23:51-00:02, 6 rows, no ERR, watch alive, handshake 11 s. Session 25888 Wh at 00:02 (10.6 kW mean). Steady:
15.4/15.7-15.8/16.2 A, 10.62-10.66 kW. Block unchanged (on, fast, 16.0 A, grid purchase off, time words
constant). 21203 26.1-27.4 A (user current 16.0 A). Battery 13023 = 0.4, PV 0. Phases constant.
Nothing new, no restart needed. Go/no-go at 0:14.

## 00:15 TEST 1: charging on written while already on (inverter 33540 = 0xAA)
Snapshot flushed 00:14:59 (`snapshot_test1.json`): block on (170), fast (160), user 16.0 A, grid purchase off.
Car before: charging, 15.4-15.5/15.8/16.2 A, 10.62-10.64 kW, 21203 27.2 A. Written once at 00:15:18 (protocol
address 33539), same value, then 60 s watched every 5 s, then a fresh-session read at 00:17:04.
Result: **no effect**. Charging stayed on, mode fast, user 16.0 A, grid off; currents 15.4-15.5/15.7-15.8/16.2 A,
power 10.610-10.640 kW, 21203 27.2-27.6 A; no dip, no stop, no mode or time-word change; no write error.
Verdict: **harmless**. A mode select that writes charging on after a mode change is safe when it is already on
(on gerd's P022 inverter, fast mode, 73 % car, battery at its floor). Log: `test1.log`.

## 00:18 TEST 2: fast mode written while already fast (inverter 33541 = 160)
Snapshot flushed 00:18:03 (`snapshot_test2.json`): on, fast, user 16.0 A, grid off. Written once at 00:18:22
(protocol address 33540), same value; 60 s watched every 5 s; fresh-session read 00:20:01.
Result: **no effect**. The session did **not** end (unlike 163 -> 160 and 160 -> 161 on 2026-11-14): charging on,
mode fast, user 16.0 A, grid off; currents 15.4/15.7-15.8/16.2 A, 10.60-10.63 kW; no dip, no stop, time words
unchanged. 21203 27.3-27.5 A, then 26.0-26.2 A from 00:18:45 (its usual wandering, no link to the write).
Verdict: **harmless**: writing the mode it already has does not end the session. Log: `test2.log`.

## 00:21 TEST 3: fast -> user defined (163) at 16 A -> back to fast, with the car charging at ~75 %
Snapshot flushed 00:21:07 (`snapshot_test3.json`): on, fast, user 16.0 A, grid off. Log: `test3.log`.
- 00:21:25 wrote mode 163 (inverter 33541). Within **6 s the session ended**: 00:21:31 wallbox status `completed`,
  0 A, 0 W; at 00:21:41 the inverter's own charging word read **off (0x55)** (we wrote nothing). So 160 -> 163
  with the car charging **stops the charge** (2026-11-14's note said 163 "turns charging on": it did so only from
  off; here it ended the session as 163 -> 160 did then).
- 00:21:57 wrote the user current 33545 = 160 (16.0 A) with charging off: taken, no effect on the car (idle).
  The question this test existed for (21203 against 33545 in user-defined mode) is **not answered**: the car was
  not charging; 21203 read 11.7 A while stopped in 163 and 0.0 A once back in fast mode. Needs 163 entered while
  the car is already off, then charging on, i.e. the reverse order.
- 00:22:45 wrote mode 160: mode fast, user 16.0 A, charging stayed **off**, status `completed`.
- 00:23:17 wrote charging on (33540 = 0xAA): car restarted in **~6 s** (7.5 A, 30 W at 00:23:23), then ramped
  about 1.4 A per 5 s (5.5 kW 00:23:28, 8.6 kW 00:23:44, 10.4 kW 00:23:55): **full power within ~40 s**.
  Fresh-session read 00:24:42: on, fast, 16.0 A, grid off, charging 15.3/15.6/16.2 A, 10.54 kW.
- Cost: the car drew no power from 00:21:31 to 00:23:23 (~1 min 50 s). Written: 163, 160 (user), 160 (mode),
  0xAA; the block is back as found (the time words not re-read in this run).
Verdict: **a mode change to user defined while charging ends the session**; the restore (mode back, then
charging on) works and the car is back at full power in ~40 s. For the integration's mode select: after a
change from fast to user defined, charging on has to be written, as the select already does, and the
"mode change ends the session" side effect now covers 160 -> 163 too (not only 163 -> 160, 160 -> 161).

### 00:26 after the tests
Watch restarted 00:25 (read only), charge monitor and VPN watchdog re-armed (watchdog 00:20). First row 00:25:40:
on, fast, 16.0 A, grid off; car 15.4/15.7/16.1 A, 10.56 kW, session counter restarted (394 Wh since 00:23).
**The time words 33546-33549 changed again** (now 2026-11-17 00:00 UTC and 2026-11-18 00:00 UTC; before the
test 2026-11-16 and 2026-11-17): each moved by exactly one day (86400 s), a date pair that follows the local
day, rolled over at midnight or by the session restart at 00:23, not a clock; the 21:36 change fits the same
reading (11-14/11-15 -> 11-15/11-16 ... to be checked against the 21:33 raw rows). Nothing else changed. Car at about 75 % (session 21:36 -> 00:21 ~28 kWh). Tests done by 00:24, ahead of
the 1:00 window; no writes from now on except a restart of a stopped charge.

### 00:27 summary
One row since the tests (00:25:40): charging on, fast, 16.0 A, grid off; 15.4/15.7/16.1 A, 10.56 kW; session
394 Wh since the 00:23 restart; 21203 27.5 A (user 16.0 A); battery 13023 0.4, PV 0, load 10.95 kW; phases
constant; no ERR. Watch alive, handshake 42 s. The go/no-go prompt fired again at about this time and was not
re-run: tests 1-3 were already done 00:14-00:24. Nothing new, no restart needed.

### 00:35 summary
00:27-00:32, 3 rows, no ERR, watch alive, handshake 106 s. Session 1572 Wh at 00:32 (since the 00:23 restart;
10.6 kW). Steady: 15.4/15.7-15.8/16.2 A, 10.59-10.60 kW. Block unchanged (on, fast, 16.0 A, grid off, time words
constant). 21203 27.3-27.6 A (user 16.0 A). Battery 13023 0.4, PV 0. Phases constant. Nothing new, no restart
needed. ISP reconnect window opens at 1:00; no writes from here except a restart of a stopped charge.

### 00:50 summary
00:34-00:48, 7 rows, no ERR, watch alive, handshake 54 s. Session 4377 Wh at 00:48 (since the 00:23 restart;
10.6 kW). Steady: 15.4-15.5/15.7-15.8/16.2 A, 10.59-10.63 kW. Block unchanged (on, fast, 16.0 A, grid off, time
words constant). 21203 26.1-27.7 A (user 16.0 A). Battery 13023 0.4, PV 0. Phases constant. Nothing new, no
restart needed. Car about 79 % (session since 21:36 about 33 kWh). ISP reconnect window starts at 1:00.

### 01:05 summary
00:50-01:03, 7 rows, no ERR, watch alive, handshake 14 s. Session 7144 Wh at 01:03 (since the 00:23 restart;
10.6 kW). Steady: 15.4/15.8/16.2 A, 10.59-10.61 kW. Block unchanged (on, fast, 16.0 A, grid off, time words
constant). 21203 26.1-27.7 A (user 16.0 A). Battery 13023 0.4, PV 0. Phases constant. The ISP reconnect
window (1:00-4:00) has begun; no reconnect seen yet. Car about 80 % (28 + 7 kWh since 21:36 at about 1.06
kWh per point). Nothing new, no restart needed.

### 01:20 summary
01:06-01:17, 6 rows, no ERR, watch alive, handshake 105 s. Session 9528 Wh at 01:17 (since the 00:23 restart;
10.6 kW). Steady: 15.4/15.7-15.8/16.2 A, 10.58-10.62 kW. Block unchanged (on, fast, 16.0 A, grid off, time words
constant). 21203 26.5-27.5 A (user 16.0 A). Battery 13023 0.4, PV 0. Phases constant. No ISP reconnect seen yet
(window 1:00-4:00). Car about 82 %. Nothing new, no restart needed.

### 01:35 summary
01:19-01:33, 7 rows, no ERR, watch alive, handshake 59 s. Session 12322 Wh at 01:33 (since the 00:23 restart;
10.6 kW). Steady: 15.4-15.5/15.8/16.2 A, 10.62-10.65 kW. Block unchanged (on, fast, 16.0 A, grid off, time words
constant). 21203 26.2-27.7 A (user 16.0 A). Battery 13023 0.4, PV 0. Phases constant. No ISP reconnect seen
yet. Car about 85 % (40 kWh since 21:36 at about 1.06 kWh per point, 47 % at 21:36). Nothing new, no restart
needed.

### 01:50 summary
01:35-01:48, 7 rows, no ERR, watch alive, handshake 72 s. Session 15084 Wh at 01:48 (since the 00:23 restart;
10.6 kW). Steady: 15.4-15.5/15.8/16.2 A, 10.63-10.65 kW. Block unchanged (on, fast, 16.0 A, grid off, time
words constant). 21203 26.3-27.7 A (user 16.0 A). **Small: battery 13023 0.4 -> 0.3 % at 01:37** (still at its
floor, no battery power; 0.5 -> 0.4 happened at 22:59). PV 0. Phases constant. No ISP reconnect seen yet. Car
about 87 %. Nothing else new, no restart needed.

## 02:00 TEST 4 (owner's go, a deliberate stop): 21203 against the user current in user-defined mode
Car at ~86 % (VW app), charging in fast mode. Order reversed from test 3: charging off, then 163, then the
user current, then charging on. Snapshot flushed 02:00:25 (`snapshot_test4.json`); log `test4.log`.
- 02:00:38 wrote charging off (33540 = 0x55): the car stopped within ~6 s (status `completed`, 0 A, 02:00:44).
- 02:00:59 wrote mode 163 with charging off: the inverter's charging word read **on (0xAA) 5 s later** without
  our writing it (as 2026-11-14: 163 turns charging on from off); the wallbox stayed `completed`.
- 02:01:10 wrote user current 33545 = 160 (16.0 A): status `suspended by the charge point`, then **charging at
  6.0 A at 02:01:15**, 21203 = 6.0 A, ramping about 1.4 A per 5 s: 21203 6.0, 8.8, 11.7, 14.6, **16.0 A from 02:01:53**
  (the car draws 15.0/15.3/15.8 A, 10.36 kW), steady for 20 s.
- **21203 follows the user current exactly in mode 163**: 16.0 A at 16.0 A set, **10.0 A within 5 s of writing
  33545 = 100** (02:02:19; the car 9.3/9.4/9.7 A, 6.39 kW, 0.7 A below the setting, as the capability test's
  6/8/10 A did). So 21203 is the inverter's offer in 0.1 A, and the car takes about 0.6-0.7 A less.
- **In fast mode the offer is 24-28 A while the car draws 15.4-16.2 A**: the car (or its onboard charger) takes
  at most ~16 A per phase, so fast mode offers more than it can use; 21203 is not the car's current there. The
  26-27 A wandering seen all night is the inverter's offer in fast mode, not a reading of the car.
- 02:02:46 wrote user 16.0 A back (21203 10.0 -> 12.8 A, ramping), 02:02:56 wrote mode 160: **the session ended again
  (163 -> 160 ends it)**, status `completed` 02:03:02-02:03:13; 02:03:12 wrote charging on: charging at 02:03:18, full
  power (15.3/15.7/16.1 A, 10.57 kW) by 02:03:52. Fresh-session read 02:04:41: on, fast, 16.0 A, car 15.4/15.7/16.1 A,
  10.60 kW, 21203 26.4 A: **the house is as found**.
- Cost: no charging 02:00:44-02:01:15 (~30 s) and 02:02:57-02:03:18 (~20 s); the charge ran at less than full
  power from 02:01:15 to 02:01:53 and 02:02:25-02:03:52 (the 10 A and ramp phases).
Verdict: answered. 21203 = the user current exactly in mode 163 (0.1 A), and the 24-28 A in fast mode is the
inverter's offer, above what the car draws (~16 A/phase). Mode changes 160 -> 163 (while charging) and 163 -> 160
end the session; 163 entered with charging off turns charging on by itself and starts at 6 A, ramping 1.4 A / 5 s.

### 02:06 summary
01:51-01:57 (4 rows, then test 4 at 02:00-02:04, no rows while the watch was stopped; restarted 02:05, first row
pending): no ERR, handshake 130 s, no ISP reconnect seen yet. Before the test: session 16671 Wh at 01:57 (since the
00:23 restart), steady 15.4/15.8/16.2 A, 10.64 kW, block on/fast/16.0 A/grid off, time words 39168/27387,
60032/27388, 21203 26.8-27.7 A, battery 13023 0.3, PV 0, phases constant. After test 4 (02:04:41 fresh read): on,
fast, 16.0 A, 15.4/15.7/16.1 A, 10.60 kW. Nothing needing a restart.

### 02:20 summary: NEW, the car suspended the charge by itself
02:05-02:17: 6 rows, steady 15.4-15.5/15.7-15.8/16.2 A, 10.61-10.65 kW; session 2423 Wh at 02:17 (since the 02:03
restart), block on/fast/16.0 A/grid off, time words unchanged (39168/27387, 60032/27388) through test 4, 21203
26.4-27.5 A, battery 13023 0.3, PV 0, phases constant.
**02:19:18 (new): wallbox status `suspended by the vehicle`, 0 A, 0 W, 21203 = 21.9 A; the inverter's charging
word still reads ON (0xAA), mode fast, 16.0 A.** House load fell to ~1.9-2.0 kW (the house alone). Seen again at
02:19:56-02:20:05 (4 reads): the state holds. So **the car, not the inverter or the wallbox, paused the charge**:
nothing of ours was written (the last write was the 02:03:12 charging on); not a "completed" end either. Car
about 88-89 % (session since 21:36: 28 + 8 kWh). A restart write would not help (the word is already on).
No ISP reconnect seen yet, handshake 124 s. VPN watchdog re-armed 02:20. No write made.

### 02:36 the vehicle's suspension: flapping
02:19:18-02:30:35 `suspended by the vehicle` (0 A, 0 W, house load 1.7-2.0 kW), the inverter word on (0xAA), fast,
16.0 A, grid off all the time. 02:32:48 the wallbox reported `charging` for one row (177 W, 0 A on the phases,
session +2 Wh), and at 02:35:02 `suspended by the vehicle` again (21203 26.8 A, load 0.5 kW). So the car is the one
pausing, and it tried once and quit again within ~2 min. Session counter 2569 -> 2572 Wh across the 13 minutes.
Nothing written since 02:03:12; a charging-on write would be a no-op (word already on). Handshake 122 s, no ISP
reconnect seen yet. Waiting for the owner's reading of the VW app (reason for the pause) before cycling charging.

### 02:36 summary
Rows 02:30-02:35 as logged above: suspended by the vehicle (02:30:35), one `charging` row at 02:32:48 (177 W),
suspended again at 02:35:02. Block unchanged (on/fast/16.0 A/grid off, time words constant), battery 13023 0.3,
PV 0, phases constant, no ERR, watch alive, handshake 16 s, no ISP reconnect seen yet. The standing restart rule
does not apply: the inverter's word is already on and the pause is the vehicle's; no write made. Waiting for the
owner's VW app reading.

### 02:50 summary
02:35-02:48, 7 rows, no ERR, watch alive, handshake 174 s, no ISP reconnect seen yet. Car **suspended by the vehicle**
in 6 of 7 rows (0 A, 0 W); **one more attempt at 02:46:16** (`charging`, 116 W), suspended again at 02:48:29. The
attempts so far: 02:32:48 and 02:46:16, each about 2 min, about 13 min apart. Session 2576 Wh at 02:48 (+7 Wh since
02:19, i.e. nothing charged). House load 0.25-1.95 kW (the house alone; the 1.7-1.95 kW rows are about 1 min
long bursts). Block unchanged (on, fast, 16.0 A, grid off, time words constant). 21203 21.8-27.8 A (the offer, as
in fast mode). Battery 13023 0.3, PV 0, phases constant. No write since 02:03:12; the inverter word is on, so the
standing restart rule does not apply. Car about 89 % (36 kWh since 21:36 at ~1.06 kWh/pt + the 47 %). Owner has not
yet given the VW app's reason or a go to cycle charging.

### 02:54 ISP RECONNECT (the first of the night)
Last good handshake about 02:46:50; the 02:50:47 watch round could not connect to either device (inverter 502 and
wallbox 516, both "could not connect"); the VPN watchdog saw the handshake stale (311 s) at 02:52:01 and re-upped
the tunnel (no handshake within its 10 s wait, so it re-upped again at 02:53:11); handshake 9 s at 02:53:21; TCP to
both ports answered at 02:53:15. **Gap: about 3.5 min (02:49-02:53)**; no manual step needed. The watchdog's 10 s
wait is too short (it re-upped a tunnel that was coming up): harmless this time. Nothing written during the gap.
First row after the gap, 02:53:37: block on (the inverter word 170), car `charging` at 172 W (a third attempt after
02:32:48 and 02:46:16; each about 2 min, so the car's own retry cycle is about 7-13 min), session 2578 Wh. The charge
while the tunnel was down could not be watched (3.5 min of the car's suspended state at most).

### 03:05 summary
02:53-03:02: 5 rows (one ERR at 02:50:47, the reconnect gap), no new ERR after, watch alive, handshake 132 s. Car
`suspended by the vehicle` at 02:55:50, 02:58:04, 03:00:17, 03:02:31 (0 A, 0 W); the 02:53:37 attempt (172 W) is the
third short one. Session 2578 Wh, unchanged since 02:53 (nothing charged since 02:19 except those minutes). House
load 0.3-0.8 kW. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203 25.9-27.8 A, battery 13023
0.3, PV 0, phases constant. The inverter word is on, so the restart rule does not apply; no write. Car about 89 %.
The owner has not answered the questions about the VW app and cycling charging (asked 02:21, 02:36, 02:50).

### 03:20 summary
03:02-03:18, 8 rows, no ERR, watch alive, handshake 79 s, no further reconnect after 02:49-02:53. Car `suspended by
the vehicle` in every row (0 A, 0 W) since 02:55:50: no attempt in this window (the last was 02:53:37). Session 2580
Wh (unchanged apart from 2 Wh at 03:04). House load 0.3-2.5 kW (bursts of ~2 kW, the house alone). Block unchanged
(on/fast/16.0 A/grid off, time words constant), 21203 19.6-27.8 A (the offer), battery 13023 0.3, PV 0, phases
constant. No write since 02:03:12. Car about 89 %: 1 h 20 min without charging. Owner not answered (a push was sent
03:05). VPN watchdog re-armed 03:20.

### 03:35 summary
03:18-03:34, 8 rows, handshake 17 s, watch alive, no tunnel drop since 02:53. Car `suspended by the vehicle` in 7 rows
(0 A, 0 W), no attempt since 02:53:37; **one ERR at 03:27:29**: `read_holding_registers(21202)` timed out on the
wallbox (the inverter rows and the phases read fine in the same round; TCP to 516 refused for a moment at 03:28:06
and was fine again at 03:29:54: the TLS port's known refusal of connections in quick succession, my own check
included). Session 2580 Wh, unchanged. House load 0.27-0.52 kW (quieter than 02:50-03:10). Block unchanged
(on/fast/16.0 A/grid off, time words constant), 21203 27.0-27.8 A, battery 13023 0.3, PV 0, phases constant. No write
since 02:03:12. The car is about 89 %, suspended for 1 h 15 min; the owner has not answered (asked 02:21, 02:36,
02:50; push 03:05). Plan: keep holding; reconsider with the owner after the reconnect window closes at 4:00.

### 03:50 summary
03:34-03:47, 7 rows, no ERR, watch alive, handshake 110 s, no tunnel drop since 02:53. Car `suspended by the vehicle` in
every row (0 A, 0 W); no attempt since 02:53:37 (the car's retry rhythm of 02:32/02:46/02:53 has stopped). Session
2580 Wh, unchanged. House load 0.25-0.65 kW. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
26.6-27.8 A, battery 13023 0.3, PV 0, phases constant. No write since 02:03:12. Car about 89 %, no charging for
1 h 30 min. Owner has not answered. VPN watchdog re-armed 03:50.

### 03:53 the inverter's word went off by itself; one restart, the car still refuses
- 03:50:08: after 1 h 30 min of `suspended by the vehicle`, the wallbox status went to `completed` and **the inverter's
  charging word went to off (0x55)** by itself (the standing restart rule now applied: a stopped charge, tunnel up
  (handshake 25 s), car about 89 %, not full).
- 03:51:02: **one write, 33540 = 0xAA** (restart 1 of the allowed 2; watch stopped first, fresh-session reads).
  Result: the inverter's word on again (03:51:07 and the fresh read 03:52:47: on, fast, 16.0 A, grid off, time words
  constant), and the offer 21203 ramped 8.2, 9.6, 11.1, 12.5, 14.7, 16.2, 17.6, 19.1, 19.7 A (a ramp of about 1.4 A /
  5 s, as the inverter does when it offers current); but the wallbox status stayed **`suspended by the vehicle`**, 0 A,
  0 W through 03:52:52. So the car still declines. No second restart (rule: not more than two without the car drawing
  power for 10 minutes). The watch restarted 03:53.

### 04:05 summary
03:50-04:02: 03:50:08 `completed` + the inverter word off, the 03:51:02 restart (logged above), then 03:53-04:02 5 rows: the
inverter word on (170), fast, 16.0 A, grid off, time words constant; car `suspended by the vehicle`, 0 A, 0 W;
21203 19.8-19.9 A (the offer after the restart), 27.8 A at 04:02:36; the session counter reset to 0 at the restart
(the wallbox's new session, 0 Wh: nothing charged). No ERR, watch alive, handshake 32 s. **The 1:00-4:00 ISP window
has closed with exactly one reconnect (02:49-02:53, about 3.5 min).** House load 0.26-2.7 kW (the house alone).
Battery 13023 0.3, PV 0, phases constant. The inverter word is on, so no further restart is due; the car is the
one declining (suspended since 02:19, 1 h 45 min). Car about 89 %. Owner has not answered the VW app question.

### 04:20 summary
04:02-04:18, 8 rows, no ERR, watch alive, handshake 121 s, no tunnel drop since 02:53. Car `suspended by the vehicle`
in every row (0 A, 0 W), session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words
constant), 21203 27.2-27.8 A (the offer), house load 0.25-0.47 kW, battery 13023 0.3 -> 0.2 at 04:13, PV 0, phases
constant. No write since 03:51:02; the inverter word is on, no restart is due. Car about 89 %, suspended since
02:19 (2 h). The owner has not answered. VPN watchdog re-armed 04:20.

### 04:35 summary
04:18-04:34, 8 rows, no ERR, watch alive, handshake 68 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
25.5-27.8 A, house load 0.24-0.82 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the inverter
word is on, no restart is due. Car about 89 %, suspended since 02:19 (2 h 15 min). The owner has not answered.

### 04:50 summary
04:34-04:47, 7 rows, no ERR, watch alive, handshake 114 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
26.8-27.8 A, house load 0.26-0.58 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the inverter
word is on, no restart is due. Car about 89 %, suspended since 02:19 (2 h 30 min). The owner has not answered.
VPN watchdog re-armed 04:50.

### 05:05 summary
04:47-05:03, 8 rows, no ERR, watch alive, handshake 78 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
25.9-27.8 A, house load 0.26-0.72 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the
inverter word is on, no restart is due. Car about 89 %, suspended since 02:19 (2 h 45 min). The owner has not
answered.

### 05:20 summary
05:03-05:19, 8 rows, no ERR, watch alive, handshake 30 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
25.9-27.9 A, house load 0.23-0.54 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the
inverter word is on, no restart is due. Car about 89 %, suspended since 02:19 (3 h). The owner has not answered.
VPN watchdog re-armed 05:20.

### 05:35 summary
05:19-05:32, 7 rows, no ERR, watch alive, handshake 110 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
25.9-27.8 A, house load 0.29-0.79 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the
inverter word is on, no restart is due. Car about 89 %, suspended since 02:19 (3 h 15 min). The owner has not
answered.

### 05:50 summary
05:35-05:48, 7 rows, no ERR, watch alive, handshake 70 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
27.1-27.9 A, house load 0.25-0.48 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the
inverter word is on, no restart is due. Car about 89 %, suspended since 02:19 (3 h 30 min). The owner has not
answered. VPN watchdog re-armed 05:50.

### 06:05 summary
05:48-06:04, 8 rows, no ERR, watch alive, handshake 25 s. Car `suspended by the vehicle` in every row (0 A, 0 W),
session 0 Wh since the 03:51 restart. Block unchanged (on/fast/16.0 A/grid off, time words constant), 21203
25.8-27.9 A, house load 0.23-0.78 kW, battery 13023 0.2, PV 0, phases constant. No write since 03:51:02; the
inverter word is on, no restart is due. Car about 89 %, suspended since 02:19 (3 h 45 min). The owner has not
answered.


---

# Test 1 log

```
00:14:59 snapshot [85, 161, 170, 160, 0, 0, 0, 160, 18304, 27386, 39168, 27387, 85]
00:15:02 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.5, 15.8, 16.2] 10639W
00:15:07 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.4, 15.8, 16.2] 10616W
00:15:13 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.4, 15.8, 16.2] 10618W
00:15:18 WROTE on (33539) = 170
00:15:18 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.4, 15.7, 16.2] 10619W
00:15:23 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.5, 15.8, 16.2] 10626W
00:15:29 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.5, 15.8, 16.2] 10617W
00:15:34 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.5, 15.8, 16.2] 10623W
00:15:39 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10615W
00:15:45 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10618W
00:15:50 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10610W
00:15:55 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10615W
00:16:01 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.2A [15.5, 15.8, 16.2] 10626W
00:16:06 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.5, 15.8, 16.2] 10640W
00:16:11 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.4, 15.8, 16.2] 10625W
00:16:16 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.5, 15.8, 16.2] 10628W
00:17:04 [fresh read] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.6A [15.5, 15.8, 16.2] 10641W
```


---

# Test 2 log

```
00:18:03 snapshot [85, 161, 170, 160, 0, 0, 0, 160, 18304, 27386, 39168, 27387, 85]
00:18:06 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.5A [15.4, 15.8, 16.2] 10612W
00:18:11 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.4, 15.8, 16.2] 10621W
00:18:17 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.4, 15.8, 16.2] 10627W
00:18:22 WROTE mode (33540) = 160
00:18:22 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.4, 15.7, 16.2] 10621W
00:18:27 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.3A [15.4, 15.8, 16.2] 10624W
00:18:33 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10614W
00:18:40 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.5A [15.4, 15.7, 16.2] 10616W
00:18:45 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.9A [15.4, 15.8, 16.2] 10626W
00:18:50 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.2A [15.4, 15.8, 16.2] 10618W
00:18:56 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.2A [15.4, 15.8, 16.2] 10613W
00:19:01 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.2A [15.4, 15.8, 16.2] 10606W
00:19:06 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.1A [15.4, 15.7, 16.2] 10604W
00:19:12 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.0A [15.4, 15.8, 16.2] 10619W
00:19:17 [after mode 160] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.0A [15.4, 15.8, 16.2] 10619W
00:20:01 [fresh read] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.5A [15.5, 15.8, 16.2] 10626W
```


---

# Test 3 log

```
00:21:07 snapshot [85, 161, 170, 160, 0, 0, 0, 160, 18304, 27386, 39168, 27387, 85]
00:21:09 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 27.4A [15.4, 15.8, 16.2] 10612W
00:21:15 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.3A [15.4, 15.8, 16.2] 10619W
00:21:20 [before] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.4A [15.4, 15.8, 16.2] 10598W
00:21:25 WROTE mode (33540) = 163
00:21:25 [after mode 163] charging=on mode=user_defined user=16.0A grid= | charging 26.4A [15.4, 15.8, 16.2] 10603W
00:21:31 [after mode 163] charging=on mode=user_defined user=16.0A grid= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:21:36 [after mode 163] charging=on mode=user_defined user=16.0A grid= | completed 11.7A [0.0, 0.0, 0.0] 0W
00:21:41 [after mode 163] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:21:47 [after mode 163] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:21:52 [after mode 163] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:21:57 WROTE user (33544) = 160
00:21:58 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:03 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:08 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:14 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:19 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:24 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:30 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:35 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:40 [after user 16.0] charging=off mode=user_defined user=16.0A grid | completed 11.7A [0.0, 0.0, 0.0] 0W
00:22:45 WROTE mode (33540) = 160
00:22:46 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:22:51 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:22:56 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:23:02 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:23:07 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:23:12 [after mode 160] charging=off mode=fast user=16.0A grid=85 raw= | completed 0.0A [0.0, 0.0, 0.0] 0W
00:23:17 WROTE on (33539) = 170
00:23:18 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | completed 0.0A [0.0, 0.0, 0.0] 0W
00:23:23 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 7.5A [0.0, 0.0, 0.0] 30W
00:23:28 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 9.7A [7.9, 8.1, 8.4] 5532W
00:23:34 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 11.2A [9.5, 9.7, 10.1] 6529W
00:23:39 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 12.6A [10.9, 11.2, 11.6] 7582W
00:23:44 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 14.1A [12.4, 12.7, 13.1] 8576W
00:23:50 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 15.6A [13.7, 14.0, 14.5] 9471W
00:23:55 [after on] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 17.1A [15.1, 15.5, 16.0] 10444W
00:24:42 [fresh read] charging=on mode=fast user=16.0A grid=85 raw=[ | charging 26.3A [15.3, 15.6, 16.2] 10537W
```


---

# Test 4 log

```
02:00:25 snapshot [85, 161, 170, 160, 0, 0, 0, 160, 39168, 27387, 60032, 27388, 85]
02:00:28 [before] on=170 mode=160 user=16.0A | charging 21203=27.5A amps=[15.4, 15.8, 16.2] 10631W
02:00:33 [before] on=170 mode=160 user=16.0A | charging 21203=27.6A amps=[15.4, 15.7, 16.2] 10610W
02:00:38 WROTE charging off (33539) = 85
02:00:38 [after off] on=85 mode=160 user=16.0A | charging 21203=27.7A amps=[15.4, 15.7, 16.2] 10617W
02:00:44 [after off] on=170 mode=160 user=16.0A | completed 21203=27.8A amps=[0.0, 0.0, 0.0] 0W
02:00:49 [after off] on=85 mode=160 user=16.0A | completed 21203=27.8A amps=[0.0, 0.0, 0.0] 0W
02:00:54 [after off] on=85 mode=160 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:00:59 WROTE mode 163 (33540) = 163
02:01:00 [after 163] on=85 mode=163 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:01:05 [after 163] on=170 mode=163 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:01:10 WROTE user current 16.0 A (33544) = 160
02:01:10 [after user 16] on=170 mode=163 user=16.0A | suspended by the charge point 21203=6.0A amps=[0.0, 0.0, 0.0] 0W
02:01:15 [after user 16] on=170 mode=163 user=16.0A | charging 21203=6.0A amps=[5.7, 5.8, 6.0] 3934W
02:01:21 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=8.8A amps=[6.7, 6.8, 7.1] 5295W
02:01:26 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=8.8A amps=[8.0, 8.1, 8.4] 5504W
02:01:31 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=11.7A amps=[10.7, 10.9, 11.2] 7373W
02:01:37 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=11.7A amps=[10.9, 11.1, 11.5] 7517W
02:01:42 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=14.6A amps=[13.6, 13.9, 14.4] 9401W
02:01:47 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=14.6A amps=[13.6, 13.9, 14.4] 9404W
02:01:53 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=16.0A amps=[15.0, 15.3, 15.8] 10353W
02:01:58 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=16.0A amps=[15.0, 15.3, 15.8] 10356W
02:02:03 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=16.0A amps=[15.0, 15.3, 15.8] 10360W
02:02:09 [163 charging 16 A] on=170 mode=163 user=16.0A | charging 21203=16.0A amps=[15.0, 15.3, 15.8] 10361W
02:02:14 WROTE user current 10.0 A (33544) = 100
02:02:14 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=16.0A amps=[15.0, 15.3, 15.8] 10373W
02:02:19 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=10.0A amps=[15.0, 15.3, 15.8] 10367W
02:02:25 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=10.0A amps=[9.3, 9.4, 9.7] 6387W
02:02:30 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=10.0A amps=[9.3, 9.4, 9.7] 6381W
02:02:35 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=10.0A amps=[9.3, 9.4, 9.7] 6387W
02:02:40 [163 charging 10 A] on=170 mode=163 user=10.0A | charging 21203=10.0A amps=[9.3, 9.4, 9.7] 6386W
02:02:46 WROTE user current 16.0 A (restore) (33544) = 160
02:02:46 [restore user] on=170 mode=163 user=16.0A | charging 21203=10.0A amps=[9.3, 9.4, 9.7] 6381W
02:02:51 [restore user] on=170 mode=163 user=16.0A | charging 21203=12.8A amps=[11.6, 11.8, 12.2] 8184W
02:02:56 WROTE mode 160 (restore) (33540) = 160
02:02:57 [after mode 160] on=85 mode=160 user=16.0A | charging 21203=12.8A amps=[11.9, 12.1, 12.5] 8226W
02:03:02 [after mode 160] on=85 mode=160 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:03:07 [after mode 160] on=85 mode=160 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:03:12 WROTE charging on (restore) (33539) = 170
02:03:13 [after restore on] on=170 mode=160 user=16.0A | completed 21203=0.0A amps=[0.0, 0.0, 0.0] 0W
02:03:18 [after restore on] on=170 mode=160 user=16.0A | charging 21203=7.4A amps=[0.0, 0.0, 0.0] 32W
02:03:23 [after restore on] on=170 mode=160 user=16.0A | charging 21203=9.7A amps=[8.1, 8.2, 8.5] 5565W
02:03:29 [after restore on] on=170 mode=160 user=16.0A | charging 21203=11.1A amps=[9.5, 9.7, 10.1] 6568W
02:03:34 [after restore on] on=170 mode=160 user=16.0A | charging 21203=12.6A amps=[11.0, 11.2, 11.6] 7618W
02:03:39 [after restore on] on=170 mode=160 user=16.0A | charging 21203=14.1A amps=[12.3, 12.6, 13.0] 8521W
02:03:46 [after restore on] on=170 mode=160 user=16.0A | charging 21203=16.3A amps=[14.4, 14.7, 15.2] 9930W
02:03:52 [after restore on] on=170 mode=160 user=16.0A | charging 21203=17.7A amps=[15.3, 15.7, 16.2] 10587W
02:03:57 [after restore on] on=170 mode=160 user=16.0A | charging 21203=19.2A amps=[15.3, 15.7, 16.1] 10566W
02:04:41 [fresh read] on=170 mode=160 user=16.0A | charging 21203=26.4A amps=[15.4, 15.7, 16.1] 10596W
```
