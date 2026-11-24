# gerd's wallbox, 2026-11-24: 0.1.0a54 in his own Home Assistant, the car plugged in

Over the tunnel from the devcontainer; times CET. Owner's consent to test everything, passed on by the
maintainer the same morning. Nothing in this session reads the devices beside his Home Assistant.

## As found, 10:45

- Home Assistant 2026.11.2 with 0.1.0a51; both entries loaded and idle, auto repeat off on both.
- Inverter: charging off, mode fast, user current 16.0 A, window start 00:00, grid purchase **on**; battery
  26.7 %, minimum 10 %, PV 2435 W, house 525 W; restart permission off.
- Wallbox: car connected, status *completed*, pilot 8.93 V, session 18133 Wh, lifetime 938353 Wh, three phase,
  offered 16.1 A, setting 0. Leave to write on, not standalone, highest current 32 A, named as managed.

## 10:56, 0.1.0a54 installed

Through the Marketplace (723c279), the a51 folder kept; restarted. Both loaded, no error in the log.

- **Finding**: the wallbox entry set up 15 s before its inverter's, and *Diagnosis: test summary* read `1/6` until
  its next update, the results command `1/9`: the three writing checks need the managing entry, and nothing tells
  the sensor when that has loaded.

## 10:57 charging on from Home Assistant, after a completed session

- *Extended test (auto repeat)* started on the wallbox entry, then *Wallbox charge* on (a service call). Status
  *completed*, then *suspended by the vehicle* at 10:57:49, **charging 10:58:00** (23 s at most after the write),
  full power 10:58:21 (10.6 kW, 15.1 A, three phase), no replug. The session counter restarted from 0.
- Auto repeat then waits: *the owner changed the wallbox's charging; not before 11:57* (`OWNER_QUIET_EV`, an hour).
  As built: a car started from Home Assistant cannot be tested by auto repeat in its first hour.
- The load read 11.4 kW with the wallbox at 10.6 kW (it includes the wallbox); the battery gave what it could.

## 11:00:54-11:03:19 the managed test from Home Assistant: its first writing run there

*Extended test* (single run) on the wallbox entry, a car charging at 15.2 A. Exit 0, 5 steps, **all three passed**:

| Check | Verdict |
| --- | --- |
| user current | 6, 8, 10 A; at 10 A the car draws 9.6 A after 8 s |
| floor | 5 A refused, 0x04 (FC 6) |
| start/stop | stopped after 1 s, charging again after 12 s, no replug |

- Put back: mode fast, 16.0 A, charging on, grid purchase on; the car at 15.2 A, 10.6 kW at the end and after.
  *Controls held* on from start to end. The session counter restarted (147 Wh at 11:03): **a stop and start is a
  new session**, as was the charging on after *completed*.
- The wallbox's entities stand still during the run (polling held), which is what a plausibility tick then misses.
- **To look at**: *Charging current setpoint* (21203) reads 0.0, last updated at setup (10:56:19), through 12 minutes
  of charging; the `management` inference, fed from it, says *unknown*.

- The setpoint is in the slow block (`SungrowWallboxCoordinator.SLOW_EVERY`, every 30th poll, 5 min), while the
  inference is fed each minute: a steady 5 min of the same stale value reads as a setting that held still.
- 11:05, block by the proxy, charging in fast: 33538 85, 33539 161, 33540 170, 33541 160, 33545 160, 33550 170
  (33538/33539 as on 2026-11-14).

## 11:06 PV surplus in sun: grid purchase off, then mode PV surplus (tests 5 and 6)

- 11:04:20 grid purchase off in fast: the car stays at 10.7 kW. 11:04:41 mode PV surplus (select): the session ends
  within 10 s (*suspended by the charge point*, then *completed* 11:05:01); the charging word reads off by 11:05:42.
  PV 2.35 kW, house 0.6 kW, battery 24 % now taking 1.7 kW. The select had written charging on straight after the mode (`mode_writes`): it read **on** until 11:05:30 and **off** at 11:05:42, so **the inverter overwrote it about a minute after 160 -> 161**. This is the delayed off of plan section 10, seen from Home Assistant, one client per path.
- 11:08:46 charging on written again, in PV surplus, grid purchase off.
- **11:09:20 one phase**: *charging*, A 5.4 A, B and C 0 A, 1240 W (PV 2.33 kW, house without car about 0.8 kW, the battery
  no longer charging). *Completed* at 11:09:30 after 3 Wh, the word off by 11:09:51 and the battery charging again.
- 11:10:14-11:13:06, the block read every ~2.5 s through the proxy (one HA press, *charging on*, at 11:10:14):

| Time | Seen |
| --- | --- |
| 11:10:24 | *charging*, 5.4 A on A only, 1240 W; PV 2.27 kW |
| 11:10:32 | the meter sees 1.3 kW leave: the car no longer draws; 11:10:42 the word **off** (85), nothing written |
| **11:11:30** | the word **on (170) by itself**, PV 2.25 kW, house 0.6 kW; 11:11:35 *charging*, one phase |
| 11:12:02 | export 1.1 then 1.5 kW (the car stopped); 11:12:05 the word **off by itself**; 9 Wh in the session |

