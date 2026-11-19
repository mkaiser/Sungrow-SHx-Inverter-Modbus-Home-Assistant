# The scenes beyond the one press, mkaiser's SH10RT, 2026-11-19

The remaining scenes of `doc/scenes.md` on hardware (T013), from the
development instance against the real inverter (`config-real`, :8125), which
runs the integration; the production Home Assistant on the same inverter runs
the YAML package and is read-only by rule.

House at the start, 12:35 CET: **battery 0.0 %**, battery power 0 W, PV 329 W,
load 517-605 W, export 0 W, Running, EMS self-consumption, command stop,
forced power 0 W, max charge 4500 W, max discharge 5000 W, feed-in limit off.

**Why only two of the four could be tried.** *Zero Export Power* and *Max
Export Power* need the house exporting. In November, with PV at 329 W under a
517 W load, the house imports and there is nothing to limit; a forced charge
makes that worse, not better. So they stay where they were. *Battery Bypass
Mode* and *Battery Forced Discharge* need a battery with something in it,
which a forced charge can fix, and that is what this run does.

**The scenes installed here were stale.** `config-real/scenes.yaml` still held
the copy from before 2026-11-17: no `number...._power` line on either forced
scene, and unquoted numeric states. Reinstalled from the current
`doc/scenes.md` before the first press, so what follows tests the document as
it stands.

Restore: snapshot above; `restore.sh` logs in afresh each time (an access
token lasts 30 minutes) and is armed detached to fire at 13:22 CET whatever
happens to the session.

## Results

### Battery Forced Charge, 12:38 CET -- the power line is what makes it move

Activated `scene.battery_forced_charge` from the reinstalled document.

| Before (12:37:53) | After (12:38:39) |
| --- | --- |
| `ems_mode` self_consumption | **forced** |
| `battery_forced_charge_discharge` stop | **charge** |
| `battery_forced_charge_discharge_power` 0.0 W | **2000.0 W** |
| `battery_power` -491 W | **-1999 W** |
| running state Running | **Running in compulsory (forced) mode** |

-1999 W against 2000 W commanded, within one watt, in under 46 s including
the poll. This is the fix of 2026-11-17 proven on hardware: the copy that was
installed here had no `number...._power` line, and without it the inverter
reports forced mode and moves nothing. The scene as the document now writes
it moves exactly what it says.

Note the start: the battery was already taking **-491 W** at 0.0 % in
self-consumption with the house importing (PV 329 W, load 583 W), so this
inverter tops an empty pack up from the grid of its own accord.

**The charge itself**, with the power raised to 4500 W by hand (not part of
the scene) to fill the pack in a session: 0.0 % at 12:38 to **8.7 % at
12:52**, 14 minutes, battery power steady at -4502 W throughout. That is
0.62 %/min, against the 0.53 %/min of the 48-minute run on 2026-11-17 at the
same 4501 W -- the pack takes the first tenth faster than the first quarter.

### Self-Consumption Mode (max battery discharge), 12:53 CET -- mode yes, power no

| Before | After |
| --- | --- |
| `ems_mode` forced | **self_consumption** |
| `battery_forced_charge_discharge` charge | **stop** |
| running state Running in compulsory (forced) mode | **Running** |
| `battery_max_discharging_power` 5000.0 W | 5000.0 W, untouched |

The mode half works. The power half **does nothing here**, exactly as the
document says it will: the scene carries no fixed value and leaves the
maximum to the automation, which is not installed on this instance. So the
scene is honest, and a reader who skips the automation gets the mode and
keeps whatever maximum was already set.

Left `battery_forced_charge_discharge_power` at 4500 W, which is right: the
forced power is only read in forced mode, and no scene should disturb it.

**What the house does at a low state of charge, in self-consumption**: the
battery went on **charging at -814 W** with the house importing (load 563 W).
Same as the -491 W seen before any scene was pressed. This inverter tops an
empty pack up from the grid on its own, so "self-consumption" here is not
"the battery covers the load" until the pack is well above 10 %.

### Battery Bypass Mode, 12:54 CET -- 0 W, and the surplus goes past the battery

| Before (12:53:52) | After (12:54:47) |
| --- | --- |
| `ems_mode` self_consumption | **forced** |
| `battery_forced_charge_discharge` stop | stop |
| `battery_power` -814 W (charging) | **0 W** |
| `export_power` 0 W | **1057 W** |
| running state Running | **Running in compulsory (forced) mode** |

Forced mode with the command at *stop* is what the name says: the battery is
held at exactly 0 W, and the PV the inverter was putting into it goes to the
grid instead. Both numbers moved together, which is what makes this a
measurement and not a coincidence: -814 W out of the battery's column and
1057 W into the grid's, against a load that did not move (563 -> 557 W).

**It needs no power setting.** `battery_forced_charge_discharge_power` stayed
at 4500 W throughout and nothing charged or discharged, so the two forced
scenes that *do* need a power are the charge and the discharge, exactly as
`doc/scenes.md` has it.

