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
installation, and [register 13074](register-13074.md) holds **5000 W against a 10000 W maximum**,
half the inverter's rating -- though feed-in limitation is off (13087 holds 0x55), so nothing
enforces it. [Register 32998](register-32998.md) holds 13.00 kW, as on every SH-RS read.

Two readings, two days apart, read only, with no capability test
([the first](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md),
[the second](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md)).
Stand-in `anon-09651441112`.

- **Version 1 is `SUNSTONE-H_01011.02.69` and version 2 `SUNSTONE-H_03021.01.16`** under an
  unchanged `SUNSTONE-H_B000.V002.P067`, where the first P067 read had `.02.67` and `.01.15`
  twelve days earlier. [bigz2012](installation-bigz2012.md)'s SH10RS, read the same day on the
  other side of the world, has the same newer pair.
- **The owner's route and the measurement disagree.** They answer "the inverter's own LAN port,
  through a Modbus proxy", and 6100 is refused with a WiNet-S2 firmware string reading: the proxy
  stands in front of the dongle, not the inverter's own port.
- **Four MPPTs answer and three carry power.** `mppt4` reads 39.5 V to 53.6 V and **0.0 A** in
  all five downloads of this machine, at 3,825 W of PV and at 10,458 W alike, and the other three
  account for `total_dc_power` to within 1 %. 13250 answers as well; both go against what the
  family table expects of an RS, and the probe keeps them.
- **`total_battery_charge`'s high word reads `0xFFFF`**, the specification's *unavailable*, while
  its low word counts properly: 429,494,257.3 kWh, then 429,494,295.3 kWh two days later, which is
  the low word rising by the **38.0 kWh** the battery took. Restoring the wraps that word has lost
  puts the real total at about **17,226.5 kWh**, just above this house's own
  `total_battery_discharge`. The same register is wrong on both other
  [P067](firmware-sunstone-h-b000-v002-p067.md) machines.
- **The pack answers at unit 2**, as through every dongle, and its cells and modules are refused
  with `IllegalDataAddressError`.
- **The inverter's EV charger block reads 161 (*PV surplus*) at 16.0 A**, charging off and
  energy purchase on -- the same words three houses with no wallbox read, so it does not say
  whether the AC22E-01 here is driven by the inverter, by the
  [iHomeManager](device-ihomemanager.md) beside it, or by nobody
  ([the wallbox](device-wallbox.md)).
- **The AC22E-01 beside this inverter is still unread.** Its 0.1.0a44 download asks for the
  diagnosis and finds none: a wallbox entry's report serves the last run's document, which does
  not survive the restart an upgrade brings. *Diagnosis: start* on the wallbox's own device page,
  then the download in the same session, is what it needs.

## Diagnoses

- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, read only](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, second reading](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md)
