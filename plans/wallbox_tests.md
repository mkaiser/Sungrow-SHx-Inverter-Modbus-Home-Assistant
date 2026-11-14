# Wallbox tests: what is known, what the capability test covers, what is next

The one plan for testing and controlling a Sungrow wallbox: the facts measured so far, the rules for
any write, which checks the capability tests run on their own and which need a person on site, and
the next session at gerd's (SH8.0RT with an AC22E-01). gerd allows every test while a car charges.

Device facts are on the wiki's [wallbox](../.wiki/wiki/entities/device-wallbox.md) page (section
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
| Grid surplus | inverter holding 33550, 0x55 / 0xAA | written; no effect seen at 1.7 kW PV and an empty battery |
| The wallbox's own current | wallbox holding 21203, 0.1 A | **driven by the inverter**: writes overwritten in seconds; the car follows the inverter's ramp (about 1.4 A every 5 s) |
| The app's enable / Start | wallbox holding 21211 / 21212 | 21211 1 = enabled; 21212 0 = start |

- The same writes work through the WiNet-S, judged by the car (its readback is not evidence).
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

- **Remote control status 8** (input 21268) and an enable register reading 8: undocumented, seen
  after the disable.
- **Why the inverter switches charging off by itself.** Twice on 2026-11-14 a fast-charge session
  ended with the car at 43 %: at about 14:55 (10.2 kWh) and at 16:31 (3.5 kWh, after a restart
  from the app). The second time the inverter's on/off word went to off first, the wallbox
  followed, and the battery read at its minimum SoC (13023 0.8 %, no PV). But charging switched
  on over Modbus at 16:51 ran 5 minutes at 10.5 kW with the battery still at 0.8 % and was not
  stopped, so the battery's minimum alone is not the cause (or it acts only after longer). Next:
  the app's reason for a stop, and a longer watched session.
- **What 162 (quantity and time) writes**, and what the three always-zero words between the mode and
  the user current are.

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
| One/three phase on a managed wallbox | — | read only on a sunny day (`phase_watch.py`), and the app's setting on site; 21204 did nothing at gerd's |
| PV surplus in sun, grid surplus off and on | — | on site, read only beside the app |
| Unplug and replug: the block and the wallbox at a session's ends | — | on site |
| The block polled every 10 s for an hour through the WiNet-S | — | read only, can run remotely |
| Does the inverter stop the charge at the battery's minimum SoC | — | read only, can run remotely (`session_watch.py` beside `energy.py`); the app's reason on site |

A check whose need was met and still did not settle runs again in the next auto-repeat slot that
meets it, up to three times; then it is reported as not settled. Charging checks need status 3 and
a draw of 5 A or more.

## 5. gerd's: how it was left (2026-11-14)

- The inverter's block as the owner wants it: charging **on**, mode **fast charge**, user current
  **16.0 A**, grid surplus **no**. The wallbox: enabled (21211 = 1), start (21212 = 0), three phase.
- The owner's Home Assistant was stopped for the session.
- Field scripts and logs are in `tmp/gerd-wallbox-2026-11-14/` (gitignored: they carry addresses,
  which live only in the maintainer's local notes). They use protocol addresses.

| Script | Does |
| --- | --- |
| `phase_a.py` | read only: the inverter's block (cable) beside the wallbox (TLS) every 5 s, to a log |
| `watch.py N` | read only: the wallbox's setting, status, phase currents, N samples |
| `session_watch.py` | read only: status, currents, session energy and the inverter's on/off every 2 min until the charge stops |
| `inv_block.py` | read only: the inverter's block and EMS mode, both paths |
| `inv_steps.py ADDR=V:SEC ...` | writes the inverter, watches, restores the snapshot; superseded by the managed test |
| `seq.py WATCH ADDR=V[:PAUSE] ...` | writes a sequence with no restore (used to put the house back), then watches |
| `energy.py` | read only: PV, grid, load, battery level |
| `phase_watch.py MINUTES` | read only: the inverter's 33536-33549, PV, battery, and the wallbox's phase registers every 5 s, changes marked |
| `scan_335xx.py LABEL` | read only: the inverter's holding 33500-33599 and the wallbox's phase registers, to a JSON for comparison |

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
   33537 (85) and 33538 (161), just below it, are candidates (baseline in the raw note, 2026-11-14).
   - **Remotely, read only**: on a day with 1.5-4 kW of sun, the battery above its minimum, the
     car plugged in and *PV surplus* set, run `phase_watch.py MINUTES` (the inverter's 33536-33549,
     PV, battery, the wallbox's 21204/21225/21270/21272, status and phase currents every 5 s; a
     changed row is marked). Then `scan_335xx.py single-phase` during the one-phase session, to
     compare with the baseline.
   - **On site**: look for a phase setting in the app (iSolarCloud, its local access, the installer
     view) and switch it with the car stopped while `phase_watch.py` runs.
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
