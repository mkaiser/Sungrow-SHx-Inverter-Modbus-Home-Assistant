---
type: source
title: gerd-wallbox-2026-11-20-test4.md
source_path: raw/gerd-wallbox-2026-11-20-test4.md
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - wallbox
  - gerd
  - ems
---

# gerd's wallbox, 2026-11-20 at 18:20: the window's start, and which words take a write

The last hour of 2026-11-20 at [gerd](../entities/installation-gerd.md)'s, after
[the user-defined window](gerd-wallbox-2026-11-20-user-window-summary.md) was mapped. Meant for a mode change from
the app while charging (the plan's test 4), which could not run: the car was unplugged at about 18:28. Source:
`raw/gerd-wallbox-2026-11-20-test4.md`.

| Fact | Evidence |
| --- | --- |
| **The user-defined window's start switches charging on by itself** (the word 85 to 170 at 18:30:06, nothing written), offering 6.0 A; with its end switching it off, the window is a daily on/off schedule held by the inverter | the block every 5 s, 18:30 |
| A save of *Benutzerdefiniertes Laden* that does not change the mode does not switch charging on; one that changes it (162 to 163, 16:25) does | three saves at 18:22-18:23, word 85 throughout |
| An unplug: status *completed* to *idle* (1), the pilot 11.9 V; the inverter's block unchanged | 18:28, 18:31 |
| **The window (33546-33549) takes a write only in mode 163, and only as one four-word write (FC 16)**: word by word refused in 163, the four-word write refused in 160, taken in 163 | exception 0x04, 18:39-18:40 |
| The scheduled target and departure (33542-33544) refused single writes in 163; the target took one in 162 (15:39, [the afternoon](gerd-wallbox-2026-11-20-summary.md)). The user current takes a write only in 163 | the same restore |
| The block put back: on, fast, 16.0 A, a whole day's window, grid purchase off | a fresh session, 18:40:23 |

## What it means

- Each mode's words are writable only while that mode is set: a control writes the mode first, then its words,
  and the window as one four-word write.
- A user-defined mode set from Home Assistant switches charging on and off on the window's schedule every day,
  whatever Home Assistant's own switch last said.
- Test 4 still waits for a car on the cable.
