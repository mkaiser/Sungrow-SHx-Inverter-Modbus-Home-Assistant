---
type: source
title: gerd-auto-repeat-2026-11-21.md
source_path: raw/gerd-auto-repeat-2026-11-21.md
ingested: '2026-11-21'
created: '2026-11-21'
tags:
  - capability-test
  - auto-repeat
  - restore
  - register-13052
  - discharge-window
  - gerd
  - sapphire-h-b001-v000-p022
---

# gerd's own Home Assistant, 2026-11-21: a day of the diagnosis in extended auto repeat

Ten capability runs from the integration (0.1.0a46) on [gerd](../entities/installation-gerd.md)'s
production Home Assistant, the inverter entry on the cable path through a modbus proxy, watched from
09:07 to 15:25 CET, when the maintainer stopped it; the readings went on being watched to 17:45. Source:
`raw/gerd-auto-repeat-2026-11-21.md`. SH8.0RT-V112 on
[P022](../entities/firmware-sapphire-h-b001-v000-p022.md), SBR096, EMS self-consumption.

| Fact | Evidence |
| --- | --- |
| **13052's hard limit is the inverter's rated power**: 8000 W on this 8 kW model; 8100, 9000 and 10000 W are refused with exception 0x04, 8000 W is stored | writes by hand through the proxy, each read back after 2 s and 10 s |
| The battery-derived maximum shown for 13052 (4860 W) is **not** enforced: one step over it (4960 W) was stored | run 1's upper-bound probe, and the register afterwards |
| **Run 1 ended with exit 5**: 13052 held 10000 W before the integration ever wrote it, the run wrote over it, and the inverter refused the value back; every other control was restored | Home Assistant's history of every control, before and after |
| After the exit 5 no repair was raised until a next setup, and auto repeat's next run saved its own snapshot over the kept one | the integration's code, run 2 |
| On P022 `battery_max_soc` (13058) and `battery_min_soc` (13059) refuse a step past their maximum; 33047, 33048, 13052, 33149 and 33150 store it | runs 1 and 10 |
| Forced charge, the PV cut, both forced-charging windows, the site import limit, backup, load control and the weekend enable write paths did as told | run 1 |
| Forced discharge at 1250 W: -788 / **1251** / -752.5 W discharge power | run 6, battery 22 % |
| The export limit at 1250 W, made by a 3280 W discharge: export 3973.5 / **1243** / 3437.5 W, set as the feed-in ratio 100 % to 15.6 % | run 6 |
| 13074's write scale was not asked in any run: feed-in limitation is off (13087 holds 0x55), and then 13074 ignores every write without an exception | runs 2-10 |
| The charging start threshold (33149) at 1000 W stopped a 660 W charge to 0 W and it came back to 683 W | run 8 |
| The charge ceiling at 53.2 % stopped a 2069.5 W charge to 0 W; 1980 W after | run 9, battery about 56 % |
| "Discharge windows away from now: nothing measurable happened" was **a procedure error**: the battery was charging through the bracket (-549.5 / -617.5 / -544 W of discharge power), and the stop check compared the absolute value | run 4, its effect row |
| End of day: 37/55 passed, 0 failed; 5 upper bounds unenforced, the false discharge-window result, and 12 readings checks or the discharging start threshold still open | the diagnosis sensors at 17:45 |

## What changed because of it

- A capability run refuses to start while an earlier run's snapshot is kept, a failed restore raises the
  repair at once, and either stops auto repeat (the integration).
- A control whose own value lies outside its bounds is written back to itself first, and left out of the
  run if refused (the library's preflight).
- A stop check compares signed power, so charging is "nothing to stop" (the library's effects).

The discharge window's earlier confirmation at gerd over the cable (3799 W to 0 W) stands; run 4's
result is wrong, and stays in gerd's ledger until the runs are cleared.
