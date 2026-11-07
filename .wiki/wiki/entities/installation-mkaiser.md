---
type: entity
title: Installation mkaiser
tags: [installation, mkaiser]
created: '2026-10-29'
---

# Installation mkaiser

The maintainer's [SH10RT](device-sh-rt.md) on [P020](firmware-sapphire-h-b001-v000-p020.md) with a
third-party battery, on its own LAN port. Its control tests matched every readback written,
13074 writes times ten, and the forced-charging window raised charging to 4499 W (judged "could
not tell"), and moving the discharge windows away from now stopped a 722.5 W discharge to 0 W and
it came back ([the check](../sources/mkaiser-discharge-window-2026-11-04-summary.md)). A watched write of [register 32998](register-32998.md) held grid import at 2.00 kW under a
4500 W forced charge ([the run](../sources/mkaiser-import-limit-2026-11-07-summary.md)), and with PV capped import alone
([the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md)); the control test's check
confirmed it, and with the PV isolator open the inverter first went to Standby
([the engine run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md)); with the battery
held idle it did not cap the house's own load ([the load run](../sources/mkaiser-import-limit-load-2026-11-07-summary.md)). Its [energy history](../concepts/energy-history.md) reads implausible 2024 slots.

## Surveys

- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, second reading](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-2-summary.md)
