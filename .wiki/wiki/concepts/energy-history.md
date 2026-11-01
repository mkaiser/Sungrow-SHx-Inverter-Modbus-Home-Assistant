---
type: concept
title: Energy history (inputs 6227-6637)
tags: [energy-history, cable-only, registers]
created: '2026-11-01'
---

# Energy history (inputs 6227-6637)

The inverter keeps its own monthly and yearly totals for three quantities: PV generation
(months 6227-6238, years 6250-6279), direct consumption from PV (6417-6428, 6429-6458) and export
from PV (6596-6607, 6608-6637). Defined in `src/sungrow_modbus/inverter/registers.py`
(`_energy_history`), gated on `Capability.ENERGY_HISTORY`.

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
  ([the survey](../sources/sh80rt-v112-b001v000p022-3p-gerd-anon-00267885816-battery-sbr096-meter-direct-lan-2-summary.md)).
- mkaiser's 2024 slots read 37461.2 kWh of PV and 32834.6 kWh of export, about three times any
  other year from a 10 kW inverter.
- fwitten's master reads more export from PV than PV generation, and 0 direct consumption since
  2025. It carries the master/slave cluster's meter, so the slave's PV may be counted in its
  export.

None is explained; the integration shows the inverter's figures as they are.
