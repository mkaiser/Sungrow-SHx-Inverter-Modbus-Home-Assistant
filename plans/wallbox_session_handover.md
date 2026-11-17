# Handover: wallbox work, as of 2026-11-17 morning

Start with `plans/wallbox_tests.md` (facts, rules, coverage, next tests at gerd's).

- **Done and committed** (4b90098 and before): the managed wallbox test (library, terminal script,
  Home Assistant from the wallbox's entry via `managing_entry`); the standalone test refuses on a
  managed wallbox. All pushed; ask the maintainer before every push.
- **Open finding**: the inverter switched gerd's charging off by itself twice on 2026-11-14 (car
  at 43 %), the second time with the battery at its minimum SoC; but a session switched on over
  Modbus at 16:51 ran 5 minutes at that SoC unstopped. Cause open (`plans/wallbox_tests.md`,
  section 2). `scripts/dev/managed_wallbox_field.py session` and `energy` read it remotely.
- **gerd's house**: fast charge, 16 A; charging off (put back after the 16:51 five-minute charge),
  the car at about 44 %. Nothing of ours to put back. Never write the wallbox's own registers there; write the inverter's
  block only with the owner's consent.
- **Phase switching**: how to find it is test 5 of `plans/wallbox_tests.md`, needs a day with
  1.5-4 kW of sun (`managed_wallbox_field.py phase`, then `scan single-phase`).
- **Next in code**: the inverter entry's EV charger entities (`Todo.md`, Wallbox item 3), from
  `src/sungrow_modbus/hybrid_inverter/ev_charger.py`.

## 2026-11-16/17, a VPN night at gerd's

- **Done**: the managed capability test's first run on hardware (terminal, passed), same-value writes
  (harmless), mode changes with a car charging (163 ↔ 160 ends a session), 21203 settled (user current in
  163, the inverter's offer in fast). Wiki: `gerd-wallbox-night-2026-11-16-summary.md` and the query
  `why-does-a-managed-wallbox-stop-charging.md`.
- **Found wrong**: the managed test's restore reported the house back 28 s before the inverter ended the
  session (it changed the mode back and read at once). Fix before its Home Assistant run
  (`plans/wallbox_tests.md`, section 7).
- **gerd's house**: on, fast, 16.0 A; the car at about 89 %, suspended by the vehicle since 02:19, not
  resumed at 06:05. Needs the owner (car app, or a replug). The tunnel is down.

