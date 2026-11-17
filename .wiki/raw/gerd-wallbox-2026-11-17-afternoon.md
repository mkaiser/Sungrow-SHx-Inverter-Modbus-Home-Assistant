# gerd's wallbox, the afternoon of 2026-11-17: the EV charger controls from Home Assistant, and the managed test again

Raw note, frozen at ingest. A VPN to the owner's site from 14:25 to about 15:55 (CET), with the owner's consent for
writes while a car charges (gerd's) and the maintainer giving a go per phase. The inverter at unit 1 over its LAN
cable (port 502), the AC22E-01 over TLS (516, unit 248); one client per path: the field tool
(`scripts/dev/managed_wallbox_field.py`) only while the dev Home Assistant was stopped, and the dev Home Assistant
(this branch's working tree) otherwise, logged through its REST API every 2 s (HA's own poll is about 10 s). The car
was plugged in at 80 % (the maintainer) and at 92 % at about 15:50. Register numbers unless "protocol" is said. No
address or serial is in this note.

---

## 14:26 baseline (field tool, read only)

- Car plugged in at 80 % (maintainer).
- Block 33538-33550: `[85, 161, 170, 160, 0, 0, 0, 160, 39168, 27387, 60032, 27388, 85]`
  = charging on (0xAA), mode 160 fast, user current 16.0 A, grid purchase off.
- Wallbox: charging, 15.2 / 15.6 / 16.1 A, 10.61 kW; 21203 = 27.5-27.7 A (the inverter's offer in fast).
- House: PV 334 W, import ~10.7 kW, load ~10.9 kW, battery 13023 = 2.8 %, battery power 0.
- No sun: PV surplus / phase switching not today.

## Log

## 14:30 dev HA preparation (nothing written to the house)

- The dev HA's inverter entry was an old diagnostics-mode entry (no EV charger controls); set to
  devices with HA stopped (maintainer's go).
- A wallbox snapshot from the standalone test of 2026-11-13 09:17 was still in `.storage`
  (protocol 21202=320, 21210=1, 21203=0, 21231=50, not managed). The next managed run would have put
  it back first, **through the wallbox's own registers**: a leftover from a standalone run is
  restored on the wallbox even when an inverter now manages it. Read-only comparison: 21211 = 1,
  21204 = 0, 21232 = 50 match; 21203 = 27.5 A (the inverter's offer, not ours to set). Discarded with
  the maintainer's go (copy kept in tmp/gerd-1117/). Code finding to look at: a non-managed
  leftover on an entry that now has a managing inverter.

## 14:36 dev HA up, inverter entry in devices mode

- EV charger entities on the inverter entry: Wallbox charge on, mode fast, user-defined current 16.0 A.
- Car charging 15.3/15.7/16.1 A, 10.68 kW, 21203 = 26.8 A. HA state logged every 2 s to halog.txt.

## 14:37 step 1: user current 10 A in fast mode, from HA

- Refused by HA before any write: ServiceValidationError `ev_charger_user_current_mode` ("Set the
  mode select to User defined first"), HTTP 400 on the REST API. By design (the inverter refuses
  33545 outside user-defined mode). Nothing written; the car unchanged.

## 14:39 step 2: mode fast -> user defined, from HA's select

- Service call 14:39:05.3-14:39:10.8 (5.5 s; one write, 33541 = 163: `mode_writes` writes no
  charging-on when entering user defined).
- **The session did not end.** Charging word stayed on; status charging throughout; session energy
  rose without a break (2914 Wh at 14:39:02 -> 3204 Wh at 14:40:42, recorder). Car 15.3/15.7/16.1 A ->
  14.7/15.0/15.5 at 14:39:24 -> 15.0/15.3/15.8 A from 14:39:34 (10.45 kW). 21203: 26.8 A (fast, the
  offer) -> 16.0 A at 14:39:54 (~45 s), the user current.
- Against the night of 2026-11-16/17, where 160 -> 163 while charging ended the session: today's house differs
  (battery 2.8 % vs 0.5 % at its minimum; PV ~0.3 kW vs 0; afternoon). Entering user defined does not
  always end a session.

## 14:41 step 3a: user current 8 A (user defined), from HA's number

- Service call 14:41:11-14:41:14, taken (state 8.0). The car followed within 10 s: 7.3/7.4/7.6 A at
  14:41:24, 7.1/7.2/7.5 A (4.95 kW) from 14:41:34. Faster than the 1.4 A / 5 s ramp seen on a start.
- **21203 stayed 16.0 A** for 3+ minutes (to 14:44:32) while the car drew ~7.2 A. On the night of 2026-11-16/17
  21203 equalled the user current (16.0, 10.0); today, after a mid-session change from HA, it keeps the
  value it took on entering user defined. 21203 is not a reliable echo of the user current.
- 21203 went to 8.0 at 14:44:54, **~3 min 40 s after the write**: it lags, it is not fixed.

## 14:45 step 3b: user current 16 A, from HA's number

- Service call 14:45:04-14:45:10. Car ramp: 7.2 A -> 10.0 (14:45:22) -> 12.9 (14:45:32) -> 15.2 A
  (14:45:42), ~1.4 A / 5 s, 10.42 kW. Down (16 -> 8) was within one 10 s sample;, up ramps.
- 21203 reached 16.0 at 14:49:53, **4 min 43 s** after the write. 21203 follows the user current
  minutes late in user-defined mode; the car follows within seconds. Judge by the car.

## 14:50 step 4: mode user defined -> fast, from HA's select

- Service call 14:50:15.3-14:50:16.2 (writes 33541 = 160, then 33540 = 0xAA at once).
- **The session did not end** (watched 90 s+): charging word on, status charging, session energy rising
  without a break (4444 Wh 14:50:02 -> 4766 Wh 14:51:52). Car 14.9/15.3/15.8 -> 15.3/15.6/16.1 A within
  6 s (10.59 kW). 21203 stayed 16.0.
- So today neither 160 -> 163 nor 163 -> 160 ended a session, while on 2026-11-16/17 night both did.
  Whether the select's immediate charging-on helped here cannot be told: nothing tried to end it.

## 14:52 step 5: Wallbox charge off, then on, from HA's switch

- Off: call 14:52:18.3-14:52:19.5; car `completed`, 0 A at 14:52:23 (first sample, <= 4 s).
- On: call 14:53:12.8-14:53:13.7 (after 54 s off); charging 6.8/6.9/7.2 A at 14:53:23 (<= 10 s), 9.9 A
  14:53:33, 12.6 A 14:53:43, 15.5 A 14:53:53 (~40 s to full, ~1.4 A / 5 s). Mode fast, user 16.0 A.

## Phase 1 summary

- Every HA control did what it says; the number refuses outside user defined before writing.
- Mode changes in both directions while charging did NOT end the session today (they did on the
  night of 2026-11-16, battery at its minimum, no PV). The select's open question (charging-on
  overwritten by the inverter's delayed off) could not be provoked; not decided.
- 21203 lags the user current by ~4-5 min in user-defined mode.
- House at 14:54: on, fast, 16.0 A, car charging 15.3/15.6/16.2 A.

## 15:08-15:16 the car cut back by itself, four times (read only, nothing written)

- Fast mode, charging on throughout; one session (session energy rising), status charging, CP 5.9 V.
- 15:08:13 15.4 -> 6.9 A, ramp to 15.2 by 15:08:43; 15:11:13 -> 9.9, 7.8 A, back by 15:11:53;
  15:14:14 -> 5.8 A, back by 15:14:54; 15:15:24 -> 6.8 A, back by 15:15:54.
- Each follows a house load spike (inverter load power, recorder): 16.0 kW at 15:08:07, 15.6 kW at
  15:11:11, ~13 kW around 15:13:4x-15:14, a phase-B meter peak of 5.87 kW at 15:15:18; phase C reaches
  ~5.9 kW in the hour before. Grid import limit is 20 kW, never reached.
- Reads as load management by the inverter (per phase, or the house's fuse), cutting the car to its
  minimum and re-ramping (~1.4 A / 5 s). Cause not confirmed: no register seen that names it.
- 21203 (the offer in fast) moved 27.6 -> 26.9 -> 24.9 -> 18.6 -> 27.3 A over the same span.
- 15:19:52-15:20:14: the wallbox entry unavailable for ~20 s (a lost poll), then back.

## 15:24 phase 2: Diagnosis: start refused by HA

- "answer the diagnosis's questions before an extended test": the wallbox entry's options lack
  "How this inverter is connected", "Is a Modbus proxy in the path?", "Is there another inverter here
  that is not a Sungrow?". Nothing written.

## 15:30-15:42 phase 2: the guard, and why the managed test cannot run from HA here

- Bug found and fixed in the working tree: the testimony guard (bc02eaf) asked a wallbox entry for the
  three inverter questions its options form does not have, so no wallbox entry could start an extended
  test. Now a wallbox entry is answered by the inverter entry that manages it, and asked nothing when
  none does (`testimony.answering_entry`, tests/test_testimony.py).
- The inverter entry's "another inverter that is not a Sungrow?" offers only yes/no; there is no
  "I don't know", though the guard's docstring says every question has one. Answered on the SH8.0RT
  entry: direct_lan, proxy no, other inverter no (maintainer).
- 15:41:55 Diagnosis: start on AC22E-01 (extended). Ran the **standalone** path ("It writes to the
  wallbox's settings"), took a snapshot and finished at 15:41:59 with nothing written (the car
  untouched): no checks allowed. `managing_entry` is None because gerd's inverter entry is on the LAN
  port, where a wallbox never answers, so it never sets `wallbox_elsewhere`. **From HA, a managed
  wallbox is only recognised behind a dongle; gerd's (inverter on the LAN cable, wallbox on TLS 516)
  can never run the managed test from HA.** Todo 3.2's premise needs a link that does not go
  through the dongle probe (e.g. an inverter entry with EV_CHARGER on the same site).

## 15:47 phase 2b: the managed test from the terminal, on this tree's library (restore fix c026b25)

- HA stopped first (one client per path). The tree's library: MODE_SETTLE 20 s, HOLD_SECONDS 60 s.
- Dry run 15:45: AC22E-01 rated 32.0 A; mode fast, user 16.0 A, charging word 170; car 16.1 A.
- Real run: `--leave --yes --start-stop --max-amps 16`.
- 15:45:21-15:48:26, exit 0, every check passed: 6 A -> car 6.0 A after 14 s; 8 A -> 7.6 A after 10 s;
  10 A -> 9.7 A after 10 s; 5 A refused (0x04 on 33544 = 50); stop after 4 s, charging again after 7 s.
  Report device-diagnosis/20261117-144825-managed-wallbox-capability-test.json (gitignored).
- **The restore held** (the fix's first hardware run): restored = true, block 33540 = 170 (on),
  33541 = 160 (fast), 33545 = 160 (16.0 A). Field tool 15:48:45-56: on, fast, 16.0 A; car charging
  15.3/15.7/16.1 A, 10.55 kW. Unlike 2026-11-16 the session did not end after the mode went back.
- Car at 92 % (maintainer, ~15:50).
