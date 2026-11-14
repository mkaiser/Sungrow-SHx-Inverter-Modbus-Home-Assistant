# gerd's wallbox: what went wrong on 2026-11-13, the recovery, and the next tests

The first writing run of the wallbox capability test (`plans/wallbox_capability_tests.md`) left
gerd's AC22E-01 disabled and the car not charging. This plan says what was found, how to get the
car charging again, and what to test next, in which order and how. Every write, with times, is in
`.wiki/raw/gerd-wallbox-capability-test-2026-11-13.md`; what other projects say is in
`.wiki/raw/cross-reference-wallbox-control-2026-11-13.md`.

**No further wallbox write at any site until the changes in section 3 are made and tested.**

## Status, 2026-11-14 (on site at gerd's, a car charging)

Every write and reading: `.wiki/raw/gerd-wallbox-inverter-control-2026-11-14.md`.

- **Recovered.** The owner enabled the charger in the app (holding 21211 0 → 1) and pressed Start
  (21212 1 → 0): the car charged at 16 A.
- **The stop above was broken once**: the capability test's base run and one hand probe wrote the
  wallbox's 21203 (60, then 316 back), only that register, nothing under 6 A. Both writes were
  overwritten by the inverter within seconds; the car never moved.
- **Phase A, partly**: the app's fast charge, PV surplus, user defined (10 A), Stop and Start, read
  at the inverter and the wallbox. Finding 1 holds: the inverter drives 21203, ramping it after a
  start, and the car follows that ramp, which settles 21203 at 0.1 A by behaviour. Not done:
  quantity and time (A3), unplugging (A5).
- **Phase B passed**, over the cable and through the WiNet-S: user current 8 and 12 A followed by
  the car; mode written over Modbus (163 brings the user current, 163 → 160 and 160 → 161 end the
  session); charging on/off (wire 33539) stops and starts a charge with no replug; user current
  5 A refused, 6 A to 33 A taken; 33544 refused outside user-defined mode.
