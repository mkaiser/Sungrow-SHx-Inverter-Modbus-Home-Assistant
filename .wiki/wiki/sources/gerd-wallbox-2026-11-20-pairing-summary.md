---
type: source
title: gerd-wallbox-2026-11-20-pairing.md
source_path: raw/gerd-wallbox-2026-11-20-pairing.md
ingested: '2026-11-20'
created: '2026-11-20'
tags:
  - wallbox
  - ac22e-01
  - gerd
  - home-assistant
  - winet-s
---

# gerd's wallbox, the evening of 2026-11-20: pairing the entries, no car

A dev Home Assistant of its own, on the branch's code, against [gerd](../entities/installation-gerd.md)'s
inverter and AC22E-01 with no car plugged in. The site reached through the maintainer's host; read only,
nothing written at the house. Source: `raw/gerd-wallbox-2026-11-20-pairing.md`.

| Fact | Evidence |
| --- | --- |
| **Naming the inverter in the wallbox entry's Configure gives the inverter entry on the cable its four EV charger controls**, within 32 s, reading what the inverter holds; before it, that entry had none | 22:37:58 saved, 22:38:30 the controls; `CONF_WALLBOX_MANAGED_BY` |
| The pairing survives a restart of Home Assistant | 22:41 |
| For a paired wallbox, an extended run asks for the **managing inverter's** diagnosis answers and is refused in its name | 22:41, `testimony.answering_entry` |
| Without *May it write to the wallbox*, an extended run on the wallbox entry runs the read-only diagnosis only, not the capability test: the managed path cannot be seen without leave | 22:46, 35 fields in 4 s |
| **An inverter entry through the WiNet-S gives the wallbox at unit 3 up to the wallbox's own entry** ("it is read there, not here"), keeping only the four controls | 22:48:38 |
| **Deleting the wallbox entry, the inverter entry reloads and takes the wallbox back** (24 entities through the dongle); adding it again, gives it up again | 22:49:32, 22:53:46 |
| A re-added wallbox entry starts unpaired: the question is asked again | 22:53 |
| The wallbox's TLS port answered its model only after 32.8 s on the first connection of the evening; the cable lost its first read and answered after 90 s of quiet | 22:2x, before Home Assistant started |

## What it means

- T059's step 2 is done: one entry per address holds on hardware, both ways
  ([the wallbox](../entities/device-wallbox.md)).
- The pairing is ready for the managed capability test from Home Assistant at gerd's; what is left is the
  run itself, with leave and a car charging.

## Not answered

- The managed run from Home Assistant: needs leave switched on and a car charging.