- So **in PV surplus without grid purchase the inverter drives 33540 itself, both ways**; the switch follows it.
  33538 = 85 and 33539 = 161 throughout one-phase charging, off and on: **neither is the phase word**. Nothing else
  in 33538-33550 moved but 33540.
- What ended the two one-phase sessions within 10 and 30 s, with surplus left (PV less house 1.6 kW against 1.24 kW
  drawn), is not in these registers: the draw ends 3-10 s before the word goes off.
- **11:13:28 grid purchase on, still PV surplus**: nothing for 60 s (word off). 11:14:31 charging on: *charging* in 5 s,
  **three phase, 5.6/5.6/5.9 A, 3.9 kW** steady to 11:17, PV 1.6-2.2 kW, house 0.6 kW, the meter near 0 (the battery gives the
  rest). So 33550 decides: off, one phase out of surplus, the word cycled by the inverter; on, three phase at the
  6 A minimum whatever the surplus.
- 11:17 grid purchase off during that charge:
  the car keeps 5.6 A for 18 s, stops at 11:17:34, the word off at 11:17:45, and stays so to 11:21 (PV 2.1 kW, house
  0.6-0.8): **switching it off ends a three-phase session; it does not switch it to one phase**.

## 11:21 back to fast, charging on: a steady charge for the readings' checks, then fast <-> user defined

Defects found by reading the code beside the data (`diagnosis.py`, `_async_observe_wallbox`):

1. *inverter load includes the wallbox* can never settle on a wallbox entry of its own: the load is read only where
   `inverter_tests`, which is False there, though a managing inverter entry is known. Auto repeat then never ends.
2. `Management` counts its "30 polls, five minutes" from a feed of one a minute whose setting (21203) is re-read every
   five: 30 stale repeats can say *standalone* of a managed wallbox in a steady fast charge.
3. The mode select writes charging on straight after the mode; after 160 -> 161 the inverter took it back about a
   minute later (11:05).
4. The wallbox summary sensor is not refreshed when its managing inverter's entry loads after it.
5. Any control of the EV block, a plain charging on included, holds auto repeat off for an hour, about as long as a
   session lasts: a car started from Home Assistant is hardly ever tested by it.

- 11:21 fast + charging on from *completed*: drawing 16 s later, 10.6 kW from 11:22:18. 21203 (the offer) 31.8 A in fast.
- 11:28: `management` says **managed** (it saw 21203 move across the modes); defect 1 shows: **0 of 3 power steps** after
  at least six steps over 1 kW.

## 11:34-11:42 the mode select, fast <-> user defined, a car charging at 15 A

Four changes from Home Assistant two minutes apart (11:34:24 user defined, 11:36:29 fast, 11:38:35 user defined,
11:40:40 fast), one client, the battery 17 -> 10 %: **no session ended**, the counter ran on (2216 -> 3654 Wh), the word
on throughout. To user defined the first time the current dipped to 10.7 A and was back at 15 A in 20 s. 21203 reads
the user current (16.0) in user defined and stays there after.
At 11:42 the battery reaches its 10 % minimum with the car at 10.7 kW: watched on.
- Correction: the *battery level* (13023) counts within the min-max window, so 10 % there is not the minimum: at 11:53 it
  reads 2.4 %, the car still at 10.7 kW in fast, 5600 Wh in the session. The minimum is near 0.

## 12:06-12:10 test 4: the same mode changes from iSolarCloud (the maintainer), the car charging

- 12:06:34 fast -> user defined, 10 A, saved in the app: the car 15.3 -> 9.2 A, **the session goes on**, word on, three minutes
  without a delayed stop. 33541 163, 33545 100; the window 33546-33549 unchanged by this save (54144/27396, 9472/27398).
- **12:09:4x user defined -> fast in the app: the session ends** (*completed* by 12:09:52, 8228 Wh), the word 85 at 12:10:34, the
  user current left at 10.0 A. The same change from Home Assistant at 11:36 and 11:40 kept the car charging: the
  select writes charging on straight after the mode, the app does not.
- The battery level stood at 0.6 % from about 11:55 to 12:06 with the car at 10.6 kW in fast and the rest from the
  grid: **the minimum does not end a fast charge**.
- To 12:11:25 the car did not resume by itself after the app's change to fast (no Start pressed).

## 12:12-12:14 put back

User current 16.0 A from Home Assistant (user defined, written, fast again; charging stayed off). Read back through the
proxy at 12:14: 33540 85, 33541 160, 33545 160, 33550 170: charging off, fast, 16.0 A, grid purchase on, as found at 10:45.
The wallbox entry's entities were unavailable for one poll at 12:12:22. Left: the car plugged in, battery about 1 %,
0.1.0a54 installed, auto repeat off on both entries, readings' checks 8 of 9 (defect 1 holds the ninth).

