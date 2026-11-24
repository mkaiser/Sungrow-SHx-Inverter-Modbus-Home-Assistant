---
type: source
title: gerd-wallbox-2026-11-24.md
source_path: raw/gerd-wallbox-2026-11-24.md
ingested: '2026-11-24'
created: '2026-11-24'
tags:
  - wallbox
  - gerd
  - ems
  - home-assistant
---

# gerd's wallbox, 2026-11-24: the managed test from Home Assistant, PV surplus, a replug

0.1.0a54 in [gerd](../entities/installation-gerd.md)'s own Home Assistant, the only client (the block read beside it
through his Modbus proxy), a three-phase car on the managed AC22E-01, battery 27 % falling to 1 %, PV 1.2-2.4 kW.
Everything was put back at 12:50. Source: `raw/gerd-wallbox-2026-11-24.md`.

| Fact | Evidence |
| --- | --- |
| **The managed test ran from Home Assistant for the first time and passed**: 6, 8, 10 A followed (9.6 A drawn at 10 A), 5 A refused (0x04), stop 1 s, start 12 s without a replug; exit 0, the house put back | 11:00-11:03 |
| **PV surplus, grid purchase off: one phase**, 5.4 A, 1.24 kW at about 1.6 kW of surplus. **The inverter switches 33540 on and off by itself.** Two such charges ended after 10 and 30 s with surplus left, the draw 3-10 s before the word; why is open | 11:09-11:12 |
| **33538 (85) and 33539 (161) do not move in a one-phase session**; nothing else in 33538-33550 does but 33540 | the block every 2.5 s |
| **PV surplus, grid purchase on: three phase at the 6 A minimum**, 3.9 kW at 1.6-2.2 kW of PV, the battery giving the rest | 11:14-11:17 |
| Grid purchase switched off in that charge ends it in 18 s; it is not switched to one phase. In fast, switching it off changes nothing | 11:17, 11:04 |
| Fast to PV surplus ends the session; charging on, written straight after the mode, read off about a minute later | 11:04-11:05 |
| Fast to user defined and back, four times from Home Assistant (charging on written after the mode): **no session ended** | 11:34-11:42 |
| The same from the app: fast to user defined keeps the session, **user defined to fast ends it** and nothing resumes it in the 90 s watched | 12:06-12:11 |
| A fast charge goes on at the battery's minimum (0.6 %, ten minutes, the rest from the grid) | 11:55-12:06 |
| **Plug&Play (21298) starts a charge on plugging in, whatever the charging word was**: on, the inverter's word goes on 3 s after the plug and the car draws 10 s after it; off, the wallbox goes to *standby* and nothing happens for 3 min. Charging on from Home Assistant then starts it in 10 s | three replugs, 12:19-12:37 |
| Switching Plug&Play on with a car plugged in starts a charge too | 12:46 |
| An unplug in a charge switches the word off at once; mode, current and grid purchase survive a replug; the session counter restarts with each session, a stop and start included | 12:24 |
| The LED blinks white in *standby* and is green while charging | the owner at the car |

## What it means

- An automation that decides when the car charges needs Plug&Play off; with it on, every plug-in starts a charge in
  the mode last set.
- The readings' check of the house load was never fed on a wallbox entry of its own, and the standalone inference
  counted one slow read as many: both fixed the same day (`tests/test_wallbox_pairing.py`,
  `tests/test_wallbox_management.py`).
