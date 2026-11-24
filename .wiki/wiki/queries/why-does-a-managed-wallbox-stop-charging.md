---
type: query
title: Why does a managed wallbox stop charging?
query: What ends a charging session on a wallbox the inverter manages, when nothing of ours wrote - the inverter, the wallbox or the car?
results_count: 7
tags: [wallbox, ems, open]
created: '2026-11-17'
---

# Why does a managed wallbox stop charging?

**Open, narrowed.** Nine endings were seen at [gerd](../entities/installation-gerd.md), a three-phase
car on a managed AC22E-01. Which side decides is settled for six of them.

| Ending | When | What was written first | Who ended it |
| --- | --- | --- | --- |
| The inverter's word went off, the wallbox `completed`, in 6 s | 2026-11-17 00:21 and 02:02 | a mode change to or from user defined (163), while charging | **the inverter**: a mode change ends the session; charging on restarts it ([the night](../sources/gerd-wallbox-night-2026-11-16-summary.md)) |
| `completed` about 30 s after the managed test's restore | 2026-11-16 21:33 | the restore's mode change from user defined back to fast | **the inverter**, most likely: 163 to 160 ends a session (measured twice the same night), and the restore had read the block before the word went off; the owner's car app said the charge was done at 47 % |
| The inverter's word went off, with the battery at its minimum | 2026-11-14 14:55 and 16:31 | nothing, and a restart from the app | open: on 2026-11-14 the battery was at its minimum, but on 2026-11-16 a fast charge ran for hours at 0.2-0.5 % without ending ([the night](../sources/gerd-wallbox-night-2026-11-16-summary.md)), so the minimum alone is not the cause |
| `suspended by the vehicle`, 0 A, from 02:19 on 2026-11-17 | 02:19, nothing written since 02:03 | nothing | **the car**: the wallbox and the inverter offered current (the word on, 21203 up to 19.8 A) and the car drew none; the inverter's own word went off at 03:50, after 1.5 h of it. The car still reached 100 % later that morning, so it was a pause ([the morning](../sources/gerd-car-morning-2026-11-17-summary.md)) |
| The inverter's word off within 1 s, `completed` at +4 s, then the word on again by itself at +7 s and the car charging at +9 s | 2026-11-20 14:54 | fast to user defined, while charging, **with the owner's own Home Assistant polling the inverter** | **the inverter**, with a second client on the house; the same write at 15:03 with that client disabled ended nothing ([2026-11-20](../sources/gerd-wallbox-2026-11-20-summary.md)) |
| `completed` at the target, the word off 11 s later | 2026-11-20 16:04 | nothing; mode 162 (scheduled) with a 1.9 kWh target | **the inverter**: scheduled charging ends a session at its target ([2026-11-20](../sources/gerd-wallbox-2026-11-20-summary.md)) |
| `completed` at the window's end, the word off 10 s later | 2026-11-20 17:30 | nothing; user defined (163) with a 16:30..17:30 window | **the inverter**: the user-defined window's end ends a session, daily ([the evening](../sources/gerd-wallbox-2026-11-20-user-window-summary.md)) |
| `completed` with the surplus still there, the draw gone 3-10 s before the word went off | 2026-11-24 11:10 and 11:12, after 10 and 30 s | PV surplus on one phase, grid purchase off | open: the car, the wallbox or the inverter; the block says nothing ([2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)) |
| `completed` within seconds, the word off | 2026-11-24 12:09 | user defined to fast **in the app** | **the inverter**: the app writes no charging on after the mode ([2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)) |

| Not an ending: the car cut to 6-8 A and ramped back, the session kept | 2026-11-17 15:08, 15:11, 15:14, 15:15 | nothing | **the inverter**, most likely: each right after a house load spike (to 16.0 kW, a phase to about 5.9 kW) under a 20 kW import limit ([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)) |

And a mode change does **not** always end a session: on the afternoon of 2026-11-17 fast to user defined
and back, while charging, left it running, with the battery at 2.8 % rather than its minimum and some PV
([the afternoon](../sources/gerd-wallbox-2026-11-17-afternoon-summary.md)); so did the same writes on
2026-11-20 at 15:03, the battery again at 2.8 %, no PV, and one client per path
([2026-11-20](../sources/gerd-wallbox-2026-11-20-summary.md)).

What is still open:

- **Why the car suspended** at 02:19 at about 89 %: a charging limit, a timer or schedule in the car or its
  app, battery temperature or conditioning, the plug. It was a pause: the car reached 100 % by the morning.
  The car app was to give the reason, but the car reported that its Internet connection was not established
  ([the morning](../sources/gerd-car-morning-2026-11-17-summary.md)), so the app's word that night,
  its "done at 47 %" at 21:33 included, may be stale. Three short attempts of 100-180 W (02:32, 02:46, 02:53) and then none for three hours.
- **Whether the inverter's 03:50 off is a reaction to the long suspension** (an inverter timeout) or a schedule.
- **When a mode change ends a session and when it does not**: the endings were at night with the battery at
  its minimum and no PV, and on 2026-11-20 at 14:54 with a second client polling; two runs with one client per
  path ended nothing, nor did four changes from Home Assistant on 2026-11-24 as the battery went from 17 to 10 %, where a
  fast charge also went on at the minimum ([2026-11-24](../sources/gerd-wallbox-2026-11-24-summary.md)).
- **How long after a mode change the inverter switches the word off**: within 1 s from 163 to 160 (02:02), 16 s
  from 160 to 163 (00:21). A writer has to wait that long before it judges or writes charging on.
