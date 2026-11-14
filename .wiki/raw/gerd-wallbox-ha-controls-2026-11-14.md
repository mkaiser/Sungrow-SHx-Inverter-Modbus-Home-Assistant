# gerd's managed wallbox from Home Assistant's new controls, 2026-11-14 night

The integration's new EV charger controls (commit b68fb3b) on gerd's SH8.0RT-V112, firmware
`SAPPHIRE-H_B001.V000.P022`, from the dev Home Assistant in the maintainer's container: an entry
over the inverter's LAN cable, unit 1, set up as a diagnostics entry with *Create the entities
too*. At the maintainer's request, who confirmed nothing else polls the inverter. Dark, PV 0, the
battery at its minimum; the wallbox idle at the last read (19:58), no car charging. Register
numbers here. Every change by a Home Assistant service call; each state below is what Home
Assistant read back on the refresh that follows a write.

## Created, and what they read (22:59)

All four controls exist (the inverter's 33541 reads a named code and the firmware is P022):

| Entity | State | The block at 22:52 (field tool, protocol 33537-33549) |
| --- | --- | --- |
| select *Wallbox charge mode* | `pv_surplus` | 33541 = 161 |
| switch *Wallbox charge* | off | 33540 = 0x55 |
| switch *Wallbox grid purchase* | off | 33550 = 0x55 |
| number *Wallbox user-defined current* | 16.0 A | 33545 = 160 |

## The writes

| Time | Service call | Result | Read back after |
| --- | --- | --- | --- |
| 23:00:50 | switch *Wallbox grid purchase* on | HTTP 200 | grid purchase on; nothing else moved |
| 23:00:55 | switch *Wallbox grid purchase* off | HTTP 200 | grid purchase off; nothing else moved |
| 23:01:11 | number *Wallbox user-defined current* 10 A, in PV surplus | **HTTP 400, refused before writing**: "The user-defined current is taken only in the user-defined charge mode; ... Set select.sh8_0rt_v112_wallbox_charge_mode to User defined first" | unchanged, 16.0 A |
| 23:01:22 | select *Wallbox charge mode* user defined (charging off) | HTTP 200 | mode user defined, **charge off** (the select writes charging off after the mode, as user defined switches it on); read again every 5 s to 23:01:47, unchanged |
| 23:02:03 | number *Wallbox user-defined current* 10 A, in user defined | taken | 10.0 A |
| 23:02:11 | number *Wallbox user-defined current* 16 A | taken | 16.0 A, as before the test |
| 23:02:30 | switch *Wallbox charge* on (user defined, no car charging) | HTTP 200 | charge on, held to 23:02:50 |
| 23:02:51 | switch *Wallbox charge* off | HTTP 200 | charge off |
| 23:03:03 | select *Wallbox charge mode* PV surplus (charging off) | HTTP 200 | mode PV surplus, charge off |

23:03:43, an independent read of the block on a session of its own (field tool, protocol
33537-33549): 85, 161, 85, 161, 0, 0, 0, 160, 42112, 27383, 62976, 27384, 85 -- word for word
the reading of 22:52. The house is as it was: PV surplus, charging off, grid purchase off, user
current 16 A.

## What it shows

- The four controls are created on P022 with a named mode, and read the block correctly.
- Each write was taken and read back as written; the user current, outside user-defined mode,
  was refused by Home Assistant before any write, with the message naming the mode select.
- After user defined with charging off, charging read off. Whether the inverter switched it on
  for a moment before the select's off write is not visible here: no car was charging, and Home
  Assistant reads only after both writes.
- Not shown, because no car charged: that the car follows any of it from Home Assistant. That was
  measured from a terminal earlier in the day (`gerd-wallbox-inverter-control-2026-11-14.md`).
