---
type: entity
title: SUNSTONE-H_B000.V002.P065
tags: [firmware, sunstone-h-b000-v002-p065]
created: '2026-11-01'
---

# SUNSTONE-H_B000.V002.P065

[SH-RS](device-sh-rs.md) firmware; version 1 reads `SUNSTONE-H_01011.02.65`. Only read through a
[WiNet-S](device-winet-s.md).

- [Register 31211](register-31211.md) answers 0x55, and **the PV cut is confirmed** by a watched
  cut (3465 W, 0 W, 3092 W), so it is in `CONFIRMED_ON_FIRMWARE`
  (`src/sungrow_modbus/hybrid_inverter/capabilities.py`).
- [Register 13074](register-13074.md) **stores a written word as handed**, by the probe's
  acceptance with feed-in limitation on.
- The battery firmware string (13280) carries bytes after its NUL, as on
  [P068](firmware-sunstone-h-b000-v001-p068.md).

## Surveys

- [SH10RS, B000.V002.P065, Jam3s97, a WiNet-S on Ethernet, with a control test](../sources/sh10rs-b000v002p065-1p-jam3s97-anon-35122522532-battery-sbh300-winet-lan-summary.md)