## 12:19 unplug and replug (test 7), round 1: charging off, fast, grid purchase on, Plug&Play on

The block through the proxy and the wallbox through his Home Assistant, every ~3 s. Nothing written by us.

| Time | Wallbox | Inverter word 33540 |
| --- | --- | --- |
| 12:19:07 | *completed*, pilot 8.93 V, session 8228 Wh, start mode *start with EMS* | 85 off |
| 12:19:34 | unplugged: *idle*, 11.9 V, counter still 8228 | 85 |
| 12:20:05-12:20:28 | the entry *unavailable* (as one poll at 12:12:22) | 85 |
| 12:20:28 | *idle*, counter **0**, start mode *stopped* | 85 |
| 12:21:07 | replugged: *idle*, 9.02 V | 85 |
| **12:21:10** | *idle*, car connected | **170, by itself** |
| **12:21:17** | *charging*, 5.5 A, 4.05 kW, start mode *unknown* | 170 |

So with charging off, **a replug starts a charge by itself within 10 s**: the inverter switches its own word on.
Home Assistant's switch still read off at 12:21:17.
At 12:21:37 the switch reads on; 12:21:46 14.9 A, 10.3 kW. Mode, 16.0 A and grid purchase kept. Not separated: whether
Plug&Play (21298, on) is what starts it.

## 12:24 round 2: out and in while charging

The maintainer reports the plug cannot be pulled while the car charges; how it came free is theirs to say.
12:22:59 a dip to 7.4 A and back to 15.2 A in 30 s, plug in. Then, nothing written by us:

| Time | Seen |
| --- | --- |
| 12:24:07 | *charging* 15.2 A, word 170 |
| 12:24:26-28 | pilot **11.9 V** (no car), *suspended by the charge point*, 471 Wh; word **85** in the first read after |
| 12:24:36 | *idle*; Home Assistant's switch off at 12:24:34 |
| 12:25:10 | word **170 by itself** (the entry still shows no car: its poll is 10 s old) |
| 12:25:17-20 | *charging*, 6.7 A, counter restarted (6 Wh); the switch on at 12:25:34 |
| 12:25:59 | 15.2 A, 10.55 kW; unchanged at 12:27 |

So **losing the car switches the word off at once, and its return switches it on and charges within about 10 s**. The
mode, 16.0 A and grid purchase are kept. The counter restarts with the new session.

## 12:30 round 3: Plug&Play switched off in the app, the charge stopped there first

- 12:29:58 *completed*, word 85 at 12:30:05 (the maintainer, in iSolarCloud). 21298 read **off** at 12:34:30 (its 5-min read).
- 12:31:51 unplugged (*idle*, 11.9 V; word 85); **12:33:00 replugged: *standby*** (9.02 V), not *idle* as in round 1. To
  12:36:14, 3 min 14 s: **no charge, word 85**, counter left at 794. The owner at the wallbox sees it **blink white**.
- So **Plug&Play (21298) is what starts the charge on plugging in**: on, the inverter's word goes on by itself within
  3 s; off, nothing happens.
- **12:36:30 *Wallbox charge* on from Home Assistant, Plug&Play still off**: *standby* -> *charging* at 12:36:42, 15.2 A at
  12:37:10, start mode *start with EMS*. A dip to 6.6 A at 12:37:21 and back up, plug in (as at 12:22:59).
- The maintainer was not on site; gerd at the car.
- The LED, as gerd sees it: **blinking white in standby** (plugged in, not started), **green while charging** (12:38).
- 12:44:38 charging off from Home Assistant; *completed*, 0 A by 12:44:56. Read through the proxy at 12:45: 33540 85,
  33541 160, 33545 160, 33550 170, as found. Plug&Play still reads off at 12:44 (read every 5 min); asked to be put on.
- **Switching Plug&Play on with the car plugged in starts a charge by itself**: after the off of 12:44, the maintainer put it
  on in iSolarCloud and the car was *charging* from about 12:46:15 (6.5 A rising), nothing written by us; switched off
  again from Home Assistant at 12:46:35 (the car at 0 A by 12:47:26, word 85).
- 12:50 or before: Plug&Play (21298) reads on again in his Home Assistant; everything as found at 10:45.

## 12:51 left for the afternoon, on the maintainer's word: PV surplus, grid purchase off, charging on

Set from Home Assistant, to see whether one-phase surplus charging holds; his Home Assistant's history is the record.
As found was fast, grid purchase on, charging off.
- 12:51:57 the word on after our press, off by itself by 12:52:47: PV 1.3 kW, house 0.3-0.4 kW, too little. Defect 3 above
  is therefore not settled as one: in this mode the inverter drives the word anyway, and with 1.6 kW of surplus from
  11:05 to 11:08 it had not put it on again, where from 11:10:42 to 11:11:30 it did.
