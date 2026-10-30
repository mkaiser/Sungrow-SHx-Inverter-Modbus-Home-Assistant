---
type: entity
title: SAPPHIRE-H_B001.V000.P023
tags: [firmware, sapphire-h-b001-v000-p023]
created: '2026-10-29'
---

# SAPPHIRE-H_B001.V000.P023

SH-RT firmware in the B001 numbering ([SH-RT](device-sh-rt.md)), version strings `SAPPHIRE-H_01011.95.14`.
The most-measured firmware in the corpus.

- [Register 13074](register-13074.md) writes **times ten**, on SH10RT-20 and SH10RT-V112, cable and dongle.
- [Register 31211](register-31211.md) answers 0x55, and the cut is **confirmed** by a control test
  on [fwitten](installation-fwitten.md)'s master: P023 is in `CONFIRMED_ON_FIRMWARE`.

- On an SH6.0RT-V112 ([firetribe](installation-firetribe.md)) the 13074 write scale is not
  measured: through a busy WiNet-S its read was refused, and on the cable the inverter
  was starting.

## Surveys

- [SH6.0RT-V112, B001.V000.P023, firetribe, the inverter's own LAN port](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-meter-direct-lan-summary.md)
- [SH6.0RT-V112, B001.V000.P023, firetribe, a WiNet-S on Ethernet](../sources/sh60rt-v112-b001v000p023-3p-firetribe-anon-56336064800-battery-sbr096-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, the inverter's own LAN port](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-20, B001.V000.P023, bar12, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p023-3p-bar12-anon-81257679535-battery-sbr096-winet-wlan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, the inverter's own LAN port](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-meter-direct-lan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on Ethernet](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-lan-summary.md)
- [SH10RT-20, B001.V000.P023, sisu70, a WiNet-S on WiFi](../sources/sh10rt-20-b001v000p023-3p-sisu70-anon-20101498141-battery-sbr128-winet-wlan-summary.md)
- [SH10RT-V112, B001.V000.P023, anonymous, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-anonymous-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, peter_sm, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-peter-sm-anon-91477823483-battery-sbr160-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten slave, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-33442450531-battery-none-winet-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, the inverter's own LAN port](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-meter-direct-lan-summary.md)
- [SH10RT-V112, B001.V000.P023, fwitten master, a WiNet-S (medium not reported)](../sources/sh10rt-v112-b001v000p023-3p-fwitten-anon-86493117545-battery-sbr096-winet-summary.md)
