# gerd's wallbox, the first writing capability test, 2026-11-13

Run from the maintainer's dev Home Assistant over a VPN, on the wallbox's entry of its own (TLS 516,
unit 248), with the owner's consent to any test while charging. Options: the test may write, highest
charging current (`wallbox_max_amps`) 16 A. Mode *Extended test*, one run, watched. The owner runs no
evcc. No serial, no address. Times are CET (UTC+1). Sources: the run's ledger block (Home Assistant
store `wallbox_capability_ledger`), the kept snapshot (`wallbox_capability_snapshot`), the Home
Assistant log, and a screenshot of the iSolarCloud app taken by the owner at 10:32.

## Before the run

A car was plugged in and charging from about 09:56: 10.5 kW, 15.1 / 15.4 / 16.0 A on the three
phases, 227 V, control pilot 5.95 V, available current (input 21322) 16.0 A.

| Reading | Register | Raw word | Decoded |
| --- | --- | ---: | --- |
| Rated current | input 21263 | 320 | 32.0 A |
| Output current setting | holding 21203 | 320 | 32.0 A at 0.1 A |
| Phase setting | holding 21204 | 0 | three phase |
| Charger enabled | holding 21211 | 1 | |
| Start/stop | holding 21212 | 1 | |
| Mileage per kWh | holding 21232 | 50 | |
| Charging status | input 21317 | | charging |

While the car charged, 21203 read 320. Home Assistant showed 0.0 A until its next slow-tier read: an
old reading, not the register.

## Run 1, 10:00:00 to 10:18:15

Exit code 5: settings not put back. Steps, with the run's own verdict and detail:

| Step | Verdict | Detail |
| --- | --- | --- |
| output current 6, 8, 10 A | could not tell | the car draws 16.1 A at every offer: "it may limit itself" |
| current follow, 6 → 16 → 6 A in 2 A steps, ~60 s each | could not tell | the draw stayed 16.1 A at every step, up and down; at 16 A it matched in 0.24 s |
| below minimum | the wallbox did as it was told | 5.0 A and 0 were both taken, and the car kept charging at 16.1 A |
| above rating | skipped | the cap (16 A) is below the rating (32 A) |
| available current | could not tell | 21322 stayed 16.0 A; it is neither the setting, the setting + 1 A nor the draw (offsets 10, 8, 6, 0 A) |
| start/stop | skipped | 21212 reads 1 while a car charges, so its polarity is unknown |
| enable | could not tell | "disabled: False, back: False" within the run's 60 s |
| phase | could not tell | 21204 written 0 → 1; the actual mode stayed 0 (three phase) |
| phase while charging | skipped | 21212 does not read as running |
| mileage | read back is not the word written | wrote 50, then read 0 |
| fallback (75 s of silence) | skipped | the output current could not be put back first |

Restore, 5 attempts each, read back on the same session (no fresh session from Home Assistant):

| Register | Original | Put back | Detail |
| --- | ---: | --- | --- |
| holding 21203 | 320 | no | read 0, wanted 320 |
| holding 21204 | 0 | yes | |
| holding 21211 | 1 | no | read 0, wanted 1 |
| holding 21232 | 50 | no | read 0, wanted 50 |

Log: at 10:17:22, during the silence, three "unexpected response" frames were discarded (a desync on
the TLS session). At 10:18:15: "could not put 21232, 21211, 21203 back; the snapshot is kept". At
08:06 a single poll had taken 10 s and desynced the same way.

The wallbox's status read *disabled* from 10:18:15 and the car stopped (0 A, control pilot 8.9 V:
connected, not charging).

## Run 2, 10:20:02 to 10:20:54

Started to put the kept snapshot back first. The same three registers again read 0 after their
writes; the run refused to go on (exit 5, "the wallbox settings of an earlier run are not back"), and
the snapshot stays kept. The status stayed *disabled*.

## The owner's app, 10:32

iSolarCloud shows the charger *Deaktiviert*, 0.00 kW. Its last session: 3.26 kWh, "13/11 10:14 -
13/11 10:14". Mileage per kWh 0.0. Lifetime 776.49 kWh. Charging mode *Schnellladen*. The app showed
the owner no way to enable the charger again.

## What this says, and what it does not

- The disable write (21211 = 0) took effect: the app ends the session at 10:14, when the enable step
  ran, although the run's own 60 s did not see the status change. Writing 1 back, ten times over two
  runs, did not enable it again.