- **Section 3, done**: writes refused unless the wallbox is declared standalone (`Options.standalone`,
  `--standalone`; Home Assistant never declares it), and refused when 21203 moves between two reads
  with nothing written; the enable check never writes 21211 = 0; nothing under 6 A, never 0. Tests:
  `tests/test_wallbox_capability_test.py`, `_cli.py`, `_ha.py`. **Not done**: the battery-SoC
  refusal, the house-level restore check, the inverter block in the snapshot (the test now refuses
  on gerd's wallbox before any of them would matter).
- **Phase D can start** on the inverter's side: `src/sungrow_modbus/hybrid_inverter/ev_charger.py`
  has the block and the write order, read only; the entities are `Todo.md`'s next wallbox item.
- **Phase B as a test**: `src/sungrow_modbus/wallbox/managed_test.py` and its terminal driver
  `sungrow_managed_wallbox_test.py` (user current steps, the 5 A refusal, start/stop, a restore
  of the house), against a fake inverter that behaves as gerd's did. Not yet in Home Assistant.
- **Next on site**: `plans/gerd_wallbox_handoff.md` (how it was left, the rules, the tools, the
  test list).

## 1. Findings

### What happened

- Run 1 (10:00-10:18, cap 16 A, over TLS 516 / unit 248, the wallbox's own entry) wrote, in order:
  the output current 21203 through 6 → 16 → 6 A, then 5 A and 0 (below minimum), **the enable
  21211 = 0 and back to 1** (10:14-10:15), the phase setpoint 21204 = 1, the mileage 21232 its
  own word, then tried to put everything back.
- **The charge was stopped by the disable (21211 = 0, 10:14:06).** The app ends the session at
  10:14. The enable written back a minute later was answered but did not bring it back.
- **No 21203 write changed what the car drew**: 16.1 A at every offer, including 5 A and 0.
- The restore failed: 21203, 21211 and 21232 read back 0 after every write, over two runs and two
  terminal restores (about 20 attempts). Only 21204 came back.
- A single enable write at 11:47, on a fresh session with nothing else connected, was answered and
  moved the status from 8 (disabled) to 2 (standby). The car has not charged since: status 4
  (*suspended by the charge point*) at 12:48, then 6 (*completed*) after every replug, with the
  car's battery empty.

### What the wallbox and the inverter read now (13:45-15:40)

| Register | Before (10-15, 11-01, 11-03) | Now |
| --- | --- | --- |
| wallbox input 21268, remote control status | 1 | **8** |
| wallbox input 21314, start mode | 0 idle, 3 charging | **1, start with EMS** |
| wallbox holding 21211, enable | 1 | **8** |
| wallbox holding 21203, output current | 320 charging, 0 idle | 0 (writes of 320 and 160 answered, not read back) |
| wallbox holding 21232, mileage | 50 | 55552 |
| inverter wire 33540, wallbox charging mode | not read before | 160, fast charge |
| inverter wire 33544, user current | not read before | 160, 16.0 A |

### Why, as far as it is known

1. **The wallbox is managed by the inverter.** It sits on the inverter's RS485 bus (it answers
   through the WiNet-S at unit 3), the inverter's wallbox block reads *fast charge* at 16 A, and
   its start mode reads "start with EMS". By the ioBroker thread (one post, not confirmed
   elsewhere), a wallbox under the inverter's energy management ignores writes to its own
   registers; control goes through the inverter's block at wire 33540-33549. That fits the car
   ignoring every 21203 write. The availability write was **not** ignored.
2. **The TLS path is the same wallbox.** Reaching it at its own address does not make it free:
   today there were two masters, the inverter over RS485 and the test over TLS.
3. **evcc never writes 21211 = 0.** It stops with 21212 = 1, and enables with 21211 = 1, then
   21212 = 0, then the current. The test's enable check wrote the one word nobody else writes.
4. **A write of 50 (5 A) leaves 21203 at 0, and a start zeroes it** (KevinD987, an AC011E): then
   the wallbox stays in status 4 until a current is written. The below-minimum check wrote 50 and
   0. Status 4 at 12:48 fits.
5. **Read-back after a write is not evidence on this wallbox**, on the same session or a fresh
   one: it answered one read four times (duplicate frames, the desyncs at 08:06 and 10:17), and
   21203 reads 0 whenever no car charges.
6. **The battery's *Schnellladung* in iSolarCloud was switched on** (found by the owner): the
   inverter in VPP mode (13050 = 4) with a forced charge (13051 = 0xAA, 10 kW), importing about
   3.6 kW. Twice written back to self-consumption from here, twice re-applied by the cloud; off
   since the owner switched it off (15:13). Who switched it on, and when, is not known, nor whether
   it is connected to the wallbox's state.

7. **The wallbox also pauses on its own for an empty battery.** At 12:49 on 2026-11-13, a minute
   after the status-4 reading (*suspended by the charge point*), the app's *Grund* screen for the
   interrupted charge listed three causes, without saying which applied: the household's
   consumption over its limit (resumes when the load drops); a charge delay required by grid
   rules (resumes when it runs out); and the home battery's SoC under its protection threshold, the
   house served first (resumes once the battery is recharged). The third fits the readings:
   - 2026-11-14 about 09:05, read only: the SBR's own SoC (input 10744, unit 2 through the
     WiNet-S) **11.4 %**, the app 11.1 % at 09:01, just over the minimum SoC (13059) of 10 %;
     maximum SoC (13058) 100 %, backup reserve (13100) 0 %;
   - the inverter's battery level (input 13023) read **1.5 %** at the same time (1.4 % at about
     08:50). Voltage, current, temperature and health in the same block match the app and the
     SBR, so it is not the scale: 13023 looks like the SoC within the window between minimum
     and maximum, (11.4 − 10) / 90 = 1.6 %. One reading, one site; a second pair at a higher SoC
     would tell this from an offset (SoC − minimum);
   - the battery discharged all night (input 5214 +300 to +600 W, positive is discharge, as a
     charge reads negative at mkaiser), stopped at about 08:00 at its minimum, and the house then
     drew from the grid (1.9 kW at 08:44). By 09:00 it charged from PV at about 200 W.
   So the car may stay paused until the battery recovers, whatever the wallbox's registers say.
   Which threshold the app means (the inverter's minimum SoC or a setting of the charger's own) is
   not known.

