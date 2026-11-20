# gerd's wallbox, 2026-11-20: a stopped car started again, the mode select's writes, scheduled charging (162)

Raw note, frozen at ingest. A WireGuard tunnel to the owner's site, brought up from the devcontainer
(split routing, the site's /24 only). The owner consented to any test (relayed by the maintainer,
13:56). The inverter at unit 1 over its LAN cable (port 502), the AC22E-01 over TLS (516, unit 248),
read through `scripts/dev/managed_wallbox_field.py`; one client per path. Whether the owner's own Home
Assistant polls was not known. Register numbers; the protocol address is one lower. Times are CET. The
car's state of charge is the owner's reading. No address or serial is in this note.

## 13:55 baseline

- Car plugged in and charging, **57 %** (owner).
- Through the dongle (unit 3, read once at 13:50): status 21317 = 3 (charging), pilot 21312 = 5.95 V
  (state C), power 21308 = 10685 W.
- Energy: PV 268 W, grid import 10982 W, load 11192 W, battery level 13023 = **2.8 %**, battery 0 W.
  November overcast: no sun-dependent test (phase switching, PV surplus) is possible today.
- Inverter block 33538-33550: `[85, 161, 170, 160, 0, 0, 0, 160, 39168, 27387, 60032, 27388, 85]` =
  charging **on**, mode **160 fast**, user current 16.0 A, grid purchase 85 (off); 33538 = 85,
  33539 = 161 as before. The time pair still reads 2026-11-17 and 2026-11-18 00:00 UTC, as left on 11-17: it does not advance by itself.
