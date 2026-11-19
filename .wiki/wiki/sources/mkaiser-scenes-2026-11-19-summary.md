---
type: source
title: mkaiser-scenes-2026-11-19.md
source_path: raw/mkaiser-scenes-2026-11-19.md
ingested: '2026-11-19'
created: '2026-11-19'
tags: [scenes, mkaiser, sh10rt, sapphire-h-b001-v000-p020, contention, forced-mode]
---

# All seven scenes on hardware, mkaiser's SH10RT, 2026-11-19

`.wiki/raw/mkaiser-scenes-2026-11-19.md`: the remaining scenes of
`doc/scenes.md` at [mkaiser](../entities/installation-mkaiser.md)'s
[SH10RT](../entities/device-sh-rt.md) on
[P020](../entities/firmware-sapphire-h-b001-v000-p020.md), from the
development instance against the real inverter, 12:35-13:11 CET. The pack
started **empty** (0.0 %), so a forced charge was run first to make the
battery scenes testable.

| Scene | What it did | Status |
| --- | --- | --- |
| Battery Forced Charge | `battery_power` -491 -> **-1999 W** against 2000 W asked; forced mode reported | measured |
| Self-Consumption Mode (max battery discharge) | mode back to self-consumption; the **limit untouched**, left to its automation | measured |
| Battery Bypass Mode | `battery_power` -814 -> **0 W**, and `export_power` 0 -> **1057 W** in the same poll | measured |
| Battery Forced Discharge | `battery_power` 0 -> **+2002 W** against 2000 W asked; export 1057 -> 2948 W | measured |
| Zero Export Power | `export_power` 676 -> **0 W**, limit 10000 -> 0 W | measured, third attempt |
| Max Export Power | limit 0 -> **10000 W** (the entity's own `max`), export 0 -> 607 W | measured, after installing its automation |
| Self-Consumption Mode (no battery discharge) | `battery_max_discharging_power` 5000 -> **10 W** | measured, second attempt |

Every setting was restored to the 12:35 snapshot and verified by read-back.

## The power line is what makes a forced scene move

Both forced scenes do exactly what they are told on P020, to within two
watts, and **both need their `number..._power` line** -- the fix of
2026-11-17. The copy of the scenes installed on this instance predated that
fix and carried no power line; reinstalled from the current document before
the run. The forced-discharge scene **overwrote** the 4500 W left in the
register by the charge, so the line writes rather than filling a blank.

*Battery Bypass Mode* needs no power at all: forced mode with the command at
*stop* holds the battery at 0 W and lets the PV it was absorbing go to the
grid. Both numbers moved in the same poll against an unmoved load, which is
what makes it a measurement.

## A scene is not atomic, and this link drops

**Three of seven presses did nothing the first time and worked on a retry**,
and one left the reason in the log:

> `Error during service call to scene.turn_on: Could not write
> switch.hwr_sh10rt_feed_in_limit_mode: write_register(13086, 170):
> Connection lost before response was received.`

Not the scene and not the registers: both of that scene's registers were
written **singly** between the failures and both took. What failed is the
link. This inverter's own LAN port carries the maintainer's production Home
Assistant (through its modbus-proxy) and the development instance at once,
and the development instance logged **34 lost connections in the hour** of
this run. A scene writes its registers one after another and **abandons the
rest when one raises**, so on a contended link a scene fails more readily
than a single write does ([contention](../concepts/contention.md)).

`doc/scenes.md` now says so where a reader meets it.

## An automation is half of two scenes

*Max Export Power* changed nothing until its automation was installed: only
one of the document's two automations was on this instance. With it, the
limit is written from the number's own `max` attribute. The document now
names the automation at the scene that needs it, rather than only in a
section below.

## What this house does at a low state of charge

In self-consumption at 0-10 %, with the house importing, the battery went on
**charging from the grid** -- -491 W before any scene was pressed and -814 W
after the forced charge ended. So "self-consumption" here does not mean "the
battery covers the load" until the pack is well above 10 %. The forced
charge itself ran 0.0 % to 8.7 % in 14 minutes at a steady -4502 W, which is
0.62 %/min against the 0.53 %/min of the 48-minute run of 2026-11-17 at the
same power: the first tenth fills faster than the first quarter.