Not established: what remote control status 8 and an enable register reading 8 mean (no source
documents 8 there), and whether they keep the wallbox from starting.

## 2. Getting the car charging again (on site)

First check the battery's SoC in the app (finding 7): while it is at or near its minimum the wallbox
pauses by design, and none of the steps below can be judged until it has recovered.

In this order; stop at the first that works. Read-only checks between steps are done from here
(TLS, one session, nothing else connected). Every step is done with the car plugged in.

1. **App, charging mode.** In iSolarCloud, set the charger's *Lademodus* from *Schnellladen* to
   another mode and back. This makes the inverter write its wallbox block again (33540).
   Check: the inverter's 33540 changes and returns; the wallbox goes to status 3; current flows.
2. **App, local access.** iSolarCloud's local access (Bluetooth or the charger's own WLAN, on the
   login screen), the charger's parameters: anything named enable, availability or remote control,
   set to enabled; working mode as it was (if shown). This is the fix reported in evcc #7104 for a
   wallbox left disabled by Modbus. Check as in 1.
3. **Power off at the breaker, 40 s or more, then replug.** Done once already (before 11:47) while it was
   disabled; worth repeating after 1 or 2, not before.
4. **Installer or Sungrow support**, with the readings of section 1. A factory reset only on their
   advice: it loses the commissioning and the link to the inverter.

**Not done from here without the maintainer's word**: writing the inverter's 33540 (charging mode)
or the evcc sequence on the wallbox (21211 = 1, 21212 = 0, 21203 = 160). Either is a further write
on a device whose control is not understood.

**Done when** the car charges at its usual current on a plain replug, the app shows the charger
enabled, and these read as before: wallbox input 21268 = 1, holding 21211 = 1, input 21317 = 3
while charging, holding 21203 = 320 while charging. Mileage per kWh is set back in the app (5.0).

## 3. Changes to the test before it writes again

