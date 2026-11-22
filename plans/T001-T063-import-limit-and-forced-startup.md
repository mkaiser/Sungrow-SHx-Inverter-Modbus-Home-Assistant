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
| 13017 left on, on **other firmware** | whether the inverter flips `0xAA` back by itself or on PV. **Answered on P020 2026-11-17: it does not** -- 13017 held `0xAA` for 90 min 48 s, through dawn and 31 min of PV, read back from the register (wiki: register-13017, the watch). #444's ~20 min is not reproduced; other firmware, or an iSolarCloud-connected house, is what is left | a watched run, after dark, reading the register back |
| 13017 on P022 and other firmware | whether it is a switch there too | a watched run, after dark |

**gerd's is the P022 this wants**, and the precondition is already met there
rather than waited for: `--forced-startup` needs the battery at its minimum
with no PV, and his SBR096 sat at its 0.5 % minimum through the nights of the
second half of November
([the night](../.wiki/wiki/sources/gerd-wallbox-night-2026-11-16-summary.md),
[the afternoon](../.wiki/wiki/sources/gerd-wallbox-2026-11-17-afternoon-summary.md)).
One night window with his Home
Assistant stopped answers this row and T032's watched restart together, in that
order -- the forced startup first, since it leaves the inverter running for the
restart to measure. It does **not** combine with T044's dongle restore run,
which wants the battery above 30 %: that is a different window, and in late
autumn a different week.

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
