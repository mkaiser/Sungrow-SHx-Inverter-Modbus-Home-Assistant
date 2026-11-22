# T001 - The site import limit (32998) and forced startup (13017)

What is still to run on hardware. Both are measured and shipped as
controls -- the number *Grid import limit* (W, 10 W step) and the switch
*Forced startup under low SoC* -- on the firmware the wiki lists
([register 32998](../.wiki/wiki/entities/register-32998.md),
[register 13017](../.wiki/wiki/entities/register-13017.md), which carry
what every run measured).

| Case | What it settles | How, where |
| --- | --- | --- |
| PV above the load, battery part full, a forced charge above the surplus | whether the cap is on the grid's share alone, PV counted. **Held by hand 2026-11-21, under passing clouds** (median 1933 W against a 2190 W cap, PV above the load; wiki: register-32998), with overshoots where PV dipped and no clean after-bracket. What is left is a bracket in steady light | **not the engine**: its fixed 1250 W charge is absorbed by a PV surplus (it declined, 582 W from the grid). A watched hand run through the entry's entities: forced charge 4500 W, a cap at half the import, 150 s, cap off 90 s, restore -- when the battery is under ~85 %, PV is 0.2-2 kW over the load and steady for 5 min (a low-battery morning in clear or uniform light) |
| 13017 left on, on other firmware | whether the inverter flips `0xAA` back by itself (#444). Held 90 min on P020 (wiki: register-13017); not watched elsewhere | a watched run after dark, reading the register back, at any house that has the switch |

13017 as a switch is settled on P020, P022 and P023 (wiki: register-13017); the SH-T is T063.

Not worth a run: a full battery at night, a forced charge into a full
battery (the engine skips at 90 %), a forced discharge.

**A watch that drives Home Assistant presses through
`scripts/dev/ha_watch.py`** rather than a `finally` block of its own: it mints
its credential when it restores, which is what the watch of 2026-11-17 could
not do, waits for a run in flight instead of interrupting one, and exits 5
where the house is left changed. Its first real use is the next 13017 watch.

**The engine refuses an inverter in low-SoC Standby** ("reports
'Standby'"), though a forced charge wakes one by itself in ~2 min (EMS or
schedule, bar12). Whether the import-limit check should command that
charge and wait for the start instead of refusing: decide with the
diagnosis's rework.

## Status log

- **2026-11-22**, gerd's night window (T063's P022 half, T032): 13017 did as told on P022 and
  P022 joined `CONFIRMED_ON_FIRMWARE`; a watched restart showed one start is enough (the night
  boot waits ~4.5 min in Standby), so `async_ensure_running` no longer re-sends into Standby.
  Two diagnosis bugs found and fixed on the way: the forced startup dry run waited out its
  10-minute deadline, and `--restart-only` was refused at night. Wiki:
  `sources/gerd-forced-startup-and-restart-2026-11-22-summary.md`. What is left here is T001's
  daylight bracket.
