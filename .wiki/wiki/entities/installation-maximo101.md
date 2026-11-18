---
type: entity
title: Installation Maximo101
tags: [installation, maximo101]
created: '2026-11-18'
---

# Installation Maximo101

An [SH10RS](device-sh-rs.md) on [P067](firmware-sunstone-h-b000-v002-p067.md) with **two
[SBR192](device-sbr-battery.md)** (38.6 kWh reported), an
[iHomeManager](device-ihomemanager.md) and an **AC22E-01**
[wallbox](device-wallbox.md) at its own address, read through a
[WiNet-S](device-winet-s.md) from Home Assistant. The owner describes it as an Australian
installation; the export limit holds 5000 W, where every other house in the corpus holds its
rating. One reading, read only, with no capability test
([the reading](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)).
Stand-in `anon-09651441112`.

- **Version 1 is `SUNSTONE-H_01011.02.69` and version 2 `SUNSTONE-H_03021.01.16`** under an
  unchanged `SUNSTONE-H_B000.V002.P067`, where the first P067 read had `.02.67` and `.01.15`
  twelve days earlier. [bigz2012](installation-bigz2012.md)'s SH10RS, read the same day on the
  other side of the world, has the same newer pair.
- **The owner's route and the measurement disagree.** They answer "the inverter's own LAN port,
  through a Modbus proxy", and 6100 is refused with a WiNet-S2 firmware string reading: the proxy
  stands in front of the dongle, not the inverter's own port.
- **Four MPPTs answer** (190.4 V, 353.4 V, 410.4 V and 40.1 V), and 13250 answers, both against
  what the family table expects of an RS; the probe keeps them.
- **`total_battery_charge` read 429,494,257.3 kWh**, an unsigned reading of a small negative raw
  value, beside ordinary figures for the two totals next to it.
- **The pack answers at unit 2**, as through every dongle, and its cells and modules are refused
  with `IllegalDataAddressError`.
- **The wallbox entry's diagnostics carries no diagnosis**, so the AC22E-01 beside this inverter
  is still unread.

## Diagnoses

- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, read only](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
