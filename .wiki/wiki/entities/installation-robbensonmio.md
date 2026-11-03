---
type: entity
title: Installation robbensonmio
tags: [installation, robbensonmio]
created: '2026-11-02'
---

# Installation robbensonmio

An [SH10RT](device-sh-rt.md) on [P020](firmware-sapphire-h-b001-v000-p020.md) with an
[SBR256](device-sbr-battery.md), eight modules of 20 cells, read on the inverter's own LAN port,
with a WiNet-S fitted but not in the path. One reading, read only, and the owner's own reading of
the SBR cell block.

- **The first eight-module SBR**: every module slot filled, `cell_type_module_1` to `_8` all 1,
  BCU `SBRBCU-S_22011.01.27`.
- **The per-module cell words**: 10765-10772 are each module's highest cell and 10773-10780 each
  module's lowest, which the owner showed in 7 of 7 samples and every cable SBR reading in the
  corpus agrees with ([issue #788](../sources/robbensonmio-sbr-cell-registers-788-summary.md)).
- [31211](register-31211.md) reads 0xFFFF, as on every P020; no meter phase registers answer.

## Sources

- [SH10RT, B001.V000.P020, robbensonmio, the inverter's own LAN port, SBR256](../sources/sh10rt-b001v000p020-3p-robbensonmio-anon-21004123443-battery-sbr256-direct-lan-summary.md)
- [SBR direct BMS registers 10757-10788 on an SBR256 (issue #788)](../sources/robbensonmio-sbr-cell-registers-788-summary.md)