- Wallbox: charging, setting 21203 = 27.9 A (the inverter's offer in fast mode), phases 15.3 / 15.6 /
  16.1 A, 10.68 kW.
- The home battery at 2.8 % and idle (0 W) under 11 kW of load: at or near the floor it is held to (2026-11-17
  counted 0.5 % as its minimum). A fast charge runs on, unstopped.

## 13:57 test 3: a car stopped for twelve minutes, started again by charging on

`managed_wallbox_field.py charge off 720`: snapshot charging word 170 (0xAA, on) flushed to disk,
then 33540 = 0x55 (off) at 13:57:30.

- 13:57:30, the first read after the write: still charging, 10.69 kW.
- 13:57:33: status **completed** (6), 0 A on every phase, 21203 = 0. The stop took at most 3 s, as on
  11-14 and 11-16 (< 1 s, 4 s).
- The block held off for the whole pause; nothing else in it moved (mode 160, user 16.0 A, grid 85,
  the time pair). The status stayed *completed*, never *idle* or *suspended*.
- **14:07:01: charging went back to on (170) by itself, 9 min 31 s after the stop, with nothing written
  from here** (the tool only reads during the pause; its restore was due at 14:09:30). The last read
  with charging off was 14:06:58. Who wrote it (the owner's app, their Home Assistant, or the
  inverter) was not known at the time: asked of the owner.
- The car woke without a replug: 14:07:01 *suspended by the charge point* (21203 6.7 A), 14:07:05
  to 14:07:15 *suspended by the vehicle* while 21203 ramped 7.4 → 10.3 A, **14:07:18 charging**
  (8.5 A, 5.8 kW), 14:07:38 full (15.1-16.1 A, 10.6 kW). 17 s from on to current, 37 s to full
  power. 21203 kept ramping past the car's 16 A (21.2 A at 14:07:51): the inverter's offer.
- So a car stopped for 9.5 minutes (not quite the 10 the plan asks) resumed on charging on alone.
  On 2026-11-14 a 7-minute stop needed a replug; what differed is not known.
- 14:09:41 the tool's restore found 170 already there on a fresh session and wrote nothing; the car
  charged at 10.6 kW through 14:09:54. The house is as it was at 13:55.
- Whether the owner pressed Start: unknown at 14:12 (the maintainer will ask). To tell an owner from
  the inverter, the stop is repeated with a 15-minute pause.

## 14:28 the stop repeated, 15 minutes: a second writer

`charge off 900`: snapshot 170, 33540 = 0x55 at 14:28:26 (the car charging, 10.72 kW).

- 14:28:30: status *completed*, 0 A: the stop took at most 4 s.
- **14:28:30, 14:28:33, 14:28:36: the word read 170 (on) again**, and 21203 began a ramp (0 → 7.3 →
  8.1 A) with the car still at 0 A, status *completed*. **14:28:40: 85 (off) again**, 21203 back to 0.
  Nothing was written from here between 14:28:26 and the restore. So within 4 s of our off something
  wrote on, and within 14 s something wrote off. Read on the inverter's LAN cable, one client.
- Candidates: the owner in the app (who knew a test was running), an automation of the owner's on
  another client, or the inverter itself.
- From 14:28:40 the word held 85 (off) for the rest of the pause, the status *completed*, 0 A. One read
  timed out at 14:32:07 (8 s, the wallbox's TLS session); the next answered.
- **No re-enable at 9.5 minutes this time**: the off held from 14:28:40 to 14:43:26 (14 min 46 s). So
  the 14:07 on in the first run was not a fixed inverter timeout.
- The owner could not be asked (14:40); who wrote 14:07's on and the 14:28:30-14:28:40 on/off stays
  open.

## 14:43 test 3 answered: a car stopped fifteen minutes, woken by charging on over Modbus

- 14:43:26 the restore wrote 170 (on); 14:43:31 a fresh session read 170.
- 14:43:31 *suspended by the vehicle* (21203 7.4 A), 14:43:38 9.5 A, 14:43:41 *suspended by the
  charge point* (10.3 A), **14:43:45 charging**, 7.8-8.3 A, 5.3 kW. **19 s from the write to current**,
  no replug, after 15 minutes stopped.
- The house is as it was at 13:55: charging on, fast, 16.0 A user current, grid purchase off.

## 14:46 the stop a third time, 3 minutes: the on/off after an off, reproduced

`charge off 180`: snapshot 170, off written 14:46:51 (car at 10.66 kW).

- 14:46:55 (4 s): status *completed*, 0 A, **and the word reads 170 (on)**; 21203 0 → 7.4 → 8.1 A
  over the next reads, the car still at 0 A. **14:47:04 the word reads 85 again**, 21203 0. The same
  shape as 14:28:30-14:28:40: on 4 s after our off, off again about 9-13 s later. Nothing written
  from here. Not seen in the first run (13:57:30 off, every read from 13:57:33 on read 85).
- The off then held to the restore. 14:49:54 wrote 170, 14:49:59 read 170 on a fresh session; the
  car charging at 14:49:59 (1.6 A, one phase first), 6.6 kW at 14:50:12, 10.5 kW at 14:51:43 (21203
  28.0 A, the inverter's offer). 5 s from the write to current after 3 minutes stopped.
- 14:52:24 the block: charging on, fast, 16.0 A, grid purchase off. The house as at 13:55.
- Open: what writes the on 4 s after an off and the off after it. Twice in three stops, both times
  with the word read on the inverter's cable at 3 s intervals. A second client polling or writing
  (the owner's Home Assistant, an automation) and the inverter itself are not told apart from here.

## 14:54 the mode select's writes replayed: fast → user defined while charging

`tmp/gerd-wallbox-2026-11-20/select_replay.py` (gitignored): `ev_charger.mode_writes(163, charge=True)`
-- the mode alone, as the select writes it -- with the car charging at 10.7 kW, then a watch every
2-3 s on the inverter's cable and the wallbox's TLS port. Snapshot (word 170, mode 160) on disk first.

- 14:54:29 wrote 33541 = 163.
- 14:54:30 (+1 s): **the word reads 85 (off), written by the inverter**; the car still at 15-16 A.
- 14:54:33 (+4 s): status *completed*, 0 A: **the session ended**, as on the night of 11-16.
- 14:54:36 (+7 s): **the word reads 170 (on) again, written by the inverter**, status *suspended by
  the vehicle*, 21203 8.8 A.
- 14:54:38 (+9 s): charging, 1.8 A on one phase; 21203 ramped 8.8 → 11.7 → 14.6 → 16.0 A in steps
  of about 10 s, the car at 0 A until 14:55:06 (+37 s), then 13.7-14.5 A and 14.8-15.8 A from
  14:55:09 (21203 = 16.0 A = the user current).
- So entering user defined while charging **ends the session and starts it again by itself**,
  within 7 s: an off, then an on, both the inverter's. The charging-on the select writes only when
  leaving user defined would not have been needed here.
- The off-then-on is the same shape as the on-then-off seen 4 s after our charging-off at 14:28:30
  and 14:46:55: the inverter's word moves twice on a transition.
- 14:55:32 the last answer: from then the inverter's cable timed out (14:55:57, 14:56:11 response
  timeouts, 14:56:26 connection refused-by-timeout). The second step (user defined → fast + on) was
  not run.
- Restore: 14:56:36 wrote mode 160, 14:56:38 wrote word 170, 14:56:41 a fresh session read
  [170, 160]. The watch after it timed out on the cable at 14:56:49.

## 14:58 found off, by another hand; the owner's Home Assistant integration disabled

- 14:58:45 the block read **charging off** (85), mode fast, and **the time pair rewritten** to
  2026-11-20 and 2026-11-21 00:00 UTC (was 11-17 / 11-18); the car *completed*, 0 A. Nothing was written
  from here after 14:56:38. The time pair moves when the app saves (11-14), so an app save is the
  likeliest writer; not confirmed.
- At about the same time the maintainer disabled this integration on the owner's Home Assistant (it
  had been polling, which this session did not know), and found their own host's WireGuard tunnel to
  the site up beside the devcontainer's, with the same key; it was taken down. Two tunnels sharing a
  peer key steal each other's handshake, which fits the cable's timeouts from 14:55:32. The
  devcontainer's tunnel was cycled at about 15:00 and answered. 15:01:31 charging on written (fresh read 170, mode 160); the car charging from 15:01:48, 10.3 kW at 15:02:09.
- The maintainer asked for charging back on and the tests to go on.

## 15:03 the mode select's writes replayed again, the owner's integration disabled: no session ends

`select_replay.py` again, both steps, the car charging at 10.7 kW, one client on each path (the
owner's integration disabled since about 14:58).

- 15:03:13 wrote 33541 = 163 (the select's writes for user defined, charge kept: the mode alone).
  **The word stayed 170 at every read, the status *charging*, the car at 14.8-16.1 A throughout.**
  21203 went 27.8 → 16.0 A within 10 s (15:03:23): the inverter's offer replaced by the user current.
- 15:04:45 wrote 33541 = 160, then 33540 = 170 at once (the select's writes for fast, charge kept).
  Word 170 and status *charging* throughout; 21203 16.0 → 27.0 A within 3 s; car unchanged.
- 108 reads over 3 min 10 s: one word (170), one status (*charging*), the lowest phase current 14.8 A.
- 15:06:24 restore check [170, 160] on a fresh session (nothing to write); 15:06:27 charging, 27.8 A
  offered, 15.2-16.1 A drawn.
- Against 14:54 (the same writes, the owner's integration still polling, the inverter writing off
  then on within 7 s) and the night of 11-16 (163 ↔ 160 ended sessions): today, with one client per
  path, neither direction ended the session. What the owner's integration did between is not known;
  it had the EV charger controls and could run the managed wallbox test.

## 15:09 the stop a fourth time, the owner's integration disabled: the on/off after an off remains

`charge off 120`: snapshot 170, off written 15:09:02 (car at 10.53 kW).

- 15:09:05 (+3 s): status *completed*, 0 A, **the word reads 170**; 15:09:15 (+13 s) 85 again. The same
  on-then-off as at 14:28:30 and 14:46:55, now with the owner's integration disabled. Three times in
  four stops; the car never drew current in it. So it is the inverter's own (or a client other
  than the owner's integration): **a charging-off written while a car charges reads back on for about
  10 s, 3-4 s after the write, then off.** A read-back in that window is not the state.
- 15:11:02 wrote 170; 15:11:07 fresh read 170; the car charging from 15:11:07 (1.0 A one phase), 6.9 kW
  at 15:11:20. Off held 2 minutes; 5 s from the write to current.

## 15:12 the hour through the WiNet-S begins; 15:27 a stop from the app

`managed_wallbox_field.py phase 60` from 15:12:51: the inverter's block at unit 1 through the WiNet-S
(port 502), the wallbox over TLS, every 6 s, read only.

- The maintainer stopped the charge in the iSolarCloud app at about 15:27 (reported 15:28).
- 15:27:46 charging, word 170, 15.4-16.1 A. **15:27:52 status *completed*, 0 A, the word still 170**;
  15:27:58 the same; **15:28:04 the word 85** (off). The car stopped 6-18 s before the inverter's word
  read off. Through the WiNet-S, whose read-back can be stale, so whether the app stops the wallbox
  first and the inverter follows is not settled by this reading.
- The time pair did not move (2026-11-20 / 11-21 00:00 UTC since 14:58): a stop from the app does not
  rewrite it. Mode, user current and grid purchase unchanged.
- The poll was ended at about 15:29 for test 1, after 16 minutes: about 160 rounds through the WiNet-S,
  **no read lost**, the block identical to the cable's readings. Not the hour the plan asks for.

## 15:29 test 1: *Terminiertes Laden* (mode 162) saved in the app

The app's charging mode list (German): *PV-Überschuss Laden*, *Schnellladen*, *Terminiertes Laden*,
*Benutzerdefiniertes Laden*. *Terminiertes Laden* opens *Voreingestellte Bedingungen* with two fields:
*Fahrzeug muss verwendet werden bei* (a departure time; 17:41 entered) and *Ziel für Aufladen (kWh)*
(4,1 entered). The maintainer saved it at about 15:30, charging stopped from the app before.
`tmp/gerd-wallbox-2026-11-14/settings_diff.py` snapshots at 15:29:11 (before) and 15:31:23 (after),
read only; register numbers below.

Inverter holding:

| Register | Before | After | Reading |
| --- | --- | --- | --- |
| 33540 | 85 | 170 | charging **on**, switched on by the save |
| 33541 | 160 | **162** | the mode: 162 is *Terminiertes Laden* |
| 33542 | 0 | **41** | the target, **0.1 kWh** (4.1 kWh) |
| 33543/33544 | 0 / 0 | 34348 / 27392 | u32, low word first: 1795196460 = 2026-11-20 **17:41:00 UTC** -- the local departure time written as if it were UTC (17:41 CET entered) |
| 33545 | 160 | 160 | user current unchanged |
| 33546-33549 | | unchanged | the other time pair (2026-11-20 / 11-21 00:00 UTC) is not this mode's |

So two of the three words between the mode and the user current are this mode's target and departure.

Wallbox (the save started the car at once):

- holding 21203: 0 → 60 (6.0 A); holding 21212 (start/stop): 1 → 0 (start).
- input 21317 status 6 → 3 (charging); phases 5.6 / 5.7 / 5.9 A at 226.6-227.3 V; power 3874 W; pilot
  21312 5.94 V. The minimum three-phase current: no sun (PV about 330 W), the battery at 2.8 % and idle.
- The session energy and start time reset (a new session).

## 15:39 the scheduled mode's target written over Modbus: taken, no effect on the car

`tmp/gerd-wallbox-2026-11-20/target_write.py` (gitignored): snapshot 33542 = 41 on disk, then
33542 = 150 (15.0 kWh) at 15:39:36 on the inverter's cable, the car charging in mode 162 at 6 A.

- **The write was taken**: 33542 read 150 from 15:39:37 to the restore.
- **The car did not change**: 21203 6.0 A, 5.6-6.0 A on each phase, 3868-3880 W, status 3, for 2 min 30 s.
  15 kWh by 17:41 (2 h) would need about 7 kW; nothing moved.
- 15:42:15 wrote 41 back; 15:42:17 a fresh session read 41; the car unchanged after.
- So either the inverter plans the session only when the mode is set (the app's save writes the mode
  as well), or it does not plan by target at all and charges at the minimum. Not settled.

## 15:43 the departure brought forward in the app: no effect on the car either

`watch162.py` (read only, every 5 s, 15:43:14-15:49:11). The maintainer re-saved *Terminiertes Laden*
with the departure at **16:20**, the target still 4.1 kWh.

- **15:43:46: 33543/33544 decode to 2026-11-20 16:20 UTC** (16:20 local, written as if UTC, as before);
  target 41, mode 162, charging on, user current 16.0 A unchanged.
- **The car stayed at the minimum**: 21203 6.0 A, 5.7 / 5.7 / 6.0 A, 3871-3877 W, status 3, through
  15:49:11 (5 min 25 s after the save). By then about 1.2 kWh had gone in since about 15:30; the rest
  (about 2.9 kWh) by 16:20 would have needed about 5.6 kW.
- So in mode 162 at this house (no PV, the battery at 2.8 % and idle) the inverter charged at the
  three-phase minimum whatever the target (15.0 kWh over Modbus) or the departure (16:20 from the
  app). Whether it stops at the target is the next reading: at 3.87 kW, 4.1 kWh from 15:31 is about
  16:35.

## 15:51 a stop from the app, then a tighter window: the car at full power

`watch162.py`, every 5 s from 15:50:58. The maintainer stopped the charge in the app (the app itself
took about 15 s to show it stopped), then saved *Terminiertes Laden* with **16:15** and **1.9 kWh**.

- Stop: 15:51:12 the car *completed*, 0 A, **the word still 170**; **15:51:23 the word 85**. As at 15:27:
  the car stops first, the inverter's word follows about 10-15 s later.
- Save: **15:53:16** word 170, target 19 (1.9 kWh), departure 2026-11-20 16:15 (local as if UTC),
  21203 6.0 A; 15:53:21 status 3.
- Then **the inverter ramped as in fast mode**: 21203 6.7, 8.2, 9.7, 11.1, 12.6, 14.1, 16.3, 17.7 ...
  27.7 A, about 1.5 A every 5 s; the car 5.6-5.9 A at 15:53:26, **15.2-16.1 A and 10.5 kW from
  15:54:04**, its maximum. 1.9 kWh in 22 minutes needed about 5.2 kW: not a computed rate.
- Against 15:39 (target 15.0 kWh written over Modbus) and 15:43 (departure 16:20 saved from the app),
  both made **while a session ran**, where the car stayed at 6 A: this save came **after a stop**, and a
  new session began with it. Taken together: mode 162 decides between the minimum and full power when a
  session starts, and does not revise it mid-session. A hypothesis from three readings, not settled.

## 16:04 mode 162 stops at its target

- The car drew 15.2-16.1 A (10.5 kW) without a change from 15:54:04 to 16:04:28.
- **16:04:33 status *completed*, 0 A**, 21203 still 6.0 A, the word still 170; **16:04:44 the word 85**
  (off), 21203 0. The car first, the inverter's word about 11 s later, as with a stop from the app.
- 16:10:58 the session's energy (21310/21311): **1913 Wh**, against the target 1.9 kWh. **Mode 162 ends
  the session at its target**, 11 minutes before the departure (16:15).
- Left at 16:11: mode **162** (target 1.9 kWh, departure 16:15), charging **off**, the car idle
  (*completed*), user current 16.0 A, grid purchase off. Not the 13:55 state (fast, charging on): the
  maintainer sets the mode back in the app.
