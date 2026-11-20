# gerd's wallbox, 2026-11-20 evening: pairing the wallbox entry with the inverter entry, no car

Raw note. No car plugged in. The site reached through the maintainer's host (its tunnel; none started in
the devcontainer). Read only unless a step says otherwise. Register numbers; the protocol address is one
lower. Times are CET. No address or serial is in this note.

## Identity and baseline

- The wallbox over TLS (516, unit 248) answered its model, `AC22E-01`, after **32.8 s** (one
  connection, after 90 s of quiet). The first try, straight after a failed inverter read, timed out at
  30 s.
- The inverter's cable (unit 1): the first read, with no quiet before it, lost the connection; after
  90 s of quiet the device type read `0x0E0E` in 4.1 s.
- Inverter block 33538-33550: `[85, 161, 170, 160, 19, 29188, 27392, 160, 36224, 27391, 57088, 27392, 85]`
  = charging **on**, mode **160 fast**, user current 16.0 A, grid purchase off; as left at 18:40.

## 22:4x Two entries in a fresh dev Home Assistant (the branch's code, uncommitted hold included)

- The inverter on its cable added by address (manual step): created in 22 s, title `SH8.0RT-V112`.
- The wallbox found by a search of its single address (`/32`): "1 wallbox", `AC22E-01 (wallbox)`; created
  in 3 s, title `AC22E-01`.
- Both loaded. Before any pairing the inverter entry has **no EV charger controls** (no switch, select
  or number for the wallbox): over the cable it never sees the wallbox, as on 2026-11-17. The wallbox
  entry's *Charger enabled* reads on.

## 22:38 The wallbox's Configure names the inverter

- *Which inverter manages this wallbox?* offered exactly one choice, the cable entry, by its title.
  Saved at 22:37:58 with *May it write to the wallbox* left **off**.
- By 22:38:30 the inverter entry on the cable had the four EV charger controls, reading what the inverter
  holds: *Wallbox charge* on, *Wallbox charge mode* fast (options fast, PV surplus, user defined),
  *Wallbox user-defined current* 16.0 A with its slider up to 32 A (the wallbox's rating, read through
  the wallbox entry), *Wallbox grid purchase* off. **The pairing works on hardware.**
- 22:41 Home Assistant restarted: both entries loaded again, the pairing kept, the four controls back.
- 22:41 *Diagnosis: start* on the wallbox entry in *Extended test* was refused **in the inverter entry's
  name**: "SH8.0RT-V112: answer the diagnosis's questions before an extended test". For a paired wallbox
  the questions are the managing inverter's (`testimony.answering_entry`). Answered in this dev instance
  (cable, no proxy, no other inverter, as in the owner's earlier diagnoses) and every inverter
  capability-test permission switched off.
- 22:46 the same press ran the **read-only diagnosis only** (35 fields, 4 s): with *May it write to the
  wallbox* off, an extended run does not start the capability test at all, so the managed path cannot be
  seen without leave. Its preflight would stop at "no car is charging" before any write
  (`src/sungrow_modbus/wallbox/managed_test.py`); not run tonight: switching leave on at the owner's
  house is left to the maintainer. The test summary's management reads `unknown`, "no charge seen yet".
- Nothing was written to the inverter or the wallbox in this session.

## 22:48 T059: the inverter entry through the WiNet-S beside the wallbox entry

- The inverter entry moved to the WiNet-S by **Reconfigure** (unit 1, port 502); the move step said
  nothing about a wallbox (it warns only when leaving a dongle). Loaded again in about 20 s with the
  four EV charger controls.
- **It gave the wallbox up**: "the wallbox behind this dongle has an entry of its own; it is read there,
  not here" (22:48:38). The inverter entry has no wallbox sensors; the wallbox entry keeps its 40.
- 22:49:05 the wallbox entry deleted. The inverter entry reloaded by itself and **took the wallbox
  back** at 22:49:32: "wallbox on unit 3, model AC22E-01", 24 wallbox entities through the dongle, none
  unavailable (idle, enabled, *Start charging on plug-in* on, lifetime 920.22 kWh).
- 22:53 the wallbox entry added again (the `/32` search, as before). The inverter entry reloaded by
  itself and **gave the wallbox up again** (22:53:46, the same line). The new entry starts unpaired: its
  *Which inverter manages this wallbox?* offered the one inverter with nothing suggested. Named again
  at 22:53:49.
- 22:55 the inverter entry moved back to the cable by **Reconfigure**; the move step said nothing about
  a wallbox (it has an entry of its own, so nothing is lost). The four controls came back within about
  20 s, reading charge on, fast, 16.0 A, purchase off.

## How it was left, 22:56

The dev instance (gitignored `tmp/config-gerd/`) stopped: the inverter entry on the cable, the wallbox
entry on TLS naming it, *May it write to the wallbox* off, every inverter capability-test permission off,
the inverter entry's diagnosis mode read only. Nothing written at the owner's house; his own Home
Assistant integration still disabled.
