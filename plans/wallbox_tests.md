# Wallbox tests: what is known, what the capability test covers, what is next

The one plan for testing and controlling a Sungrow wallbox: the facts measured so far, the rules for
any write, which checks the capability tests run on their own and which need a person on site, and
the next session at gerd's (SH8.0RT with an AC22E-01). gerd allows every test while a car charges.

Where a session left off: `plans/wallbox_session_handover.md`. Device facts are on the wiki's [wallbox](../.wiki/wiki/entities/device-wallbox.md) page (section
*Under an inverter's energy management*) and in `doc/wallbox_registers.md`. Every write and reading,
with times, is in the raw notes:

- `.wiki/raw/gerd-wallbox-capability-test-2026-11-13.md`: the standalone test on the managed wallbox,
  which left it disabled (no wiki source page yet);
- `.wiki/raw/gerd-wallbox-inverter-control-2026-11-14.md`: control through the inverter;
- `.wiki/raw/cross-reference-wallbox-control-2026-11-13.md`: what evcc, ioBroker and others say.

Register numbers below are register numbers; the protocol address is one lower.

## 1. Two kinds of wallbox

A wallbox on a hybrid inverter's bus, set up as the inverter's EV charger in iSolarCloud, is
**managed**: the inverter drives it, and writes to the wallbox's own registers are overwritten
within seconds (gerd's). A **standalone** wallbox (no inverter manages it; working mode EMS in its
own interface, as evcc needs) is controlled at its own registers. Nothing has been measured on a
standalone one yet.

Signs of a managed wallbox: the inverter's block (33540-33550) reads non-zero; the wallbox's start
mode (input 21314) reads 1, *start with EMS*; it answers through the dongle at unit 3; its 21203
moves with nothing written.

## 2. What is known

### A managed wallbox (gerd's, 2026-11-14)

| What | Where | Measured |
| --- | --- | --- |
| Charging on/off | inverter holding 33540, 0xAA / 0x55 | off stops the car in < 1 s; on starts it in 7-15 s with no replug, unless the car has fallen asleep (a 7-minute stop needed a replug) |
| Charging mode | inverter holding 33541: 160 fast, 161 PV surplus, 163 user defined | written and followed; 162 (quantity and time) never seen |
| User current | inverter holding 33545, 0.1 A | **only in mode 163** (0x04 otherwise); 5 A refused, 6 A to 33 A taken on a 32 A unit |
| Mode side effects | — | to 163 turns charging on; 163 → 160 and 160 → 161 **end the session**; charging on starts it again |
| Two times | inverter 33546-33549, two u32, low word first, Unix time | changed when the app saved; probably the quantity-and-time window |
| Grid surplus | inverter holding 33550, 0x55 / 0xAA | **the app's energy purchase (*Netzbezug*)**: followed the app both ways (2026-11-14 19:34); written, no effect seen at 1.7 kW PV and an empty battery |
| The wallbox's own current | wallbox holding 21203, 0.1 A | **driven by the inverter**: writes overwritten in seconds; the car follows the inverter's ramp (about 1.4 A every 5 s) |
| The app's enable / Start | wallbox holding 21211 / 21212 | 21211 1 = enabled, 0 = disabled (status 21317 then reads **8**, *disabled*); 21212 0 = start |
| The app's other system parameters | wallbox holding 21298 Plug&Play (1/0), 21299 offline current (0.1 A), 21313 power limit (0.1 kW, shown only while disabled) | each changed in the app and back, 2026-11-14 19:36-19:58, seen in the registers within a minute; the offline current does not follow the limit |
| Mileage per kWh | wallbox holding 21232, 0.1 km/kWh | read **55552 = the app's 5555.2** after the capability test of 2026-11-13 (50 before; its restore of 21232 failed); set back to 5.0 in the app at 20:16, read 50 |

