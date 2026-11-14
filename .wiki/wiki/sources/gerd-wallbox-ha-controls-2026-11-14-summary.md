---
type: source
title: gerd-wallbox-ha-controls-2026-11-14.md
source_path: raw/gerd-wallbox-ha-controls-2026-11-14.md
ingested: '2026-11-14'
created: '2026-11-14'
tags: [wallbox, gerd, ems, home-assistant]
---

# gerd's managed wallbox from Home Assistant's controls, 2026-11-14 night

`.wiki/raw/gerd-wallbox-ha-controls-2026-11-14.md`: the integration's four EV charger controls
on the inverter's entry at [gerd](../entities/installation-gerd.md) (P022, over the cable), each
written once from the dev Home Assistant and put back, with no car charging. The
[managed wallbox's](../entities/device-wallbox.md) block read back as written each time.

| Fact | Evidence |
| --- | --- |
| The four controls are created on P022 where the mode reads a named code, and show the block | mode PV surplus, charge off, grid purchase off, 16 A, as the field tool read it |
| *Wallbox grid purchase* writes 33550 both ways | on and off, read back |
| *Wallbox user-defined current* is refused before any write outside user-defined mode | HTTP 400 with the message naming the mode select; 16 A unchanged |
| In user-defined mode it takes 10 A and 16 A | read back each time |
| Mode PV surplus → user defined with charging off leaves charging off; back to PV surplus too | read after each change |
| *Wallbox charge* writes 33540 on and off | read back each time |
| Everything put back | an independent read at 23:03:43 matched 22:52 word for word |

Not shown: what a car does, for no car charged (measured from a terminal earlier that day:
[gerd, 2026-11-14](gerd-wallbox-inverter-control-2026-11-14-summary.md)), and whether user
defined switched charging on for a moment before the select's off write.
