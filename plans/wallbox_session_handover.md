# Handover: wallbox work, as of 2026-11-14 evening

Start with `plans/wallbox_tests.md` (facts, rules, coverage, next tests at gerd's).

- **Done and committed** (4b90098 and before): the managed wallbox test (library, terminal script,
  Home Assistant from the wallbox's entry via `managing_entry`); the standalone test refuses on a
  managed wallbox. Pushed up to c455602; **4b90098 and later are not pushed**: ask before pushing.
- **Running, read only**: `tmp/gerd-wallbox-2026-11-14/session_watch.py` logs gerd's session to
  `session_watch.log` in that folder every 2 min until the charge stops. It tests whether a session
  in fast mode stops near 10 kWh (the last one stopped at 10223 Wh with the car at 43 %; restarted
  from the app at about 16:11). Write the result into
  `.wiki/raw/gerd-wallbox-inverter-control-2026-11-14.md` and `plans/wallbox_tests.md` section 2.
- **gerd's house**: charging on, fast charge, 16 A. Nothing to put back. Never write the wallbox's
  own registers there; write the inverter's block only with the owner's consent.
- **Next in code**: the inverter entry's EV charger entities (`Todo.md`, Wallbox item 3), from
  `src/sungrow_modbus/hybrid_inverter/ev_charger.py`.
