---
type: query
title: "Which unit does a WiNet-S give a wallbox?"
tags: [wallbox, winet-s, open]
created: '2026-11-13'
query: "Behind a WiNet-S, does a wallbox always answer at unit 3, or at 2 or 4 elsewhere, as others report?"
results_count: 0
---

# Which unit does a WiNet-S give a wallbox?

**Open.** The one [wallbox](../entities/device-wallbox.md) measured behind a
[WiNet-S](../entities/device-winet-s.md), an AC22E-01 at
[gerd](../entities/installation-gerd.md), answers at unit **3**
([wallbox registers](../sources/wallbox-registers-summary.md)). Others report other units, none
measured here:

- **2 and 3**, in the ioBroker thread and evcc discussion
  [#7104](https://github.com/evcc-io/evcc/discussions/7104);
- **2**, in ha-modbus-manager issue #127;
- **4**, for an AC011E-01, in this repository's issue #786 (cyablo, 2026-11-12).

The search (`sungrow_modbus.wallbox.discovery.UNITS`) tries 3, then 2 and 4, then 248; 2 and 4
only once the endpoint has answered an earlier unit, because the inverter's own LAN port goes
silent on every wallbox unit and would cost a timeout for each. A unit counts only if its model
name starts with `AC`, since a WiNet-S can put an [SBR](../entities/device-sbr-battery.md) at
unit 2.

What answers it: a diagnosis through a WiNet-S whose `wallbox` section names a unit other
than 3.