### Battery Forced Discharge, 12:55 CET -- 2002 W against 2000 W asked

| Before (12:54:47) | After (12:55:44) |
| --- | --- |
| `battery_forced_charge_discharge` stop | **discharge** |
| `battery_forced_charge_discharge_power` 4500.0 W | **2000.0 W** |
| `battery_power` 0 W | **+2002 W** (discharging) |
| `export_power` 1057 W | **2948 W** |

Two watts off what was asked for, and the scene **overwrote** the 4500 W that
was in the register from the charge: the power line writes, it does not merely
fill a blank. The grid took the difference -- 1891 W more exported against a
load that stayed at 563 W, which is the battery's 2002 W less the 111 W the
house took of it.

So both forced scenes do as they say on P020, and both need their power line.

### Zero Export Power, 13:04 CET -- it works, on the third attempt

| Before | After |
| --- | --- |
| `feed_in_limit_mode` off | **on** |
| `feed_in_limit` 10000.0 W | **0.0 W** |
| `export_power` 676 W | **0 W** |

**And the first two attempts failed, which is the more useful finding.** At
12:57 and at 13:00 the scene changed nothing at all, and the second one left
the reason in the log:

> `ERROR ... Error during service call to scene.turn_on: Could not write
> switch.hwr_sh10rt_feed_in_limit_mode: write_register(13086, 170):
> Connection lost before response was received.`

Not the scene, and not the registers: both were written **singly** between
the failures and both took -- the switch on by itself, and the limit to 0 by
itself, which took export from 967 W to 0 W. What failed is the link. This
inverter's own LAN port is carrying the maintainer's production Home
Assistant (through its modbus-proxy) and this development instance at once,
and the development instance logged **34 lost connections in the hour** of
this run (2159 in its log overall). A scene writes two registers back to
back, which is two chances to meet a drop, and **when the first write raises
the rest of the scene is abandoned** -- so a scene is all-or-nothing, and on
a contended link it is nothing more often than a single write is.

Worth saying in `doc/scenes.md`: a scene that appears to do nothing on a
busy inverter has probably lost the connection, and the log says so. Retry
it.

### Max Export Power

Activated at 13:05 with only the switch to set, and **nothing moved**: the
limit stayed at 0.0 W from the zero-export test and export stayed at 0 W.
The scene is not at fault -- it deliberately carries no limit, because a
scene cannot ask the inverter what its maximum is. **The automation that
does was never installed on this instance**: `config-real/automations.yaml`
held only *Max battery discharge scene sets the battery's own limit*, one of
the two `doc/scenes.md` gives.

Installed the second one from the document, reloaded, and activated again:

| Before | After (13:07) |
| --- | --- |
| `feed_in_limit_mode` on | on |
| `feed_in_limit` 0.0 W | **10000.0 W** |
| `export_power` 0 W | **607 W** |

So the pair works as the document describes it: the scene turns the limit on
and the automation fills in the inverter's own maximum, read from the
number's `max` attribute -- the same trick as the battery one, and the
second half of the pattern the 2026-11-17 run proved with
`state_attr(..., 'max')` rendering 7420 W rather than `None`.

**The lesson for a reader is the same as the battery's**: the two export
scenes are only half a thing without their automation, and the document
should say which scene needs which automation where the scene is, not only
in a section below it.

### Self-Consumption Mode (no battery discharge), 13:08 CET -- and the retry again

First activation set the mode and **left `battery_max_discharging_power` at
5000 W**. Second activation, 90 s later, set it to **10.0 W**. Nothing else
changed between them. That is the third time in this run that a scene's
second register did not land first time and did on a retry.

So the count for this link, over seven scene activations: **three needed a
second press**, and in one case the log named the cause outright (a lost
connection mid-write). A scene is not atomic, and on a contended inverter it
is worth reading back what it set.

## Restore, 13:11 CET

Every setting the run touched, put back to the 12:35 snapshot and **verified
by read-back**, each with up to five attempts because one write is not a
restore on this link:

| Setting | Back to |
| --- | --- |
| `battery_forced_charge_discharge` | stop |
| `ems_mode` | self_consumption |
| `battery_forced_charge_discharge_power` | 0.0 W |
| `battery_max_discharging_power` | 5000.0 W |
| `battery_max_charging_power` | 4500.0 W |
| `feed_in_limit` | 10000.0 W |
| `feed_in_limit_mode` | off |

All seven read back right; the inverter is Running and the battery taking
-175 W from the PV, as it was before any of this. The pack is left at **10 %**
rather than the 0 % it started at, which is a gift and not a changed setting.

A detached restore was armed before the first write and left armed, set to
fire at 13:22 whatever happened to the session; it logs in afresh each time
because an access token lasts thirty minutes, which is how a watch once left
13017 on for fifty minutes past its window.

## What is still untested

Nothing of `doc/scenes.md` -- all seven scenes and both automations have now
run on hardware. What is **not** measured is what any of them does over
time: every reading here is within a minute or two of the press.