- The same writes work through the WiNet-S, judged by the car (its readback is not evidence).
- **Status 8 is *disabled***: it reads 8 whenever 21211 is 0, and 1 (idle) again on enable.
- **A disable (21211 = 0) stops the charge, and writing 1 back does not restart it.** The owner had
  to enable it in the app and press Start.
- **The wallbox pauses on its own** when the home battery is at its minimum SoC (the app's *Grund*
  screen). The inverter's 13023 then reads the charge within the min-max window, near 0.
- **Read-back after a write is not evidence** on this wallbox: it answered one read twice, and
  21203 reads 0 whenever no car charges. Judge by the car: status (input 21317), the phase currents
  (21303/21305/21307).
- **Two clients on the inverter's cable give timeouts**, and the TLS port (516) refuses connections
  opened in quick succession.

### Open questions

- ~~The 8 seen after the disable~~: answered on 2026-11-14, the charging status (input 21317) reads
  8, *disabled*, whenever 21211 is 0; input 21268 reads 0 then.
- **How 21232 became 55552 on 2026-11-13.** The snapshot at 10:00 held 50, and every recorded
  write of 21232 that day (run 1's no-op and restore, run 2, three terminal restores) wrote 50;
  none carried 55552. Yet a probe at 11:47 read 55552 (0xD900), and the app showed 5555.2 until it
  was set back on 2026-11-14 20:16, so the wallbox had really stored it. The same day 21211 read 8
  (only 0 and 1 are documented) after a write of 1, and the wallbox answered duplicate frames.
  Every read-back that day was 0, so the restore's check could not see either value. No
  transcript of the day is left. Until it is understood, the capability test's mileage check
  stays off (it is opt-in) and is not run at gerd's.
- **Why the inverter switches charging off by itself.** Twice on 2026-11-14 a fast-charge session
  ended with the car at 43 %: at about 14:55 (10.2 kWh) and at 16:31 (3.5 kWh, after a restart
  from the app). The second time the inverter's on/off word went to off first, the wallbox
  followed, and the battery read at its minimum SoC (13023 0.8 %, no PV). But charging switched
  on over Modbus at 16:51 ran 5 minutes at 10.5 kW with the battery still at 0.8 % and was not
  stopped, so the battery's minimum alone is not the cause (or it acts only after longer). Next:
  the app's reason for a stop, and a longer watched session.
- **What 162 (quantity and time) writes**, and what the three always-zero words between the mode and
  the user current are.

### What others report on phase switching (web, 2026-11-14)

Register numbers here; evcc's code uses protocol addresses, one lower.

- **Sungrow switches automatically, by power.** Datasheets and dealers: automatic 1/3-phase
  switching with a Sungrow hybrid, charging from 1.38 kW of PV surplus. The iHomeManager's manual:
  when the charging power falls within **1.38-4.14 kW** the iHomeManager tells the charger to switch
  to single phase. No source names a setting, in iSolarCloud or elsewhere, to choose the phases by
  hand.
- **evcc on a standalone wallbox** (`charger/sungrow.go`, PR #23716 for issue #23715): writes
  holding **21204** (0 three, 1 single) only with the charge stopped: holding 21212 = 1 (stop),
  then 21204, then 21211 = 1, 21212 = 0 and the current; reads the phases in use at input 21270.
  Issue #23715: on an AC011E (firmware 1.7.186) a switch without a stop was ignored by some cars;
  evcc's maintainer calls a switch that does not interrupt the charge a firmware fault.
- **A fork's fix** (BastiSch/evcc, branch `fix_sungrow_phase_switching`, 2026-09-07) waits **5 s
  after the stop** before writing 21204. Its comment: the wallbox sets the phases back to three once
  it reaches *completed*, 2-3 s after a stop; and *the SH10RT does not stop the charger when it
  switches phases*: so the inverter switches phases on a managed wallbox, under load.
- **Cars differ**: a Toyota bZ4X needed a pause; a CUPRA Tavascan stopped at the three-phase
  minimum and did not resume on one phase (evcc discussions #23715, #28643).
- **Inverter and evcc on one wallbox fight** (evcc discussion #20739): users decouple the wallbox
  from the inverter for evcc to switch phases; one switched the wallbox to EMS mode for it.

So on gerd's managed wallbox the phases are the inverter's to switch, most likely in PV surplus
when the power wanted is 1.38-4.14 kW; test 5 watches for that.

Sungrow's own manuals, ha-modbus-manager and the 873-post Photovoltaikforum thread, read on
2026-11-14, agree: no setting anywhere, automatic only, and owners see one phase in **PV surplus
with energy purchase (33550) off**, three phase with it on. The wiki keeps it:
`.wiki/wiki/concepts/managed-wallbox-phases.md`.

## 3. Rules for any wallbox write

1. **Never write a managed wallbox's own registers.** The capability test refuses unless the wallbox
   is declared standalone (`--standalone`; Home Assistant never declares it yet), and refuses when
   21203 moves between two reads with nothing written. Do not give `--standalone` at gerd's.
2. **Never write 21211 = 0, never offer under 6 A, never 0.**
3. **Snapshot first, restore after**, and restore the house, not just the register: after a mode
   change, write charging on if the car was charging before; then watch the car charge again.
4. **One client per path.** Home Assistant's polling is held off during a run; ask the owner and the
   maintainer whether anything else polls before testing.
5. **Write every finding into the day's raw note as soon as it is found**, before the next test.
6. The owner consents per phase of testing; the maintainer is asked before any push.

## 4. What the capability tests cover

Three runners:

- **The managed test** (`src/sungrow_modbus/wallbox/managed_test.py`): writes the inverter's block,
  reads the wallbox, puts the house back. From a terminal,
  `device-diagnosis/scripts/python/sungrow_managed_wallbox_test.py INVERTER --wallbox WALLBOX`
  (a dry run; `--leave` writes, `--start-stop` adds the stop and start). In Home Assistant from the
  wallbox's own entry, in *Extended test* or *auto repeat*, when an inverter entry there manages it.
  Needs this tree's library until the release after 0.1.0a38.
- **The standalone test** (`src/sungrow_modbus/wallbox/capability_test.py`): writes the wallbox's
  own registers. Terminal only (`sungrow_wallbox_capability_test.py --standalone`); Home Assistant
  has its whole machinery but no option that declares a wallbox standalone.
- **The plausibility checks** (`src/sungrow_modbus/wallbox/plausibility.py`): read only, fed by
  auto repeat's tick on any wallbox entry.

| Question | Covered by | Status |
| --- | --- | --- |
| User current 6, 8, 10 A followed by the car (managed) | managed test, *user current* | built; the hand-run equivalent passed at gerd's |
| 5 A refused, 6 A taken (managed) | managed test, *floor* | built; matches gerd's by hand |
| Charging off and on, timed, no replug (managed) | managed test, *start/stop* (15 s pause) | built; matches gerd's by hand |
| Output current 6, 8, 10 A, its scale (standalone) | standalone test, *output current* | built; no standalone wallbox yet |
| Current follow across the range, with timings | standalone test, *current follow* | built; no standalone wallbox yet |
| Available current (21322) against the setting | standalone test, *available current* | built; no standalone wallbox yet |
| Above the rating: refused or clamped | standalone test, *above rating* | built; needs the owner's cap set explicitly |
| Start/stop at 21212, timed | standalone test, *start/stop* | built; no standalone wallbox yet |
| Phase switch, idle and while charging (stop seen before 21204) | standalone test, *phase*, *phase while charging* | built; no standalone wallbox yet |
| Fallback after 75 s of silence | standalone test, *fallback* | built; no standalone wallbox yet |
| Mileage per kWh no-op write (21232) | standalone test, *mileage* | built; no standalone wallbox yet |
| Enable (21211) | — | **never written**, by rule 2; the check only skips |
| Below the minimum on the wallbox (5 A, 0) | — | **never written**, by rule 2; the check only skips |
| A write through the dongle (unit 3) | — | not built |
| Power, energy, pilot voltage, counters, the inverter's load against the wallbox | plausibility | built, read only; no committed document carries a block yet |
| 21313, unnamed | plausibility log | logged for a person to read |
| Quantity and time mode (162) | — | on site: the owner sets it in the app |
| Writing what is already set (charging on while on, the same mode) | — | not built; could join the managed test |
| Starting a car asleep (stopped over 10 min) by charging on | — | not built; the managed test's pause is 15 s |
| A mode change from the app: does it end the session too | — | on site |
| One/three phase on a managed wallbox | — | read only on a sunny day (the field tool's `phase`), and the app's setting on site; 21204 did nothing at gerd's |
| PV surplus in sun, grid surplus off and on | — | on site, read only beside the app |
| Unplug and replug: the block and the wallbox at a session's ends | — | on site |
| The block polled every 10 s for an hour through the WiNet-S | — | read only, can run remotely |
| Does the inverter stop the charge at the battery's minimum SoC | — | read only, can run remotely (`session_watch.py` beside `energy.py`); the app's reason on site |

A check whose need was met and still did not settle runs again in the next auto-repeat slot that
meets it, up to three times; then it is reported as not settled. Charging checks need status 3 and
a draw of 5 A or more.

## 5. gerd's: how it was left (2026-11-14)

- At 20:16: the inverter in mode **PV surplus** (set in the app by the maintainer at 19:32),
  *Netzbezug* (33550) **off**, charging **off**, user current 16.0 A. The wallbox: enabled
  (21211 = 1), start (21212 = 0), Plug&Play on, offline current 32 A, power limit 22 kW, three
  phase, idle. Everything the app's system parameters touched read as it did at 19:36.
- Mileage per kWh (21232) set back to 5.0 in the app at 20:16 (it read 5555.2, left by the
  capability test of 2026-11-13). The charger's own page (Plug&Play, Netzbezug) writes the same
  words as the system parameters and the charging mode screen.
- The owner's Home Assistant was stopped for the session.
- The car at about 44 %. In PV surplus without Netzbezug it charges only with surplus: the
  one-phase test (section 6, test 5) needs a sunny day and the battery above its minimum.
- `tmp/gerd-wallbox-2026-11-14/settings_diff.py LABEL [BASE]` (read only) snapshots the wallbox
  whole and the inverter's 33501-33600 and prints what changed: the way the app's settings were
  mapped.

**The field tool** is `scripts/dev/managed_wallbox_field.py` (this tree's library; the addresses as
`--inverter` / `--wallbox` or `$SUNGROW_INVERTER` / `$SUNGROW_WALLBOX`, never in the repository).
Run it from `tmp/`: its logs and scans go to the current directory.

| Command | Does |
| --- | --- |
| `block` | read only: the inverter's block with the two words below it (33538-33550) |
| `energy` | read only: PV, grid, load, battery level (13023) and power |
| `watch N` | read only: the wallbox's status, setting, phase currents and power, N samples |
| `log MINUTES` | read only: the block beside the wallbox every 5 s, to a log |
| `session MINUTES` | read only: the wallbox, the session's energy and the block every 2 min, until the charge stops |
| `phase MINUTES` | read only: the block, PV, battery and the wallbox's 21204/21225/21270/21272 every 5 s; a changed row is marked |
| `scan LABEL` | read only: the inverter's holding 33501-33600 and the wallbox's phases, to `scan_LABEL.json` |
| `charge on\|off SECONDS` | **writes** the inverter's charging on/off, watches, puts the snapshot (flushed first) back, checked on a fresh session |

For the user current and the mode use the managed test (section 4), which restores the house.
2026-11-14's one-off scripts stay in the maintainer's `tmp/gerd-wallbox-2026-11-14/`.

## 6. Next at gerd's (on site, a car plugged in)

In order; 1 to 4 need the owner at the app.

1. **Quantity and time** in the app: which words change (the time pair, the three zero words).
   Decides whether a mode select offers 162.
2. **Writing what is already set**: charging on while on, the mode it has. Must be harmless, because
   a mode select writes charging on after every mode change.
3. **Starting a car asleep** (stopped over 10 minutes) by charging on over Modbus.
4. **The same mode change from the app**: does user defined → fast end the session there too?
5. **Phase switching.** On a managed wallbox the inverter switches phases itself: gerd's charged on
   one phase on 2026-09-08 (21204 = 1, written by nobody here) and 2026-10-30 (the portal: 6.1 A on
   phase A only), and Sungrow's datasheet promises automatic 1/3-phase switching from 1.38 kW of
   PV surplus. Our own 21204 write did nothing. The inverter's charger block has no phase word;
   registers 33538 (85) and 33539 (161), just below it, are candidates (baseline in the raw note,
   2026-11-14, there in protocol addresses). With charging off both refused a write (0x04: 33539 =
   160, 33538 = 0xAA) in fast mode and again in PV surplus mode (19:22); 33539 reads 161 in both
   modes. Whether either moves during a one-phase session is open. Neither
   app account shows a phase setting.
   - **Remotely, read only**: on a day with 1.5-4 kW of sun, the battery above its minimum, the
     car plugged in and *PV surplus* set, run the field tool's `phase MINUTES`. Then
     `scan single-phase` during the one-phase session, to compare with `scan` at three phase.
   - **On site**: look for a phase setting in the app (iSolarCloud, its local access, the installer
     view) and switch it with the car stopped while `phase` runs.
   - **Decides**: a phase select on the inverter entry (if an inverter word switches it, written
     stop → switch → start), or only a sensor for the phase in use (21270, 21225) with *PV surplus*
     as the way to one phase.
6. **PV surplus on a sunny day**, battery well above its minimum, grid surplus off then on: how the
   inverter modulates the current and what 33550 does.
7. **Unplug and replug**: the block and the wallbox at a session's end and start.
8. **The managed test end to end**, from the terminal and then from the dev Home Assistant with
   gerd's inverter and wallbox entries side by side, watched live before auto repeat is left alone.
9. **An hour of the block polled every 10 s through the WiNet-S** beside normal polling: stable
   enough for entities.

## 7. In the repository, still to do

- **Entities on the inverter's entry** (`Todo.md`, Wallbox): a charging switch, a mode select, a user
  current number, from `src/sungrow_modbus/hybrid_inverter/ev_charger.py` through the write table.
  Tests 1-3 above decide details of the select.
- **The standalone test before it meets a standalone wallbox**:
  - refuse to start while the battery is at or near its minimum SoC (the SBR's 10744 against 13059;
    13023 near 0 if the SBR cannot be read), recorded in the snapshot;
  - a restore that checks the house (status as before, the enable reading 1 on a fresh session) and
    says what to do on site if it cannot;
  - the inverter's block and EMS mode in its snapshot, read only;
  - an option, or a measured signal, that declares a wallbox standalone in Home Assistant.
- **The standalone test's phase switch** writes 21204 as soon as the stop is seen; by the fork
  above, the wallbox then resets the phases to three when it reaches *completed*. Wait for a
  settled status and 5 s more before writing 21204.
- **A write through the dongle** (unit 3), leg C only, if a standalone wallbox behind a dongle turns
  up.
- **The managed test's open checks**: writing what is already set, and a longer stop for a sleeping
  car, once tests 2 and 3 above have been done by hand.
- **Ingest**: a wiki source page for `.wiki/raw/gerd-wallbox-capability-test-2026-11-13.md`.

## Verification

- `make check`: `tests/test_wallbox_capability_test.py` (`_cli.py`, `_ha.py`),
  `tests/test_wallbox_managed_test.py` (`_cli.py`), `tests/test_wallbox_managed_ha.py`,
  `tests/test_ev_charger_control.py`.
- The simulator for the plumbing only: it produces no finding.
- Each session on site ingested into the wiki (wallbox page, `doc/wallbox_registers.md`, `log.md`)
  before the next.
