# T001 - The site import limit (32998) and forced startup (13017)

What is still to run on hardware. Both are measured and shipped as
controls -- the number *Grid import limit* (W, 10 W step) and the switch
*Forced startup under low SoC* -- on the firmware the wiki lists
([register 32998](../.wiki/wiki/entities/register-32998.md),
[register 13017](../.wiki/wiki/entities/register-13017.md), which carry
what every run measured).

| Case | What it settles | How, where |
| --- | --- | --- |
| PV above the load, battery part full, a forced charge above the surplus | whether the cap is on the grid's share alone, PV counted | the engine's `--import-limit` check, daylight |
| 13017 left on, on **other firmware** | whether the inverter flips `0xAA` back by itself or on PV. **Answered on P020 2026-11-17: it does not** -- 13017 held `0xAA` for 90 min 48 s, through dawn and 31 min of PV, read back from the register (wiki: register-13017, the watch). #444's ~20 min is not reproduced; other firmware, or an iSolarCloud-connected house, is what is left | a watched run, after dark, reading the register back |
| 13017 on P022 and other firmware | whether it is a switch there too | a watched run, after dark |

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
