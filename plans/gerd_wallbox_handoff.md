# Handoff: the next wallbox session at gerd's

For whoever picks up gerd's wallbox next, human or agent. Written 2026-11-14 at 14:30, when the
maintainer left the site. Read this, then `plans/wallbox_recovery_and_retest.md` (its status block),
then the wiki's `device-wallbox` page (section *Under an inverter's energy management*).

## How it was left

- **The car was charging**: 10.6 kW, 15.3-16.1 A, wallbox status charging (read 14:25).
- The inverter's wallbox block, as the owner wants it: charging **on**, mode **fast charge**, user
  current **16.0 A**, surplus from the grid **no**. The two time words read 2026-11-14 00:00 and
  2026-11-15 00:00 UTC (set by the app).
- The wallbox: enabled (holding 21211 = 1), start/stop 0 (start), phase setting 0 (three phase).
- The owner's Home Assistant had been stopped for the session; the maintainer also polls the
  inverter's cable at times. **Ask before testing whether either is running**: two clients on the
  cable gave timeouts (2026-11-14, 13:46).

## What is known (2026-11-14)

The inverter (SH8.0RT-V112) **manages** the AC22E-01. All register numbers below; the protocol
address is one lower.

| What | Where | Measured |
| --- | --- | --- |
| Charging on/off | inverter holding 33540, 0xAA / 0x55 | off stops the car in < 1 s; on starts it in 7-15 s, no replug if the car stopped minutes ago |
| Charging mode | inverter holding 33541: 160 fast, 161 PV surplus, 163 user defined | written and followed; 162 (quantity and time) never seen |
| User current | inverter holding 33545, 0.1 A | **only in mode 163** (0x04 otherwise); 6 A floor, 33 A accepted on a 32 A unit |
| Mode side effects | — | to 163 turns charging on; 163 → 160 and 160 → 161 **end the session** |
| Two times | inverter 33546-33549, two u32, low word first, Unix time | changed when the app saved; probably the quantity-and-time window |
| Grid surplus | inverter holding 33550, 0x55 / 0xAA | written; no effect seen at 1.7 kW PV and an empty battery |
| The wallbox's own current | wallbox holding 21203, 0.1 A | **driven by the inverter**: writes overwritten in seconds; the car follows the inverter's value |
| The app's enable / Start | wallbox holding 21211 / 21212 | 21211 1 = enabled; 21212 0 = start |

Through the WiNet-S the same writes work (judged by the car; its readback is not evidence).

Every write with times and what the car drew: `.wiki/raw/gerd-wallbox-inverter-control-2026-11-14.md`.

## Rules for the next session

1. **Never write the wallbox's own registers** at gerd's: they are the inverter's. The capability
   test refuses anyway unless `--standalone` is given; do not give it there.
2. Write only the inverter's block above, one write at a time, each judged by what the car draws
   (wallbox input 21303/21305/21307, the phase currents) and its status (input 21317).
3. **Snapshot first, restore after**, and restore the house, not just the register: after a mode
   change, write charging on (33540 = 0xAA) if the car was charging before. Then read it back over
   the cable and watch the car charge again.
4. **Write every finding into the day's raw note as soon as it is found**, before the next test
   (the maintainer's rule).
5. The owner consents to any test while charging; the maintainer must be asked before any push.

## Tools

Today's field scripts and logs are in `tmp/gerd-wallbox-2026-11-14/` (gitignored: they carry the
addresses; the addresses themselves are in the maintainer's local notes, never in the repository):

| Script | Does |
| --- | --- |
| `phase_a.py` | read only: the inverter's block (cable) beside the wallbox (TLS) every 5 s, to a log |
| `watch.py N` | read only: the wallbox's setting, status, phase currents, N samples |
| `inv_block.py` | read only: the inverter's block and EMS mode, both paths |
| `inv_steps.py ADDR=V:SEC ...` | writes the inverter, watches, **restores the snapshot**, checked by read (`INV=` picks the path) |
| `seq.py WATCH ADDR=V[:PAUSE] ...` | writes a sequence with no restore (used to put the house back), then watches |
| `energy.py` | read only: PV, grid, load, battery level |

**For the inverter-side checks use the managed test instead**, which does what `inv_steps.py`
did with a snapshot on disk and a restore that waits for the car:
`device-diagnosis/scripts/python/sungrow_managed_wallbox_test.py INVERTER --wallbox WALLBOX`
(dry run), then `--leave` (`--start-stop` for the stop and start). It needs this tree's library
until the next release.

Addresses in them are **protocol** addresses (33539 is register 33540). One session per path at a
time; the TLS port refuses connections opened in quick succession.

## What to test next (on site, a car plugged in)

In order; 1 to 4 need the owner at the app.

1. **Quantity and time (*Menge/Zeit*)** in the app: which words change (the time pair, the three
   words between the mode and the user current that always read 0). Decides whether a mode select
   offers 162.
2. **Writing what is already set**: charging on while on, the mode it has. Must be harmless,
   because the select writes charging on after every mode change.
3. **Starting a car asleep** (stopped over 10 minutes), by charging on over Modbus. A 7-minute
   stop needed a replug on 2026-11-14.
4. **The same mode change from the app**: does user defined → fast end the session there too?
5. **Phase switching**: find the app's one/three phase setting (the wallbox did a single-phase
   session on 2026-09-08; writing its own 21204 did nothing on 2026-11-13). Switch it with the car
   stopped while `phase_a.py` reads the inverter's whole block and wallbox inputs 21225, 21270,
   21272.
6. **PV surplus on a sunny day**, battery well above its minimum, grid surplus off then on: how the
   inverter modulates the current and what 33550 does.
7. **Unplug and replug**: the block and the wallbox at a session's end and start.
8. **An hour of the block polled every 10 s through the WiNet-S** beside normal polling: stable
   enough for entities.

## What is waiting in the repository

- Entities on the inverter's entry (`Todo.md`, Wallbox, item 3.2): a charging switch, a mode select,
  a user current number, from `src/sungrow_modbus/hybrid_inverter/ev_charger.py` through the write
  table. Tests 1-3 above decide details of the select.
- The rest of `plans/wallbox_recovery_and_retest.md` section 3 (battery-SoC refusal, house-level
  restore, inverter block in the snapshot) matters only for a standalone wallbox now.
- `.wiki/raw/gerd-wallbox-capability-test-2026-11-13.md` has no wiki source page yet.
