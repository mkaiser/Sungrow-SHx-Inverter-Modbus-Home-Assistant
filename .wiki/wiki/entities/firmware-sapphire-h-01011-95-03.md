---
type: entity
title: SAPPHIRE-H_01011.95.03
tags: [firmware, sapphire-h-01011-95-03]
created: '2026-10-29'
updated: '2026-11-24'
---

# SAPPHIRE-H_01011.95.03

The older SH-RT numbering, which the diagnoses do not carry: the 13250 block does not read, so the
string is known from 2582 and from the export scale the integration stored with it. Seen on
[fwitten](installation-fwitten.md)'s SH10RT-V112 pair before their upgrade to
[P023](firmware-sapphire-h-b001-v000-p023.md), and on both SH10RT-20s of
[swo14](installation-swo14.md)'s cluster.

- [Register 13074](register-13074.md) stores a written word **as handed** (1:1), the only SH-RT
  firmware measured to do so, now at two installations and on two models: fwitten's SH10RT-V112
  and both of swo14's SH10RT-20s (the held 10000 W and 9580 W written back and accepted, with
  feed-in limitation lifted for the one write).
- [Register 31211](register-31211.md) answers the sentinel: no PV cut. 13017 does not answer
  either: no forced startup.
- **The 13250 block fails in two ways.** At fwitten it **closed the connection** -- which is why
  `ABSENT_ON_FIRMWARE` gates `FIRMWARE_VERSIONS` and `METER_CHANNEL_2` off here, to stop the
  reconnect cost -- and at swo14, behind a Modbus proxy, it is **refused with an exception**. The
  gate is right either way, and a proxy may be what turns one into the other.
- **[Register 13023](register-13023.md) reads 0 on a slave with no battery here**, where
  fwitten's slave on P023 answered 0xFFFF. The firmware decides which, not the role.
- **13022 is a signed word here**, 62365 for -3171 W ([swo14](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)), where the B001, SH-RS and
  SH-T readings hold a magnitude ([the query](../queries/is-battery-power-firmware-dependent.md)).
- **Forced discharge and the discharge windows work**: 1251 W for 1250 W
  ([swo14](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md)), and 1726, 0, 1758.5 W ([swo14](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)). 13059 refuses 51 %.

## Diagnoses

- [SH10RT-V112, pre-B001 firmware, fwitten slave, the inverter's own LAN port](../sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten slave, a WiNet-S (medium not reported)](../sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten master, the inverter's own LAN port](../sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten master, a WiNet-S (medium not reported)](../sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's host inverter, a BYD pack, through a Modbus proxy](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's host inverter, 53 minutes later](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-2-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's slave inverter, no battery of its own](../sources/sh10rt-20-3p-sw14-anon-25617150722-battery-none-direct-lan-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's host, battery full, no car charging](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-3-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's host, the car charging](../sources/sh10rt-20-3p-swo14-anon-00541024454-battery-thirdparty-meter-direct-lan-4-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's slave, no car charging](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-summary.md)
- [SH10RT-20 on 01011.95.03, swo14's slave, the car charging, outcome 5](../sources/sh10rt-20-3p-swo14-anon-25617150722-battery-none-direct-lan-2-summary.md)
