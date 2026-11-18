---
type: entity
title: Installation swo14
tags: [installation, swo14, cluster, proxy, third-party-battery]
created: '2026-11-18'
---

# Installation swo14

A **master/slave cluster of two [SH10RT-20](device-sh-rt.md)**, both on the older
[`SAPPHIRE-H_01011.95.03`](firmware-sapphire-h-01011-95-03.md) numbering, with a **third-party
BYD HVM 11 kWh** pack on the host and none on the slave, read from Home Assistant through a
**Modbus proxy**: the host on port 502 at unit 1, the slave on port 503 at unit 2. Three readings
on 2026-11-17, each with a capability test, the inverter restart left out. Stand-ins
`anon-00541024454` (host) and `anon-25617150722` (slave).

- **The second cluster in the corpus**, after [fwitten](installation-fwitten.md)'s, and it keeps
  both rules the config flow rests on: the slave's unit id is 2, and it answers **0** for the
  hardware it lacks where a lone inverter answers 0xFFFF
  ([zero means absent](../concepts/zero-means-absent.md)).
- **[13074](register-13074.md) stores a written word as handed** on both inverters -- the held
  10000 W and 9580 W written back and accepted, with feed-in limitation lifted for that one write
  and put straight back. The second installation on `.95.03`, and the first that is not an
  SH10RT-V112: the 1:1 behaviour follows the firmware, not the model.
- **The 13250 firmware block is refused** here, where fwitten's pair on the same version closed
  the connection on it. The same conclusion by a different refusal, with a proxy in the path.
- **[31211](register-31211.md) and 13017 do not answer**: no PV cut and no forced startup on this
  firmware, as at fwitten.
- **[Register 6100](register-6100.md) answers through the Modbus proxy**, on both entries, over
  their ordinary polling connection
  ([the query](../queries/does-a-modbus-proxy-carry-6100.md)).
- **[Register 32998](register-32998.md) did not hold.** It reads 20.00 kW on both. On the host a
  520 W cap against 1030 W of import under a forced charge moved nothing; the battery was at 3.3 %
  against a 10 % floor. Every SH-RT that obeyed was on P020, P022 or P023, and the integration
  offers the control there only.
- **Register 5214 answers `0x7FFFFFFF` on the slave**, the first reading of what battery power
  reports with no battery at all; 13022 beside it reads the declared 65535
  ([the query](../queries/is-battery-power-firmware-dependent.md)).
- **Five power bounds are not enforced** on the host (10100 W stored over a 10000 W maximum, 1010 W
  over 1000 W), as at [peter-sm](installation-peter-sm.md) on P023 -- so that is not a B001 habit.
- **A BYD pack reads like a Sungrow one** as far as the inverter's own registers go: capacity
  11.1 kWh, 202.5 V, state of health 97 %, and 5214 answering. No pack-specific block exists for
  it, and none was expected.
- The owner's EV was charging through all three readings; the inverter's own EV charger block
  reads mode "PV surplus" and a user current of 16 A throughout.

## Diagnoses

- [SH10RT-20 on 01011.95.03, swo14's host inverter, a BYD pack, through a Modbus proxy](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's host inverter, 53 minutes later](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's slave inverter, no battery of its own](../sources/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md)
