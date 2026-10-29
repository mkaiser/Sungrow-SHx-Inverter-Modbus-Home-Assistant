---
type: concept
title: Identify by what answers
tags: [discovery, unit-id, config-flow]
created: '2026-10-29'
---

# Identify by what answers

**Never by an open port, and never by unit id.** Not every endpoint on 502
is a Sungrow, and an inverter is not always unit 1.

- `identify()` and the config flow sweep `discovery.IDENTIFY_UNITS` (1, then
  2-5). They return which unit answered, and they name the exception type on
  failure, because a refusal and a timeout lead to different next steps
  ([a failed read is not a refusal](failed-read-is-not-refusal.md)).
- A **cluster slave** answers on unit **2**
  ([fwitten](../entities/installation-fwitten.md)).
- Input 8000 on unit 247 is probed for an
  [iHomeManager](../entities/device-ihomemanager.md).

## Units by device and transport

| Device | Inverter's LAN port | Through a WiNet-S | Own address |
| --- | --- | --- | --- |
| inverter | 1 (slave: 2) | 1 | |
| [SBR battery](../entities/device-sbr-battery.md) | 200 | 2 | |
| [wallbox](../entities/device-wallbox.md) | never | 3 | 248, TLS on 516 |
| [iHomeManager](../entities/device-ihomemanager.md) | | | 247 on 502 or 503 |

Sub-devices are found again whenever an entry's endpoint changes. So moving
to a cable keeps the pack, and loses a wallbox the dongle was carrying unless
`wallbox_host` points at it.

## One entry, one endpoint

One config entry is **one inverter, reached through one Modbus endpoint**
(host + port) at a time, plus the devices discovered on it. That is exactly
the set that shares one serialized connection ([contention](contention.md)).
The unique id is the inverter's serial. The endpoint is the owner's choice
and can change without losing anything (Reconfigure, or Add integration
finding it elsewhere).
