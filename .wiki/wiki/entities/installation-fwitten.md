---
type: entity
title: Installation fwitten
tags: [installation, fwitten]
created: '2026-10-29'
---

# Installation fwitten

Two [SH10RT-V112](device-sh-rt.md) in a **master/slave cluster**, each reachable at its own LAN
port and through its own [WiNet-S](device-winet-s.md). The master (`anon-86493117545`) has an
[SBR096](device-sbr-battery.md) and the meter. The slave (`anon-33442450531`) has no battery and
answers on **unit 2** at its own port; see [identify by what answers](../concepts/identify-by-what-answers.md).

Read on [01011.95.03](firmware-sapphire-h-01011-95-03.md) and again on
[P023](firmware-sapphire-h-b001-v000-p023.md) after the owner's upgrade: the cleanest evidence that
[13074](register-13074.md)'s write scale and [31211](register-31211.md) follow the firmware.
The PV cut and the forced-charging window were confirmed on the master, which answered every
block with the owner's Home Assistant polling.

On P023 the master **did not obey [register 32998](register-32998.md)**, the site import limit: a
1090 W cap under the capability test's 1250 W forced charge left import at 1718 W, the battery at
15 % against a 7 % floor ([the run](../sources/fwitten-import-limit-engine-2026-11-22-summary.md)).
Four more caps, on the master, on the slave and on both, all read back and all did nothing
([the cluster run](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md)). The check's run found 13074 multiplying by ten, as before, and the battery power bounds not enforced.

On P023 the **slave's 13050 follows the master's** within a sample, and [register 33500](register-33500.md) reads
0xAA on both inverters ([the run](../sources/fwitten-cluster-mirror-2026-11-24-summary.md)).

## Measurements

- [The slave's EMS mode and 33500, 2026-11-24](../sources/fwitten-cluster-mirror-2026-11-24-summary.md)
- [The site import limit by master, slave and both, 2026-11-24](../sources/fwitten-import-limit-cluster-2026-11-24-summary.md)
- [The capability test's import limit check, master, 2026-11-22](../sources/fwitten-import-limit-engine-2026-11-22-summary.md)

## Diagnoses

- [SH10RT-V112, pre-B001 firmware, fwitten slave, the inverter's own LAN port](../sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten slave, a WiNet-S (medium not reported)](../sources/sh10rt-v112-3p-fwitten-anon-33442450531-battery-none-winet-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten master, the inverter's own LAN port](../sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, pre-B001 firmware, fwitten master, a WiNet-S (medium not reported)](../sources/sh10rt-v112-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port, second reading](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-2-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md)
