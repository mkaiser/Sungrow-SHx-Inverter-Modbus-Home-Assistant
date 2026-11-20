---
type: source
title: gerd-wallbox-2026-11-20-user-window.md
source_path: raw/gerd-wallbox-2026-11-20-user-window.md
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - wallbox
  - gerd
  - ems
  - winet-s
---

# gerd's wallbox, the evening of 2026-11-20: the user-defined window

The hour after [the afternoon](gerd-wallbox-2026-11-20-summary.md) at [gerd](../entities/installation-gerd.md)'s,
the same tunnel, one client per path, the owner's integration disabled. The maintainer saved *Benutzerdefiniertes
Laden* in the app with a window and a current; the block and the car were read every 5 s, and the inverter's block
through the [WiNet-S](../entities/device-winet-s.md) every 10 s for an hour beside it. Source:
`raw/gerd-wallbox-2026-11-20-user-window.md`.

| Fact | Evidence |
| --- | --- |
| **33546-33549 are the user-defined mode's window**: start and end, two u32 pairs, low word first, the local times written as if UTC. The midnights a day apart read on every earlier day are a whole day's window | the app's save at 16:25:34: 16:30..17:30 today |
| The app's save writes mode 163, the user current (33545, 14.0 A) and the window, and switches charging on. The dial steps in no less than 10 minutes, and the end is no less than an hour after the start | the block; the maintainer, of the app |
| **The window's start did not hold the charge back**: the car charged from 16:25:55, 4 minutes before 16:30 | the wallbox every 5 s |
| **The window's end ends the session** (`completed` at 17:30:07, the word off at 17:30:17) **and moves the window one day on** (2026-11-21 16:30..17:30): a daily window | the block and the wallbox, 17:30 |
| **The block through the WiNet-S: 360 reads in an hour at 10 s, none lost**, median 350 ms, slowest 2.7 s; both changes seen at the same seconds as on the cable | test 9, 16:43-17:43 |

## What it means

- A user-defined control that writes only the mode and the current leaves whatever window the app set; a
  window short of a whole day will end a session that Home Assistant started. A control that sets the mode
  should either write a whole day's window or show the window as it is.
- Whether the next day's start switches charging on by itself is open.
- The WiNet-S carries the EV charger block well enough for entities at a 10 s poll.
