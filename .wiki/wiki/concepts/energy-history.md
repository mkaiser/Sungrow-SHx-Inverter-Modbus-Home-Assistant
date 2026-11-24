---
type: concept
title: Energy history (inputs 6227-6637)
tags: [energy-history, cable-only, registers]
created: '2026-11-01'
---

# Energy history (inputs 6227-6637)

The inverter keeps its own monthly and yearly totals for three quantities: PV generation
(months 6227-6238, years 6250-6279), direct consumption from PV (6417-6428, 6429-6458) and export
from PV (6596-6607, 6608-6637). Defined in `src/sungrow_modbus/hybrid_inverter/registers.py`
(`_energy_history`), gated on `Capability.ENERGY_HISTORY`.
Each month, and each year that holds something, is a sensor (`custom_components/sungrow_modbus/history_descriptions.py`),
and the readings checks compare this month with the daily counter and the year with its month.

## The layout

- **Months are U16, 0.1 kWh, this calendar year only**; the current month counts up through the
  day.
- **Years are U32, low word first, 0.1 kWh, and the first slot is 2015.** Each 2026 slot equals
  the sum of the year's months exactly, for all three quantities, at four cable houses:
  [peter-sm](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-3-summary.md),
  [mkaiser](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md)
  (P020), [fwitten](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md)
  (P023), and [bar12](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2-summary.md) (P023).
- **But a year is not always the sum of its months.** At [gerd](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md) (P022) direct
  consumption's 2026 slot is, while PV generation's and export's are each 1610.3 kWh above
  theirs. The slot positions still hold there (2026 is the slot the months come closest to, and
  the later slots read 0), so the integration's month and year sensors each show the inverter's
  own register, and no sum is ever computed from the other.

## Cable only

Every WiNet-S refuses the block, as it refuses 6100. A dongle that answers part of it with 0
([Jam3s97](../sources/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan-summary.md))
is [not evidence](zero-means-absent.md). See [transport detection](transport-detection.md).

## What does not add up

- gerd's yearly PV and export slots exceed their months by the same 1610.3 kWh in 2026, and
  read 21429.6 and 28914.4 kWh of PV for 2024 and 2025 from an 8 kW inverter
  ([the diagnosis](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)).
- mkaiser's 2024 slots read 37461.2 kWh of PV and 32834.6 kWh of export, about three times any
  other year from a 10 kW inverter.
- fwitten's master reads more export from PV than PV generation, and 0 direct consumption since
  2025. It carries the master/slave cluster's meter, so the slave's PV may be counted in its
  export.

- **The years against the lifetime counters.** Direct consumption's years add up to
  `total_direct_energy_consumption` everywhere both answer, within 2.2 kWh. PV generation's and
  export's years do not: at six inverters both are too high, by the *same* amount to 0.3 kWh in these readings --
  [mkaiser](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md) 52579.1 kWh, [an anonymous SH10RT-V112](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-summary.md) 45210.9,
  [RobBensonMIO](../sources/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan-summary.md) 42897.2, [gerd](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md) 32451.9,
  [mahagon](../sources/sh50rt-v112-b001v000p023-3p-mahagon-anon-11187075801-battery-sbr096-meter-direct-lan-summary.md) 17409.6, [bar12](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-2-summary.md) 8533.3. At three the two excesses differ:
  [an anonymous SH10RT-V112](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-33455145473-battery-sbr128-meter-direct-lan-summary.md) 12715.2 and 10702.6, [fwitten](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md) 2762.4 and 2251.9,
  [tristangrichard](../sources/sh80rt-v112-b001v000p023-3p-tristangrichard-anon-04477133025-battery-sbr096-meter-direct-lan-summary.md) 283.0 and 139.1. At the others read, peter-sm's among them, the years add up.
  The lifetime counters are the plausible ones.
  What adds the energy is unknown: it is in PV and export, never in direct consumption.

None is explained; the integration shows the inverter's figures as they are.
