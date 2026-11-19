---
type: entity
title: SUNSTONE-H_B000.V002.P067
tags: [firmware, sunstone-h-b000-v002-p067]
created: '2026-11-05'
updated: '2026-11-19'
---

# SUNSTONE-H_B000.V002.P067

[SH-RS](device-sh-rs.md) firmware, read on three machines through a [WiNet-S](device-winet-s.md)
only. **The PV cut is confirmed here**, so the switch ships on this firmware.

**The versions beside it move while the string does not.** The first reading, 2026-11-05, had
version 1 `SUNSTONE-H_01011.02.67` and version 2 `SUNSTONE-H_03021.01.15`; the two readings of
2026-11-17, from houses on opposite sides of the world, both have
**`SUNSTONE-H_01011.02.69`** and **`SUNSTONE-H_03021.01.16`** under the same
`SUNSTONE-H_B000.V002.P067`. So this string is not enough to say what an SH-RS is running, and an
update can arrive with nothing in 13250 to show for it
([firmware gating](../concepts/firmware-gating.md) keys its tables on version 1 for that reason).

- **[Register 31211](register-31211.md) cuts PV**, watched at
  [bigz2012](installation-bigz2012.md) in daylight through a WiNet-S2: 3467 W before, 0 W during,
  3641 W after. `CONFIRMED_ON_FIRMWARE` now holds this firmware beside
  [P065](firmware-sunstone-h-b000-v002-p065.md).
- **Forced charge and forced discharge act**: 1234 W and 1256 W against 1250 W commanded, same run.
- **[13074](register-13074.md)'s write scale is unmeasured here.** The one run wrote it with
  feed-in limitation off, which the register ignores, and read it back through a dongle's cache;
  the owner reports 1:1 in watts, which is a report and not a measurement.
- **The battery ceiling is 13974 W** on an SH10RS with two SBR224: 14074 W refused at 33047,
  33048 and 13052 with exception 0x04. `battery_charging_start_power` and
  `battery_discharging_start_power` do not answer, as on every SH-RS (#743).
- **`total_battery_charge`'s high word is wrong here, on all three machines read.** 13042 holds
  `0x0002` at [bigz2012](installation-bigz2012.md), `0x0000` at [brendan](installation-brendan.md)
  and **`0xFFFF`** -- the specification's *unavailable* -- at
  [Maximo101](installation-maximo101.md), so the totals read 14,844.2, 6,374.1 and 429,494,295.3
  kWh against their own `total_battery_discharge` of 20,874.6, 12,708.0 and 16,668.7 kWh. A battery
  cannot give out more than it took in, and `total_battery_charge_from_pv` is a part of the charge:
  it too reads higher than the charge on all three. Restore the wraps the high word has lost
  (6,553.6 kWh each) and the three land just above their own discharge totals -- 21,397.8, 12,927.7
  and 17,226.5 kWh -- and exactly one whole number of wraps does that for each
  ([Maximo101's second reading](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md)
  sets out the arithmetic). **13041, the low word, is sound**: it rises by the kilowatt-hours the
  battery takes. No machine on any other firmware shows it, and every other lifetime total on these
  three is exact -- `total_direct_energy_consumption` + `total_battery_charge_from_pv` +
  `total_exported_energy_from_pv` meets `total_pv_generation` to the 0.1 kWh.
- An earlier capability test was refused because that inverter was key-stopped.
- The battery firmware string (13280) carries bytes after its NUL, as on
  [P065](firmware-sunstone-h-b000-v002-p065.md).

## Diagnoses

- [SH10RS, B000.V002.P067, brendan, a WiNet-S on Ethernet, capability test refused](../sources/sh10rs-b000v002p067-1p-brendan-anon-01362170354-battery-sungrow-winet-lan-summary.md)
- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, read only](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-summary.md)
- [SH10RS, B000.V002.P067, Maximo101, through a WiNet-S2, second reading](../sources/sh10rs-b000v002p067-1p-maximo101-anon-09651441112-battery-sungrow-direct-lan-2-summary.md)
- [SH10RS, B000.V002.P067, bigz2012, a WiNet-S2 on Ethernet: the PV cut works on P067](../sources/sh10rs-b000v002p067-1p-bigz2012-anon-10002952285-battery-sungrow-winet-lan-summary.md)