- No offer from 6 A to 16 A, nor 5 A, nor 0, changed what the car drew. 21203's scale is not settled
  by this run: either the wallbox ignores the setting in this mode, or it acts on it only later.
- Every read-back after a write gave 0, including registers that were not changed. On the same
  session, after a desync, that is not evidence of what the registers hold.
- The phase step (from 10:16) runs only with nothing flowing. By the app, the session had ended at
  10:14, so it most likely ran with the car stopped by the disable. The actual mode did not change,
  and 21204 is back at 0.

## Recovery from a fresh session, 10:44 to 10:59

Home Assistant stopped, the kept snapshot put back with the terminal driver's `--restore`
(`--timeout 10`), on a TLS session of its own. Exit 5 after 15 minutes: holding 21232, 21204, 21211
and 21203 all "NOT put back", including 21204, which had read back as its original after run 1.
A first attempt at 10:37 was cut off after 5 minutes by a shell timeout. A read-only dry run right
before and right after answered at once: status disabled, setting word 0, the car drawing 0 A. The
wallbox answers reads on a fresh session and, while disabled, answers no write.

## Re-enabled, 11:47

The owner switched the wallbox off at its breaker for 40 s: it stayed disabled (red LED, a short white
blink on plugging in, the app *Deaktiviert*), so the disable is stored. The VPN had dropped meanwhile
and came back after a restart.

A probe of its own, on a fresh TLS session with nothing else connected, read holding 21203 0, 21204 0,
21211 0, 21212 1, 21232 55552 (0xD900), and input 21317 8 (disabled). The first read was answered
four times over (three duplicate frames with the same transaction id discarded). One write of
21211 = 1 (function 06) was answered without an exception; on a fresh session after it, 21317 read 2
(standby), and holding 21211 read 8, twice, on two sessions. A dry run after it: status standby,
setting word 0, the car drawing 0 A.

Why this write took and the twenty before it did not is not known. The difference: no other client
connected (Home Assistant stopped), one write on a session that had read before it, and a session
opened after the VPN restart.

## Every write of the day, in order

Register numbers as in `doc/wallbox_registers.md` (the wire address is one lower). Times are from the
run's step sensor (polled every 10 s), the Home Assistant log and the shell. Which writes a check
makes, and in what order, is from `src/sungrow_modbus/wallbox/capability_test.py`; the run recorded
no refused or lost write (`refusals` empty), so each write below was answered.

Snapshot at 10:00, before the first write: 21203 = 320, 21212 = 1, 21211 = 1, 21204 = 0, 21232 = 50.

| # | Time | Who | Register | Words written | Why |
| --- | --- | --- | --- | --- | --- |
| 1 | 10:00-10:01 | run 1, output current | 21203 | 60, 80, 100 | 6, 8, 10 A, 25 s each |
| 2 | 10:01-10:11 | run 1, current follow | 21203 | 60, 80, 100, 120, 140, 160, 140, 120, 100, 80, 60 | 6 → 16 → 6 A, up to 60 s each |
| 3 | 10:12-10:14 | run 1, below minimum | 21203 | 50, then 0 | 5 A, then nothing; the car kept charging after each, so no 6 A resume word was written |
| — | — | run 1, above rating, start/stop, phase while charging | — | none | skipped (cap below rating; 21212 reads 1 while charging) |
| 4 | 10:14:06 | run 1, enable | 21211 | **0** | disable; status 8 was not seen within 60 s |
| 5 | ~10:15 | run 1, enable | 21211 | 1 | enable; charging was not seen within 60 s |
| 6 | 10:16 | run 1, phase (idle only) | 21204 | 1 | single phase; ran because the status was already one of 1, 2, 6, 8, i.e. the car had stopped; the actual mode stayed three phase |
| 7 | 10:17 | run 1, mileage | 21232 | 50 | its own word; read back 0 |
| 8 | 10:17 | run 1, fallback, put the setting back first | 21203 | 320 × 5 | read back 0 each time, so the silence was skipped |
| 9 | 10:17-10:18 | run 1, restore (newest first) | 21232, 21204, 21211, 21203 | 50 × 5, 0 × 1, 1 × 5, 320 × 5 | only 21204 read back as written |
| 10 | 10:20 | run 2, leftover restore | 21232, 21204, 21211, 21203 | 50, 0, 1, 320, up to 5 each | none read back; refused to go on |
| 11 | 10:37-10:42 | terminal `--restore`, fresh TLS session | same four | | cut off by a shell timeout before it reported |
| 12 | 10:44-10:59 | terminal `--restore`, fresh TLS session | same four | up to 5 each | none read back |
| 13 | 11:06-11:10 | terminal `--restore`, enable only | 21211 | 1 × 5 | none read back |
| 14 | 11:47 | single write, fresh TLS session, function 06 | 21211 | 1 | answered; status 8 → 2 |
| 15 | 12:49 | single write, fresh TLS session, function 06 | 21203 | 320 | answered; read back 0; status was already 6 |
| 16 | 13:56 | single writes through the WiNet-S, inverter unit 1 | inverter holding 13051, 13050 | 0xCC, then 0 | stop the forced charge, self-consumption |
| 17 | 14:33 | the same again | inverter holding 13051, 13050 | 0xCC, then 0 | after it had gone back to 4 / 0xAA |

