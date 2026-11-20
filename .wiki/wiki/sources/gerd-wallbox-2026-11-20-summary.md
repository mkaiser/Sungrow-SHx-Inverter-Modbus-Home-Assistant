---
type: source
title: gerd-wallbox-2026-11-20.md
source_path: raw/gerd-wallbox-2026-11-20.md
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - wallbox
  - gerd
  - ems
  - scheduled-charging
---

# gerd's wallbox, the afternoon of 2026-11-20

An afternoon at [gerd](../entities/installation-gerd.md)'s over a WireGuard tunnel run from the devcontainer,
a three-phase car plugged in at 57 %, the managed AC22E-01 driven through the inverter's block at unit 1 on
its LAN cable, with the owner's consent to any test. No PV, the home battery at 2.8 % and idle. Until about
14:58 the owner's own Home Assistant ran this integration, polling the same inverter; the maintainer
disabled it then. Source: `raw/gerd-wallbox-2026-11-20.md`.

| Fact | Evidence |
| --- | --- |
| **A car stopped for 15 minutes starts again on charging on over Modbus**, no replug: drawing current 19 s after the write (after 3 minutes stopped: 5 s; after 2 minutes: 5 s) | 33540 written 0xAA, the wallbox's status and phase currents, 14:43 |
| **A charging off written while a car charges reads back on for about 10 s**: 3-4 s after 33540 = 0x55 the word reads 0xAA until about +13 s, then 0x55, the car at 0 A throughout. Three stops in four, the last with the owner's integration disabled | four stops at 3 s reads, 13:57-15:11 |
| **The mode select's writes ended no session with one client per path**: fast to user defined (the mode alone) and user defined to fast with charging on, 108 reads, the word on, the car at 14.8 A or more. The same first write at 14:54, with the owner's integration still polling, ended the session and the inverter switched it on again by itself within 7 s | `ev_charger.mode_writes` replayed, 14:54 and 15:03 |
| **Mode 162 is the app's *Terminiertes Laden*** (scheduled charging): its screen asks a departure time and a target in kWh. A save writes 33541 = 162, **33542 the target in 0.1 kWh**, **33543/33544 the departure as a u32, low word first, the local time written as if it were UTC**, and charging on (33540). 33545 and the time pair 33546-33549 are untouched | snapshots before and after the save, 15:29 and 15:31 |
| **33542 takes a write over Modbus** (150 read back), but the running session did not change | 15:39 |
| **Mode 162 charges either at the minimum or at full power, not at a computed rate**: 6 A (3.9 kW) for 4.1 kWh by 17:41, unchanged when the target (Modbus) or the departure (app, 16:20) moved mid-session; 6 A ramping to the fast mode's offer (27.7 A, the car at 16 A, 10.5 kW) for 1.9 kWh by 16:15 saved after a stop | the wallbox every 5 s, 15:43-16:04 |
| **Mode 162 ends the session at its target**: `completed` at 1913 Wh against 1.9 kWh, 11 minutes before the departure | 16:04, session energy 21310/21311 |
| **A stop, from the app or at the target, reaches the car first**: `completed` and 0 A while the inverter's word still reads on, the word off 11-18 s later | 15:27, 15:51, 16:04 |
| A stop from the app does not rewrite the time pair 33546-33549; something at about 14:58 switched charging off and set the pair to that day's and the next day's midnight (UTC), the way an app save does | the block, 14:58 |
| Through the WiNet-S the block read for 16 minutes at 6 s with no read lost, beside the cable | 15:12-15:28 |

## What it means

- A Home Assistant switch that reads 33540 right after writing off shows *on* for a poll; judge a stop by the
  car, or hold the written state through the next two polls.
- The mode endings seen before (the night of 2026-11-16, and 14:54 today) may have been a second client's:
  with one client per path, two runs (2026-11-17 afternoon, today 15:03) ended nothing. Not settled
  ([why a managed wallbox stops charging](../queries/why-does-a-managed-wallbox-stop-charging.md)).
- A *scheduled charging* control needs the target and the departure written before the session starts:
  mid-session the inverter kept its plan. When it chooses the minimum and when full power is open; three
  readings, all without sun and with the battery idle.
- The cable timed out for about a minute at 14:55 while the host's tunnel ran beside the devcontainer's, with one
  key; two such tunnels steal each other's handshake, which is the likeliest cause. Unproven.
