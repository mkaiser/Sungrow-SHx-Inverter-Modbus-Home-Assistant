---
type: entity
title: SAPPHIRE-H_B001.V000.P020
tags: [firmware, sapphire-h-b001-v000-p020]
created: '2026-10-29'
---

# SAPPHIRE-H_B001.V000.P020

SH-RT firmware in the B001 numbering ([SH-RT](device-sh-rt.md)). Version strings `SAPPHIRE-H_01011.95.12`.

- [Register 13074](register-13074.md) writes **times ten**.
- [Register 31211](register-31211.md) answers the sentinel 0xFFFF: no PV cut. Four houses now,
  on SH10RT, SH10RT-20 and SH10RT-V112.
- The discharge windows obey: moved away from now, a 722.5 W discharge stopped and came back
  ([mkaiser](../sources/mkaiser-discharge-window-2026-11-04-summary.md)).
- The forced-charging window obeys: opened around now, charging went from -633 W to 4499 W and
  back ([mkaiser](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)).
- The history block (inputs 6101-6826) answers whole over the cable, on the SH10RT-V112 and on
  [robbensonmio](installation-robbensonmio.md)'s SH10RT.
- **[Register 32998](register-32998.md), the site import limit, holds during a forced charge**: set to
  2.00 kW under a 4500 W forced charge, import held at 1978 W by cutting the charge; [the run](../sources/mkaiser-import-limit-2026-11-07-summary.md). With PV it caps
  grid import alone, 1 (0.01 kW) charges from PV only, and 0 and 5001 are refused; [the PV run](../sources/mkaiser-import-limit-pv-2026-11-07-summary.md).
  The capability test's `--import-limit` check confirmed it; [the engine run](../sources/mkaiser-import-limit-engine-2026-11-07-summary.md).
  It does not hold against house load with the battery idle: import ran at the whole ~2.2 kW
  load against a 2.00 kW cap; [the load run](../sources/mkaiser-import-limit-load-2026-11-07-summary.md).
  With PV above the load it disturbs neither a charge from PV nor export;
  [the export run](../sources/mkaiser-import-limit-export-2026-11-08-summary.md).
  With the battery's discharge limit below the load, a 0.05 kW cap neither made it discharge past
  the limit nor cut the load; [the discharge run](../sources/mkaiser-import-limit-discharge-2026-11-08-summary.md).
  So it is a control here: the number *Grid import limit*.
- **[Register 13017](register-13017.md), forced startup under low SoC, is a switch here too**: 0xAA
  woke the inverter from low-SoC Standby (Running after 3 min 35 s), 0x55 sent it back, 0x01 and 0
  are refused; [the run](../sources/mkaiser-forced-startup-2026-11-08-summary.md). So the switch
  *Forced startup under low SoC* exists here.
- **A minimum SoC (13059) raised above the battery's SoC** made the inverter report 0x8000 (Stop)
  while charging the battery from the grid at its charge limit; [the run](../sources/mkaiser-forced-startup-2026-11-08-summary.md).

## Diagnoses

- [SH10RT-20, B001.V000.P020, bar12, a WiNet-S on Ethernet](../sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P020, bar12, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p020-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port](../sources/sh10rt-b001v000p020-3p-mkaiser-anon-37323352958-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT, B001.V000.P020, mkaiser, the inverter's own LAN port, third reading](../sources/sh10rt-b001v000p020-3p-anonymous-anon-37323352958-battery-unknown-meter-summary.md)
- [SH10RT, B001.V000.P020, robbensonmio, the inverter's own LAN port, SBR256](../sources/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P020, anonymous, through a Modbus proxy to the inverter's own LAN port](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P020, anonymous, the inverter's own LAN port, second reading](../sources/sh10rt-v112-b001v000p020-3p-anonymous-anon-33472554127-battery-thirdparty-meter-direct-lan-2-summary.md)