| Change | Why |
| --- | --- |
| **Refuse wallbox-register writes on a wallbox managed by an inverter.** Detect it from the inverter's wallbox block (33540 not 0 / not absent) and the wallbox's start mode; if either cannot be read, refuse. | Finding 1 and 2: the writes are ignored or fight the inverter. |
| **Drop the disable from the enable check.** Never write 21211 = 0. If enable is tested at all, only on a standalone wallbox, only as evcc does it (21211 = 1 first, then start), and stop with 21212. | Finding 3: the one write that broke the house. |
| **Below minimum: never write under 60 (6 A), and never 0.** Test the floor by refusal only if a source says it is refused; otherwise leave it out. | Finding 4. |
| **After any start, write the current.** | Finding 4. |
| **Judge by behaviour only**: status, phase currents, control pilot. A read-back of a holding register is recorded, never a verdict, on either path. | Finding 5. |
| **One client.** The run refuses to start while any other client is connected that it knows of (Home Assistant's own polling held off, as now); the terminal driver says so in its question. | The 11:47 write took only with nothing else connected. |
| **Restore checks the house, not the register**: the restore is done when the status is what it was (charging if it was charging) and the enable reads 1 on a fresh session, and it keeps trying (never deadlined) with the evcc order. If it cannot, it says what to do on site (section 2). | Today's restore "failed" on read-backs while the charge point was the real problem. |
| **Snapshot also the inverter's wallbox block and EMS mode** (read only), so a run can show what the inverter was doing. | Finding 1 and 6. |
| **Refuse to start while the battery is at or near its minimum SoC** (the SBR's own 10744 against 13059; 13023 near 0 if the SBR cannot be read), and record both in the snapshot and every step. | Finding 7: the wallbox pauses by itself then, so no step can be judged. |
| Tests in `tests/test_wallbox_capability_test.py` against a fake port that ignores writes (slave mode), drops a session, answers a read twice, and zeroes 21203 on start. | Each of today's failures as a test. |

## 4. The test plan

Each phase needs the one before it to have passed. Every phase: gerd's consent for that phase,
watched live, Home Assistant's polling held off, one client, a snapshot flushed before the first
write, the restore never skipped.

### Phase A: read only, who controls the wallbox (no writes)

Goal: learn to tell an inverter-managed wallbox from a free one, and what the registers do in each
state. Over TLS (wallbox) and the WiNet-S (inverter), one read per minute.

| Step | Owner does | Read | Expect / learn |
| --- | --- | --- | --- |
| A1 | nothing, no car | wallbox 21263 (holding), 21268, 21314, 21317, 21203, 21211; inverter wire 33539-33549, 13050-13052 | the idle baseline |
| A2 | plugs the car in | the same, every 10 s for 2 min | who starts the session: start mode, 33540 |
| A3 | while charging, switches *Lademodus* through each mode in the app (fast, PV surplus, quantity/time, user defined), 3 min each | the same, plus phase currents | the meaning of each 33540 value; whether 33544 follows a current set in the app; whether 21203 ever changes |
| A4 | sets a current in the app's user-defined mode (e.g. 10 A) | the same | that the car follows 33544 (the path a controller should use) |
| A5 | unplugs | the same | the end-of-session values (start mode, 21203) |

Settles: the meaning of 33540-33549 on this firmware (until now one forum post), start mode 3,
remote control status 8, and a reliable "managed by the inverter" signal for section 3.

### Phase B: control through the inverter (writes to the inverter, not the wallbox)

Only if phase A shows the car follows the inverter's block. Through the WiNet-S (behaviour is the
only evidence there) or the inverter's LAN port at unit 1 if it answers then.

| Step | Writes | Judge by | Restore |
| --- | --- | --- | --- |
| B1 | 33540 = 163 (user defined), 33544 = 100 (10 A) | the draw follows to 10 A within 60 s | 33544, then 33540, to the snapshot |
| B2 | 33544 = 60, 80, 120, 160 in turn | the draw follows each; time to follow | as B1 |
| B3 | 33540 back to 160 (fast) | the draw returns to the car's maximum | — |

Settles: whether the integration can offer a charging current number for an inverter-managed
wallbox, and through which registers. Nothing in phase B writes the wallbox's own registers.

### Phase C: the wallbox's own registers, standalone only

Only on a wallbox that is not managed by an inverter: either another owner's standalone unit, or
gerd's only if he decides to run it standalone (working mode EMS in the wallbox's own interface,
off the inverter's bus, as evcc requires). Not on gerd's current installation.

| Step | Writes | Judge by |
| --- | --- | --- |
| C1 | 21203 = 100 while charging | the draw follows to 10 A |
| C2 | 21212 = 1 (stop), then 21212 = 0 (start), then 21203 = 160 | stop seen (status not 3), start seen, current after the start |
| C3 | 21204 phase, only with the charge stopped by 21212 | input 21270 follows; the car resumes on one phase |
| C4 | 75 s of silence | what the wallbox falls back to |

No 21211 write, no current under 6 A, no 0.

### Phase D: the integration

Only after B (and C where it ran): entities through the write table for what was measured, a
charging current number on the path that phase B or C confirmed, and the "managed by the inverter"
signal shown on the wallbox's device page. Not before.

## Verification

- `make check`; the new fake-port tests in section 3 fail on today's procedure and pass after.
- Each phase ingested into the wiki (wallbox page, `doc/wallbox_registers.md`, `log.md`) before the
  next.