## What stopped the charging

**Write 4, holding 21211 = 0 (disable), at 10:14:06.** The app ends the last session at 10:14
(3.26 kWh). None of the 21203 writes before it changed what the car drew, down to 0: it drew 16.1 A
throughout. Start/stop (21212) was never written. The run's own 60 s wait did not see status 8;
Home Assistant first showed *disabled* at 10:18:15, when its polling resumed.

## Why it does not charge now: what the registers say (open)

A full read-only dump at about 13:45, against gerd's own document of 2026-11-03 (charging then):

| Register | 2026-10-15 / 11-01 / 11-03 | Now |
| --- | --- | --- |
| input 21268, remote control status | 1, 1, 1 | **8** |
| input 21314, start mode | 0 idle / 3 charging | **1, "start with EMS"** |
| holding 21211, enable | 1 | **8** |
| holding 21203, current setting | 320 (charging); 0 idle on 11-06 | **0** |
| holding 21232, mileage | 50 | 55552 |
| holding 21233, minimum current | 6 | 6 |
| holding 21204, phase setting | 0 | 0 |
| input 21322, available current | 160 | 161 |
| inverter holding 13050 / 13051 | 0 / 0xCC (10-13, 11-01, 11-03) | **4 (VPP) / 0xAA, 10 kW** before writes 16 and 17 |

After the enable at 11:47 the car was replugged: status 4 *suspended by the charge point* at
12:48, then 6 *completed* from about 12:49, also after a fresh replug at 13:02, with the car's
battery empty. Not established which of these is the cause:

1. **The current setting is 0.** It was last written 0 at 10:13-10:14 (write 3), and no write of
   320 since has read back. *Suspended by the charge point* is what a wallbox offering under 6 A
   shows; during the run the setting had no effect on the session already going, but it may on a
   new one.
2. **The wallbox is now under remote (EMS) control.** Remote control status 8 and start mode
   "start with EMS" were never seen before; in that mode a session may wait for a start from an EMS
   (21212) and a current (21203) that nobody sends.
3. **The inverter was in VPP mode with a forced charge**, never seen before at gerd's; set again
   within 7 minutes after write 16, by something outside this session (no inverter write of today's
   runs sets 4; the inverter test only ever sets 2). When it began is not known: today's dev Home
   Assistant read the inverter but recorded no history of it. Whether it and the wallbox's EMS start
   mode share a cause (iSolarCloud's energy management, a tariff service) is not known.
4. **Holding 21211 reads 8** where the documented values are 0 and 1, on fresh sessions, twice.

## The inverter's VPP forced charge: found, 15:10

The owner found the battery's *Schnellladung* (fast charge) switched on in iSolarCloud. That
accounts for 13050 = 4 (VPP) with 13051 = 0xAA at 10 kW, and for it coming back after writes 16 and
17: the cloud re-applied it. Who switched it on, and when, is not known. Whether it also put the
wallbox into "start with EMS" (input 21314 = 1, input 21268 = 8) is not established.

## The inverter's wallbox block, 15:40

Read only, through the WiNet-S at unit 1, holding wire 33539-33549: 85, **160**, 0, 0, 0, **160**,
57584, 27181, 57584, 27181, **85**. Read with the ioBroker thread's map
(`cross-reference-wallbox-control-2026-11-13.md`): wire 33540 = 160, the wallbox's charging mode is
*fast charge* (the app's *Schnellladen*); wire 33544 = 160, a user-defined current of 16.0 A;
wire 33549 = 85, no surplus from the grid. So this wallbox is managed by the inverter's energy
management, which by that source makes writes to the wallbox's own registers ineffective: consistent
with the car drawing 16.1 A whatever 21203 was written during run 1, and with input 21314 reading
1, "start with EMS". The availability write (21211 = 0) was not ignored.
