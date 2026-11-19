---
type: entity
title: Installation bigz2012
tags: [installation, bigz2012, pv-cut, mdns]
created: '2026-11-18'
---

# Installation bigz2012

An [SH10RS](device-sh-rs.md) on [P067](firmware-sunstone-h-b000-v002-p067.md) with **two
[SBR224](device-sbr-battery.md)** (44.8 kWh), read through a wired **WiNet-S2** on
`WINET-SV300.001.03.P032`. One document: a read-only run after dark on 2026-11-16 with a daylight
capability test merged into it on 2026-11-17, the inverter restart deliberately left out -- the
owner has servers on the backup circuit
([the reading](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)).
Stand-in `anon-10002952285`.

- **The PV cut works on P067**, watched: 3467 W before, **0 W during**, 3641 W after. The
  behavioural leg, which a dongle cannot spoil, so
  [31211](register-31211.md)'s control now ships on P065 and P067.
- **Forced charge and forced discharge both act**: 1234 W and 1256 W against 1250 W commanded.
- **The run's outcome 4 is not a device finding.** The one wrong slope is 13074 written divided
  by ten with feed-in limitation off and read back through the dongle's cache; the write scale
  here is unmeasured. It narrows the standing lead at [ra1k-0](installation-ra1k-0.md), where the
  same pattern was kept open as possible evidence of a 1:1 firmware
  ([13074](register-13074.md)).
- **Version 1 is `SUNSTONE-H_01011.02.69` and version 2 `SUNSTONE-H_03021.01.16`**, as at
  [Maximo101](installation-maximo101.md) and against the `.02.67` / `.01.15` of the first P067
  reading.
- **The battery ceiling is 13974 W**: 14074 W is refused at 33047, 33048 and 13052 with exception
  0x04. `battery_max_discharge_power` holds 8900 W where the charge limit holds 10000 W.
- **The dongle's mDNS record names both packs**, each with its own serial and units: `battery1`
  at 2 and 200, `battery2` at **3 and 201**. Unit 3 behind a dongle is a
  [wallbox](device-wallbox.md) at every other house measured, which is a reason to keep
  identifying by [what answers](../concepts/identify-by-what-answers.md) rather than by unit.
  The dongle's reverse-DNS label is **`espressif`**, the first real one in the corpus.
- **Four blocks are refused with 0x02** through the dongle: the sub-controller and battery
  firmware, and both history blocks. The owner offers a run on the inverter's own LAN port to tell
  the dongle's limit from absent hardware, which would settle 13074's write scale here too.
- `battery_charging_start_power` and `battery_discharging_start_power` are absent on this model,
  as #743 concluded for the SH-RS.
- **`total_battery_charge` reads 14,844.2 kWh against a discharge total of 20,874.6 kWh**, which no
  battery can do: its high word (13042) is missing a wrap, and the real figure is about 21,397.8 kWh.
  The register is wrong on every [P067](firmware-sunstone-h-b000-v002-p067.md) machine read.

## Diagnoses

- [SH10RS, B000.V002.P067, bigz2012, a WiNet-S2 on Ethernet: the PV cut works on P067](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)
