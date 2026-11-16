---
type: query
title: "Which unit does a WiNet-S give a wallbox?"
tags: [wallbox, winet-s]
created: '2026-11-13'
query: "Behind a WiNet-S, does a wallbox always answer at unit 3, or at 2 or 4 elsewhere, as others report?"
results_count: 1
---

# Which unit does a WiNet-S give a wallbox?

**Answered: not always 3.** An AC011E-01 answers at unit **4** behind a WiNet-S, measured
2026-11-16
([the diagnosis](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-14076202309-battery-unknown-winet-summary.md)),
where the AC22E-01 at [gerd](../entities/installation-gerd.md) answers at **3**
([wallbox registers](../sources/wallbox-registers-summary.md)). Two wallboxes, two units, so the
unit is a property of the installation and not of the dongle, and nothing read so far says which
to expect. The search tries 3, then 2 and 4, and found this one without a setting.

Units still only reported, never measured here:

- **2 and 3**, in the ioBroker thread and evcc discussion
  [#7104](https://github.com/evcc-io/evcc/discussions/7104);
- **2**, in ha-modbus-manager issue #127.

The search (`sungrow_modbus.wallbox.discovery.UNITS`) tries 3, then 2 and 4, then 248; 2 and 4
only once the endpoint has answered an earlier unit, because the inverter's own LAN port goes
silent on every wallbox unit and would cost a timeout for each. A unit counts only if its model
name starts with `AC`, since a WiNet-S can put an [SBR](../entities/device-sbr-battery.md) at
unit 2.

What is left: whether **2** ever answers, which would be the one unit the search tries on
nothing but other people's reports. A diagnosis through a WiNet-S whose `wallbox` section names
unit 2 settles it; a third unit other than 2, 3 or 4 would mean the sweep is incomplete.
